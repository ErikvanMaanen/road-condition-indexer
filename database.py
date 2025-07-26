"""Database management module for Road Condition Indexer.

This module handles all database operations including:
- Database connection management
- Table creation and schema updates
- Data access layer for bike data, debug logs, and device nicknames
"""

import os
import sqlite3
import json
import logging
import traceback
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from contextlib import contextmanager
import pytz

# SQLAlchemy imports
from sqlalchemy import create_engine, text, MetaData, Table, Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.sql import func

# Import logging utilities
from log_utils import LogLevel, LogCategory

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available, continue without it
    pass

# Import HTTPException for management operations
try:
    from fastapi import HTTPException
except ImportError:
    # Fallback if FastAPI not available
    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str):
            self.status_code = status_code
            self.detail = detail
            super().__init__(detail)

# Table name constants
TABLE_BIKE_DATA = "RCI_bike_data"
TABLE_DEBUG_LOG = "RCI_debug_log" 
TABLE_DEVICE_NICKNAMES = "RCI_device_nicknames"
TABLE_BIKE_SOURCE_DATA = "RCI_bike_source_data"
TABLE_ARCHIVE_LOGS = "RCI_archive_logs"
TABLE_USER_ACTIONS = "RCI_user_actions"

# Base directory for the application
BASE_DIR = Path(__file__).resolve().parent

# Check if SQL Server environment variables are available
SQLSERVER_ENV_VARS = {
    "AZURE_SQL_SERVER": os.getenv("AZURE_SQL_SERVER"),
    "AZURE_SQL_PORT": os.getenv("AZURE_SQL_PORT"),
    "AZURE_SQL_USER": os.getenv("AZURE_SQL_USER"),
    "AZURE_SQL_PASSWORD": os.getenv("AZURE_SQL_PASSWORD"),
    "AZURE_SQL_DATABASE": os.getenv("AZURE_SQL_DATABASE"),
}

# Determine if we should use SQL Server based on environment variables
USE_SQLSERVER = all(SQLSERVER_ENV_VARS.values())

# Force SQL Server usage - fail if credentials not available
FORCE_SQLSERVER = True  # Set this to True to always require SQL Server

if FORCE_SQLSERVER and not USE_SQLSERVER:
    missing_vars = [k for k, v in SQLSERVER_ENV_VARS.items() if not v]
    if missing_vars:
        raise RuntimeError(f"SQL Server configuration required but missing environment variables: {missing_vars}")

USE_SQLSERVER = FORCE_SQLSERVER or USE_SQLSERVER


class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self, log_level: LogLevel = LogLevel.INFO, 
                 log_categories: Optional[List[LogCategory]] = None):
        self.use_sqlserver = USE_SQLSERVER
        self.log_level = log_level
        self.log_categories = log_categories or list(LogCategory)
        self._log_level_order = {
            LogLevel.DEBUG: 0,
            LogLevel.INFO: 1,
            LogLevel.WARNING: 2,
            LogLevel.ERROR: 3,
            LogLevel.CRITICAL: 4
        }
        
        # Initialize SQLAlchemy engine
        self.engine: Optional[Engine] = None
        
        # Initialize logging
        self._setup_logging()
        self.log_debug("DatabaseManager initialized", LogLevel.INFO, LogCategory.DATABASE)
    
    def _setup_logging(self) -> None:
        """Set up Python logging for fallback when database logging fails."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]
        )
        self.logger = logging.getLogger(__name__)
    
    def set_log_level(self, level: LogLevel) -> None:
        """Change the minimum log level."""
        self.log_level = level
        self.log_debug(f"Log level changed to {level.value}", LogLevel.INFO, LogCategory.GENERAL)
    
    def set_log_categories(self, categories: List[LogCategory]) -> None:
        """Set which log categories to record."""
        self.log_categories = categories
        self.log_debug(f"Log categories set to: {[c.value for c in categories]}", 
                      LogLevel.INFO, LogCategory.GENERAL)
    
    def _should_log(self, level: LogLevel, category: LogCategory) -> bool:
        """Check if a message should be logged based on level and category filters."""
        level_ok = self._log_level_order[level] >= self._log_level_order[self.log_level]
        category_ok = category in self.log_categories
        return level_ok and category_ok
    
    def _get_utc_timestamp(self, utc_time: datetime = None) -> str:
        """Get UTC timestamp for database storage."""
        if utc_time is None:
            utc_time = datetime.utcnow()
        
        if self.use_sqlserver:
            # SQL Server format without timezone info
            return utc_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]  # milliseconds
        else:
            # ISO format for other databases
            return utc_time.isoformat()
    
    def _parse_dutch_time_display(self, iso_time_str: str) -> str:
        """Parse ISO time string and return formatted Dutch time for display."""
        try:
            # Parse the datetime (could be UTC or already with timezone)
            if '+' in iso_time_str or iso_time_str.endswith('Z'):
                # Already has timezone info
                dt = datetime.fromisoformat(iso_time_str.replace('Z', '+00:00'))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=pytz.UTC)
            else:
                # Assume UTC if no timezone info
                dt = datetime.fromisoformat(iso_time_str)
                dt = dt.replace(tzinfo=pytz.UTC)
            
            # Convert to Dutch time
            dutch_tz = pytz.timezone('Europe/Amsterdam')
            dutch_time = dt.astimezone(dutch_tz)
            
            return dutch_time.strftime('%d-%m-%Y %H:%M:%S %Z')
        except Exception:
            # Fallback to original string
            return iso_time_str
    
    @contextmanager
    def get_connection_context(self, database: Optional[str] = None):
        """Get a database connection with proper context management to prevent journal file issues."""
        engine = self.get_engine(database)
        connection = None
        try:
            connection = engine.connect()
            yield connection
        except Exception as e:
            if connection:
                try:
                    connection.rollback()
                except Exception:
                    pass
            raise
        finally:
            if connection:
                try:
                    connection.close()
                except Exception:
                    pass
    
    def get_engine(self, database: Optional[str] = None) -> Engine:
        """Get SQLAlchemy engine for database operations."""
        if self.engine is not None:
            return self.engine
            
        try:
            if self.use_sqlserver:
                server = os.getenv("AZURE_SQL_SERVER")
                port = os.getenv("AZURE_SQL_PORT")
                user = os.getenv("AZURE_SQL_USER")
                password = os.getenv("AZURE_SQL_PASSWORD")
                db_name = database or os.getenv("AZURE_SQL_DATABASE")
                
                self.log_debug(f"Creating SQLAlchemy engine for SQL Server: {server}:{port}, database: {db_name}", 
                              LogLevel.DEBUG, LogCategory.CONNECTION)
                
                # Using pymssql driver instead of pyodbc
                connection_string = f"mssql+pymssql://{user}:{password}@{server}:{port}/{db_name}"
                
                self.engine = create_engine(
                    connection_string,
                    echo=False,  # Set to True for SQL query logging
                    pool_pre_ping=True,
                    pool_recycle=3600,  # Recycle connections after 1 hour
                    connect_args={"timeout": 30}
                )
                
                self.log_debug("SQL Server SQLAlchemy engine created successfully", 
                              LogLevel.DEBUG, LogCategory.CONNECTION)
                return self.engine
            else:
                # SQLite fallback with optimized settings
                db_file = BASE_DIR / "RCI_local.db"
                self.log_debug(f"Creating SQLAlchemy engine for SQLite database: {db_file}", 
                              LogLevel.DEBUG, LogCategory.CONNECTION)
                
                connection_string = f"sqlite:///{db_file}"
                
                self.engine = create_engine(
                    connection_string,
                    echo=False,  # Set to True for SQL query logging
                    poolclass=StaticPool,
                    connect_args={
                        'check_same_thread': False,
                        'timeout': 30
                    }
                )
                
                # Set SQLite pragmas for optimized performance
                with self.engine.connect() as conn:
                    conn.execute(text("PRAGMA journal_mode=WAL"))  # Use Write-Ahead Logging
                    conn.execute(text("PRAGMA synchronous=NORMAL"))  # Balanced safety/performance
                    conn.execute(text("PRAGMA cache_size=-8000"))  # 8MB cache (negative = KB)
                    conn.execute(text("PRAGMA temp_store=MEMORY"))  # Use memory for temp tables
                    conn.execute(text("PRAGMA mmap_size=268435456"))  # 256MB memory-mapped I/O
                    conn.execute(text("PRAGMA wal_autocheckpoint=1000"))  # Checkpoint every 1000 pages
                    conn.execute(text("PRAGMA busy_timeout=30000"))  # 30 second busy timeout
                    conn.commit()
                
                self.log_debug("SQLite SQLAlchemy engine created successfully with optimized settings", 
                              LogLevel.DEBUG, LogCategory.CONNECTION)
                return self.engine
        except Exception as e:
            self.log_debug(f"Database engine creation failed: {e}", 
                          LogLevel.ERROR, LogCategory.CONNECTION, include_stack=True)
            raise

    def get_connection(self, database: Optional[str] = None):
        """Return a database connection.

        When the required Azure SQL environment variables are present the
        connection uses SQLAlchemy with pymssql driver. Otherwise a local SQLite database named
        ``RCI_local.db`` in the project directory is used. This makes the API usable
        without any external dependencies.
        """
        engine = self.get_engine(database)
        return engine.connect()

    def ensure_database_exists(self) -> None:
        """Ensure the configured database exists."""
        try:
            if self.use_sqlserver:
                server = os.getenv("AZURE_SQL_SERVER")
                port = os.getenv("AZURE_SQL_PORT")
                user = os.getenv("AZURE_SQL_USER")
                password = os.getenv("AZURE_SQL_PASSWORD")
                database = os.getenv("AZURE_SQL_DATABASE")

                self.log_debug(f"Checking if database '{database}' exists on {server}", 
                              LogLevel.DEBUG, LogCategory.DATABASE)

                with self.get_connection_context("master") as conn:
                    result = conn.execute(
                        text("SELECT database_id FROM sys.databases WHERE name = :db_name"),
                        {"db_name": database}
                    )
                    if not result.fetchone():
                        self.log_debug(f"Database '{database}' does not exist, creating it", 
                                      LogLevel.INFO, LogCategory.DATABASE)
                        conn.execute(text(f"CREATE DATABASE [{database}]"))
                        conn.commit()
                        self.log_debug(f"Database '{database}' created successfully", 
                                      LogLevel.INFO, LogCategory.DATABASE)
                    else:
                        self.log_debug(f"Database '{database}' already exists", 
                                      LogLevel.DEBUG, LogCategory.DATABASE)
            else:
                # SQLite creates the database file automatically
                db_file = BASE_DIR / "RCI_local.db"
                if not db_file.exists():
                    self.log_debug(f"Creating SQLite database file: {db_file}", 
                                  LogLevel.INFO, LogCategory.DATABASE)
                    db_file.touch(exist_ok=True)
                    self.log_debug("SQLite database file created successfully", 
                                  LogLevel.INFO, LogCategory.DATABASE)
                else:
                    self.log_debug(f"SQLite database file already exists: {db_file}", 
                                  LogLevel.DEBUG, LogCategory.DATABASE)
        except Exception as e:
            self.log_debug(f"Failed to ensure database exists: {e}", 
                          LogLevel.ERROR, LogCategory.DATABASE, include_stack=True)
            raise

    def init_tables(self) -> None:
        """Ensure that required tables exist."""
        start_time = time.time()
        
        try:
            self.log_debug("Starting table initialization", LogLevel.INFO, LogCategory.DATABASE)
            
            self.ensure_database_exists()
            
            with self.get_connection_context() as conn:
                if self.use_sqlserver:
                    self.log_debug("Creating SQL Server tables", LogLevel.DEBUG, LogCategory.DATABASE)
                    self._create_sqlserver_tables(conn)
                else:
                    self.log_debug("Creating SQLite tables", LogLevel.DEBUG, LogCategory.DATABASE)
                    self._create_sqlite_tables(conn)
                
                conn.commit()
                
                total_time = (time.time() - start_time) * 1000
                self.log_debug(f"Table initialization completed successfully in {total_time:.2f}ms", LogLevel.INFO, LogCategory.DATABASE)
                
        except Exception as exc:
            total_time = (time.time() - start_time) * 1000
            self.log_debug(f"Database init error: {exc}", LogLevel.ERROR, LogCategory.DATABASE, include_stack=True)
            raise Exception(f"Database init error: {exc}")

    def _create_sqlserver_tables(self, conn):
        """Create tables for SQL Server."""
        # Create bike data table
        conn.execute(
            text(f"""
            IF NOT EXISTS (
                SELECT 1 FROM sys.tables WHERE name = '{TABLE_BIKE_DATA}'
            )
            BEGIN
                CREATE TABLE {TABLE_BIKE_DATA} (
                    id INT IDENTITY PRIMARY KEY,
                    timestamp DATETIME DEFAULT GETDATE(),
                    latitude FLOAT,
                    longitude FLOAT,
                    speed FLOAT,
                    direction FLOAT,
                    roughness FLOAT,
                    distance_m FLOAT,
                    device_id NVARCHAR(100),
                    ip_address NVARCHAR(45)
                )
            END
            """)
        )
        
        # Create debug log table
        conn.execute(
            text(f"""
            IF NOT EXISTS (
                SELECT 1 FROM sys.tables WHERE name = '{TABLE_DEBUG_LOG}'
            )
            BEGIN
                CREATE TABLE {TABLE_DEBUG_LOG} (
                    id INT IDENTITY PRIMARY KEY,
                    timestamp DATETIME DEFAULT GETDATE(),
                    level NVARCHAR(20),
                    category NVARCHAR(50),
                    device_id NVARCHAR(100),
                    message NVARCHAR(4000),
                    stack_trace NVARCHAR(MAX)
                )
            END
            """)
        )
        
        # Create device nicknames table
        conn.execute(
            text(f"""
            IF NOT EXISTS (
                SELECT 1 FROM sys.tables WHERE name = '{TABLE_DEVICE_NICKNAMES}'
            )
            BEGIN
                CREATE TABLE {TABLE_DEVICE_NICKNAMES} (
                    device_id NVARCHAR(100) PRIMARY KEY,
                    nickname NVARCHAR(100),
                    user_agent NVARCHAR(256),
                    device_fp NVARCHAR(256)
                )
            END
            """)
        )
        
        # Create bike source data table for retrospective analysis
        conn.execute(
            text(f"""
            IF NOT EXISTS (
                SELECT 1 FROM sys.tables WHERE name = '{TABLE_BIKE_SOURCE_DATA}'
            )
            BEGIN
                CREATE TABLE {TABLE_BIKE_SOURCE_DATA} (
                    id INT IDENTITY PRIMARY KEY,
                    bike_data_id INT NOT NULL,
                    z_values NVARCHAR(MAX),
                    speed FLOAT,
                    interval_seconds FLOAT,
                    freq_min FLOAT,
                    freq_max FLOAT,
                    FOREIGN KEY (bike_data_id) REFERENCES {TABLE_BIKE_DATA}(id) ON DELETE CASCADE
                )
            END
            """)
        )
        
        # Create archive logs table (same structure as bike data for archived records)
        conn.execute(
            text(f"""
            IF NOT EXISTS (
                SELECT 1 FROM sys.tables WHERE name = '{TABLE_ARCHIVE_LOGS}'
            )
            BEGIN
                CREATE TABLE {TABLE_ARCHIVE_LOGS} (
                    id INT IDENTITY PRIMARY KEY,
                    latitude FLOAT NOT NULL,
                    longitude FLOAT NOT NULL,
                    speed FLOAT NOT NULL,
                    direction FLOAT NOT NULL,
                    roughness FLOAT NOT NULL,
                    timestamp DATETIME2 DEFAULT GETDATE(),
                    device_id NVARCHAR(255) NOT NULL,
                ip_address NVARCHAR(45)
            )
            END
            """)
        )

        # Create user actions table for tracking user behavior and system events
        conn.execute(
            text(f"""
            IF NOT EXISTS (
                SELECT 1 FROM sys.tables WHERE name = '{TABLE_USER_ACTIONS}'
            )
            BEGIN
                CREATE TABLE {TABLE_USER_ACTIONS} (
                    id INT IDENTITY PRIMARY KEY,
                    timestamp DATETIME2 DEFAULT GETDATE(),
                    action_type NVARCHAR(50) NOT NULL,
                    action_description NVARCHAR(500) NOT NULL,
                    user_ip NVARCHAR(45),
                    user_agent NVARCHAR(500),
                    device_id NVARCHAR(255),
                    session_id NVARCHAR(100),
                    additional_data NVARCHAR(MAX),
                    success BIT DEFAULT 1,
                    error_message NVARCHAR(MAX)
                )
            END
            """)
        )
        
        # Schema migration statements
        self._apply_sqlserver_migrations(conn)

    def _apply_sqlserver_migrations(self, conn):
        """Apply schema migrations for SQL Server."""
        # Add ip_address column if it doesn't exist
        conn.execute(
            text(f"""
            IF COL_LENGTH('{TABLE_BIKE_DATA}', 'ip_address') IS NULL
                ALTER TABLE {TABLE_BIKE_DATA} ADD ip_address NVARCHAR(45)
            """)
        )
        
        # Remove old user_agent column from bike_data
        conn.execute(
            text(f"""
            IF COL_LENGTH('{TABLE_BIKE_DATA}', 'user_agent') IS NOT NULL
                ALTER TABLE {TABLE_BIKE_DATA} DROP COLUMN user_agent
            """)
        )
        
        # Remove old device_fp column from bike_data
        conn.execute(
            text(f"""
            IF COL_LENGTH('{TABLE_BIKE_DATA}', 'device_fp') IS NOT NULL
                ALTER TABLE {TABLE_BIKE_DATA} DROP COLUMN device_fp
            """)
        )
        
        # Add distance_m column if it doesn't exist
        conn.execute(
            text(f"""
            IF COL_LENGTH('{TABLE_BIKE_DATA}', 'distance_m') IS NULL
                ALTER TABLE {TABLE_BIKE_DATA} ADD distance_m FLOAT
            """)
        )
        
        # Add device_id column to debug log table if it doesn't exist
        conn.execute(
            text(f"""
            IF COL_LENGTH('{TABLE_DEBUG_LOG}', 'device_id') IS NULL
                ALTER TABLE {TABLE_DEBUG_LOG} ADD device_id NVARCHAR(100)
            """)
        )
        
        # Remove old version column
        conn.execute(
            text(f"""
            IF COL_LENGTH('{TABLE_BIKE_DATA}', 'version') IS NOT NULL
            BEGIN
                DECLARE @cons nvarchar(200);
                SELECT @cons = dc.name
                FROM sys.default_constraints dc
                JOIN sys.columns c ON dc.parent_object_id = c.object_id
                        AND dc.parent_column_id = c.column_id
                WHERE dc.parent_object_id = OBJECT_ID('{TABLE_BIKE_DATA}')
                      AND c.name = 'version';
                IF @cons IS NOT NULL
                    EXEC('ALTER TABLE {TABLE_BIKE_DATA} DROP CONSTRAINT ' + @cons);
                ALTER TABLE {TABLE_BIKE_DATA} DROP COLUMN version;
            END
            """)
        )
        
        # Add columns to device_nicknames if they don't exist
        conn.execute(
            text(f"""
            IF COL_LENGTH('{TABLE_DEVICE_NICKNAMES}', 'user_agent') IS NULL
                ALTER TABLE {TABLE_DEVICE_NICKNAMES} ADD user_agent NVARCHAR(256)
            """)
        )
        conn.execute(
            text(f"""
            IF COL_LENGTH('{TABLE_DEVICE_NICKNAMES}', 'device_fp') IS NULL
                ALTER TABLE {TABLE_DEVICE_NICKNAMES} ADD device_fp NVARCHAR(256)
            """)
        )
        
        # Add new debug log columns if they don't exist
        conn.execute(
            text(f"""
            IF COL_LENGTH('{TABLE_DEBUG_LOG}', 'level') IS NULL
                ALTER TABLE {TABLE_DEBUG_LOG} ADD level NVARCHAR(20)
            """)
        )
        conn.execute(
            text(f"""
            IF COL_LENGTH('{TABLE_DEBUG_LOG}', 'category') IS NULL
                ALTER TABLE {TABLE_DEBUG_LOG} ADD category NVARCHAR(50)
            """)
        )
        conn.execute(
            text(f"""
            IF COL_LENGTH('{TABLE_DEBUG_LOG}', 'stack_trace') IS NULL
                ALTER TABLE {TABLE_DEBUG_LOG} ADD stack_trace NVARCHAR(MAX)
            """)
        )

    def _create_sqlite_tables(self, cursor):
        """Create tables for SQLite."""
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {TABLE_BIKE_DATA} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                latitude REAL,
                longitude REAL,
                speed REAL,
                direction REAL,
                roughness REAL,
                distance_m REAL,
                device_id TEXT,
                ip_address TEXT
            )
            """
        )
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {TABLE_DEBUG_LOG} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                level TEXT,
                category TEXT,
                device_id TEXT,
                message TEXT,
                stack_trace TEXT
            )
            """
        )
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {TABLE_DEVICE_NICKNAMES} (
                device_id TEXT PRIMARY KEY,
                nickname TEXT,
                user_agent TEXT,
                device_fp TEXT
            )
            """
        )
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {TABLE_BIKE_SOURCE_DATA} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bike_data_id INTEGER NOT NULL,
                z_values TEXT,
                speed REAL,
                interval_seconds REAL,
                freq_min REAL,
                freq_max REAL,
                FOREIGN KEY (bike_data_id) REFERENCES {TABLE_BIKE_DATA}(id) ON DELETE CASCADE
            )
            """
        )
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {TABLE_ARCHIVE_LOGS} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                speed REAL NOT NULL,
                direction REAL NOT NULL,
                roughness REAL NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                device_id TEXT NOT NULL,
                ip_address TEXT
            )
            """
        )
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {TABLE_USER_ACTIONS} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                action_type TEXT NOT NULL,
                action_description TEXT NOT NULL,
                user_ip TEXT,
                user_agent TEXT,
                device_id TEXT,
                session_id TEXT,
                additional_data TEXT,
                success INTEGER DEFAULT 1,
                error_message TEXT
            )
            """
        )
        
        # Apply SQLite schema migrations
        self._apply_sqlite_migrations(cursor)

    def _apply_sqlite_migrations(self, cursor):
        """Apply schema migrations for SQLite."""
        # Check if device_id column exists in debug log table
        cursor.execute(f"PRAGMA table_info({TABLE_DEBUG_LOG})")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'device_id' not in columns:
            try:
                cursor.execute(f"ALTER TABLE {TABLE_DEBUG_LOG} ADD COLUMN device_id TEXT")
                self.logger.info("Added device_id column to debug log table")
            except Exception as e:
                self.logger.error(f"Failed to add device_id column: {e}")

    def log_debug(self, message: str, level: LogLevel = LogLevel.INFO, 
                  category: LogCategory = LogCategory.GENERAL,
                  include_stack: bool = False, device_id: Optional[str] = None) -> None:
        """Insert a debug message into the debug log table with filtering support.
        
        Args:
            message: The log message
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            category: Log category for filtering
            include_stack: Whether to include stack trace information
            device_id: Optional device ID to associate with the log entry
        """
        if not self._should_log(level, category):
            return
            
        timestamp = self._get_utc_timestamp()
        stack_trace = None
        
        if include_stack or level in [LogLevel.ERROR, LogLevel.CRITICAL]:
            stack_trace = traceback.format_stack()[-3:-1]  # Get relevant stack frames
            stack_trace = ''.join(stack_trace).strip()
        
        try:
            self.execute_non_query(
                f"""INSERT INTO {TABLE_DEBUG_LOG} (timestamp, level, category, device_id, message, stack_trace) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (timestamp, level.value, category.value, device_id, message, stack_trace)
            )
        except Exception as e:
            # Check for database corruption
            error_msg = str(e).lower()
            if "disk i/o error" in error_msg or "database is locked" in error_msg or "corrupt" in error_msg:
                try:
                    # Try to recover the debug log table
                    self._recover_debug_log_table()
                except Exception:
                    pass  # Recovery failed, fall back to Python logging
            
            # Fallback to Python logging if database logging fails
            log_msg = f"[{category.value}] {message}"
            if level == LogLevel.DEBUG:
                self.logger.debug(log_msg)
            elif level == LogLevel.INFO:
                self.logger.info(log_msg)
            elif level == LogLevel.WARNING:
                self.logger.warning(log_msg)
            elif level == LogLevel.ERROR:
                self.logger.error(log_msg)
            elif level == LogLevel.CRITICAL:
                self.logger.critical(log_msg)
    
    def get_debug_logs(self, level_filter: Optional[LogLevel] = None,
                      category_filter: Optional[LogCategory] = None,
                      device_id_filter: Optional[str] = None,
                      limit: Optional[int] = 100) -> List[Dict[str, Any]]:
        """Retrieve debug logs with optional filtering.
        
        Args:
            level_filter: Filter by minimum log level
            category_filter: Filter by specific category
            device_id_filter: Filter by specific device ID
            limit: Maximum number of logs to return
            
        Returns:
            List of log entries as dictionaries
        """
        try:
            query = f"SELECT * FROM {TABLE_DEBUG_LOG} WHERE 1=1"
            params = []
            
            if level_filter:
                # Filter by level and above based on severity
                level_order = self._log_level_order[level_filter]
                valid_levels = [l.value for l, o in self._log_level_order.items() if o >= level_order]
                placeholders = ",".join("?" for _ in valid_levels)
                query += f" AND level IN ({placeholders})"
                params.extend(valid_levels)
            
            if category_filter:
                query += " AND category = ?"
                params.append(category_filter.value)
            
            if device_id_filter:
                query += " AND device_id = ?"
                params.append(device_id_filter)
            
            query += " ORDER BY id DESC"
            if limit:
                if self.use_sqlserver:
                    query = query.replace("SELECT *", f"SELECT TOP {limit} *")
                else:
                    query += " LIMIT ?"
                    params.append(limit)
            
            return self.execute_query(query, tuple(params) if params else None)
        except Exception as e:
            # Check if this is a disk I/O error or corruption
            error_msg = str(e).lower()
            if "disk i/o error" in error_msg or "database is locked" in error_msg or "corrupt" in error_msg:
                self.logger.error(f"Database corruption detected: {e}")
                try:
                    # Try to recover by recreating the debug log table
                    self._recover_debug_log_table()
                    return []  # Return empty list after recovery attempt
                except Exception as recovery_error:
                    self.logger.error(f"Failed to recover debug log table: {recovery_error}")
            
            self.logger.error(f"Failed to retrieve debug logs: {e}")
            return []

    def _recover_debug_log_table(self) -> None:
        """Attempt to recover the debug log table from corruption."""
        try:
            # First try to backup existing data if possible
            backup_table = f"{TABLE_DEBUG_LOG}_backup_{int(datetime.utcnow().timestamp())}"
            try:
                backup_query = f"CREATE TABLE {backup_table} AS SELECT * FROM {TABLE_DEBUG_LOG}"
                self.execute_query(backup_query)
                self.logger.info(f"Created backup table: {backup_table}")
            except Exception:
                self.logger.warning("Could not create backup of corrupted debug log table")
            
            # Drop the corrupted table
            self.execute_query(f"DROP TABLE IF EXISTS {TABLE_DEBUG_LOG}")
            
            # Recreate the table with fresh structure
            self._create_debug_log_table()
            
            self.logger.info("Debug log table recovered successfully")
            
        except Exception as e:
            self.logger.error(f"Debug log table recovery failed: {e}")
            raise

    def check_database_integrity(self) -> bool:
        """Check database integrity and repair if needed."""
        try:
            if not self.use_sqlserver:
                # For SQLite, run PRAGMA integrity_check
                result = self.execute_query("PRAGMA integrity_check")
                if result and len(result) > 0:
                    first_result = result[0]
                    if isinstance(first_result, dict) and 'integrity_check' in first_result:
                        integrity_ok = first_result['integrity_check'] == 'ok'
                    elif isinstance(first_result, (list, tuple)) and len(first_result) > 0:
                        integrity_ok = first_result[0] == 'ok'
                    else:
                        integrity_ok = str(first_result).lower() == 'ok'
                    
                    if not integrity_ok:
                        self.logger.warning("Database integrity check failed, attempting repair")
                        # Try to vacuum the database
                        self.execute_query("VACUUM")
                        return False
                    return True
            else:
                # For SQL Server, check if we can perform basic operations
                self.execute_query("SELECT 1")
                return True
        except Exception as e:
            self.logger.error(f"Database integrity check failed: {e}")
            return False

    def log_user_action(self, action_type: str, action_description: str,
                       user_ip: Optional[str] = None, user_agent: Optional[str] = None,
                       device_id: Optional[str] = None, session_id: Optional[str] = None,
                       additional_data: Optional[Dict] = None, success: bool = True,
                       error_message: Optional[str] = None) -> None:
        """Log user actions to the user actions table."""
        try:
            timestamp = self._get_utc_timestamp()
            additional_data_json = json.dumps(additional_data) if additional_data else None

            self.execute_non_query(
                f"""INSERT INTO {TABLE_USER_ACTIONS}
                   (timestamp, action_type, action_description, user_ip, user_agent,
                    device_id, session_id, additional_data, success, error_message)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (timestamp, action_type, action_description, user_ip, user_agent,
                 device_id, session_id, additional_data_json, success, error_message),
            )

            status = "SUCCESS" if success else "FAILED"
            log_message = f"USER_ACTION [{action_type}] {action_description} - {status}"
            if error_message:
                log_message += f" - Error: {error_message}"

            self.log_debug(log_message, LogLevel.INFO, LogCategory.USER_ACTION, device_id=device_id)

        except Exception as e:
            self.logger.error(f"Failed to log user action: {e}")
            self.log_debug(
                f"Failed to log user action [{action_type}] {action_description}: {e}",
                LogLevel.ERROR,
                LogCategory.USER_ACTION,
            )

    def log_sql_operation(self, operation_type: str, query: str, params: Optional[Tuple] = None,
                         result_count: Optional[int] = None, execution_time_ms: Optional[float] = None,
                         success: bool = True, error_message: Optional[str] = None,
                         device_id: Optional[str] = None) -> None:
        """Log SQL operations for auditing and debugging.
        
        Args:
            operation_type: Type of SQL operation (INSERT, SELECT, UPDATE, DELETE, etc.)
            query: The SQL query executed (will be truncated if too long)
            params: Parameters used in the query
            result_count: Number of rows affected/returned
            execution_time_ms: Execution time in milliseconds
            success: Whether the operation was successful
            error_message: Error message if operation failed
            device_id: Device ID if applicable
        """
        try:
            # Truncate long queries for logging
            query_for_log = query[:500] + "..." if len(query) > 500 else query
            
            # Create detailed log message
            log_parts = [f"SQL_{operation_type}"]
            log_parts.append(f"Query: {query_for_log}")
            
            if params:
                # Safely represent parameters (avoid logging sensitive data)
                params_str = str(params)[:200] + "..." if len(str(params)) > 200 else str(params)
                log_parts.append(f"Params: {params_str}")
            
            if result_count is not None:
                log_parts.append(f"Results: {result_count} rows")
            
            if execution_time_ms is not None:
                log_parts.append(f"Time: {execution_time_ms:.2f}ms")
            
            if not success and error_message:
                log_parts.append(f"Error: {error_message}")
            
            log_message = " | ".join(log_parts)
            log_level = LogLevel.ERROR if not success else LogLevel.DEBUG
            
            self.log_debug(log_message, log_level, LogCategory.SQL_OPERATION, device_id=device_id)
            
        except Exception as e:
            # Fallback logging if SQL operation logging fails
            self.logger.error(f"Failed to log SQL operation: {e}")

    def log_startup_event(self, event_type: str, event_description: str,
                         success: bool = True, error_message: Optional[str] = None,
                         additional_data: Optional[Dict] = None) -> None:
        """Log startup events for system monitoring.
        
        Args:
            event_type: Type of startup event (DB_INIT, TABLE_CREATION, MIGRATION, etc.)
            event_description: Description of the startup event
            success: Whether the event was successful
            error_message: Error message if event failed
            additional_data: Additional structured data
        """
        try:
            # Log to debug log with startup category
            status = "SUCCESS" if success else "FAILED"
            log_message = f"STARTUP [{event_type}] {event_description} - {status}"
            if error_message:
                log_message += f" - Error: {error_message}"
            if additional_data:
                log_message += f" - Data: {json.dumps(additional_data, default=str)}"
            
            log_level = LogLevel.ERROR if not success else LogLevel.INFO
            self.log_debug(log_message, log_level, LogCategory.STARTUP)
            
        except Exception as e:
            # Fallback logging if startup event logging fails
            self.logger.error(f"Failed to log startup event: {e}")

    def insert_bike_data(self, latitude: float, longitude: float, speed: float, 
                        direction: float, roughness: float, distance_m: float,
                        device_id: str, ip_address: Optional[str]) -> int:
        """Insert bike data into the database and return the ID."""
        start_time = time.time()
        
        self.log_debug(f"Inserting bike data for device {device_id}: lat={latitude}, lon={longitude}, speed={speed}, roughness={roughness}", 
                      LogLevel.DEBUG, LogCategory.QUERY)
        
        query = f"INSERT INTO {TABLE_BIKE_DATA} (latitude, longitude, speed, direction, roughness, distance_m, device_id, ip_address) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        params = (latitude, longitude, speed, direction, roughness, distance_m, device_id, ip_address)
        
        try:
            with self.get_connection_context() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                
                # Check rowcount immediately after INSERT
                if cursor.rowcount != 1:
                    error_msg = f"Insert affected {cursor.rowcount} rows, expected 1"
                    self.log_debug(error_msg, LogLevel.ERROR, LogCategory.QUERY)
                    raise Exception(error_msg)
                
                # Get the inserted ID
                if self.use_sqlserver:
                    cursor.execute("SELECT @@IDENTITY")
                    bike_data_id = cursor.fetchone()[0]
                else:
                    bike_data_id = cursor.lastrowid
                
                conn.commit()
                
                # Calculate execution time
                execution_time = (time.time() - start_time) * 1000
                
                # Log the successful SQL operation
                self.log_sql_operation(
                    operation_type="INSERT",
                    query=query,
                    params=params,
                    result_count=1,
                    execution_time_ms=execution_time,
                    success=True,
                    device_id=device_id
                )
                
                self.log_debug(f"Successfully inserted bike data for device {device_id} with ID {bike_data_id}", 
                              LogLevel.DEBUG, LogCategory.QUERY)
                return bike_data_id
        except Exception as e:
            # Calculate execution time even for failed operations
            execution_time = (time.time() - start_time) * 1000
            
            # Log the failed SQL operation
            self.log_sql_operation(
                operation_type="INSERT",
                query=query,
                params=params,
                result_count=0,
                execution_time_ms=execution_time,
                success=False,
                error_message=str(e),
                device_id=device_id
            )
            
            self.log_debug(f"Failed to insert bike data for device {device_id}: {e}", 
                          LogLevel.ERROR, LogCategory.QUERY)
            raise

    def upsert_device_info(self, device_id: str, user_agent: Optional[str], 
                          device_fp: Optional[str]) -> None:
        """Insert or update device information."""
        self.log_debug(f"Upserting device info for {device_id}: user_agent={user_agent}, device_fp={device_fp}", 
                      LogLevel.DEBUG, LogCategory.QUERY)
        
        try:
            with self.get_connection_context() as conn:
                cursor = conn.cursor()
                if self.use_sqlserver:
                    cursor.execute(
                        f"""
                        MERGE {TABLE_DEVICE_NICKNAMES} AS target
                        USING (SELECT ? AS device_id, ? AS ua, ? AS fp) AS src
                        ON target.device_id = src.device_id
                        WHEN MATCHED THEN UPDATE SET user_agent = src.ua, device_fp = src.fp
                        WHEN NOT MATCHED THEN INSERT (device_id, user_agent, device_fp) VALUES (src.device_id, src.ua, src.fp);
                        """,
                        (device_id, user_agent, device_fp)
                    )
                else:
                    cursor.execute(
                        f"""
                        INSERT INTO {TABLE_DEVICE_NICKNAMES} (device_id, user_agent, device_fp)
                        VALUES (?, ?, ?)
                        ON CONFLICT(device_id) DO UPDATE SET user_agent=excluded.user_agent,
                        device_fp=excluded.device_fp
                        """,
                        (device_id, user_agent, device_fp)
                    )
                conn.commit()
                self.log_debug(f"Successfully upserted device info for {device_id}", 
                              LogLevel.DEBUG, LogCategory.QUERY)
        except Exception as e:
            self.log_debug(f"Failed to upsert device info for {device_id}: {e}", 
                          LogLevel.ERROR, LogCategory.QUERY)
            raise

    def insert_bike_source_data(self, bike_data_id: int, z_values: List[float], 
                               speed: float, interval_seconds: float, 
                               freq_min: float, freq_max: float) -> None:
        """Insert bike source data for retrospective analysis."""
        self.log_debug(f"Inserting source data for bike_data_id {bike_data_id}: z_values count={len(z_values)}", 
                      LogLevel.DEBUG, LogCategory.QUERY)
        
        try:
            # Serialize z_values as JSON
            z_values_json = json.dumps(z_values)
            
            with self.get_connection_context() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f"INSERT INTO {TABLE_BIKE_SOURCE_DATA} (bike_data_id, z_values, speed, interval_seconds, freq_min, freq_max)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (bike_data_id, z_values_json, speed, interval_seconds, freq_min, freq_max)
                )
                conn.commit()
                self.log_debug(f"Successfully inserted source data for bike_data_id {bike_data_id}", 
                              LogLevel.DEBUG, LogCategory.QUERY)
        except Exception as e:
            self.log_debug(f"Failed to insert source data for bike_data_id {bike_data_id}: {e}", 
                          LogLevel.ERROR, LogCategory.QUERY, include_stack=True)
            raise

    def get_last_bike_data_point(self, device_id: str) -> Optional[Tuple[datetime, float, float]]:
        """Get the last recorded bike data point for a device."""
        self.log_debug(f"Retrieving last bike data point for device {device_id}", 
                      LogLevel.DEBUG, LogCategory.QUERY)
        
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            if self.use_sqlserver:
                cursor.execute(
                    f"SELECT TOP 1 latitude, longitude, timestamp FROM {TABLE_BIKE_DATA} WHERE device_id = ? ORDER BY id DESC",
                    (device_id,)
                )
            else:
                cursor.execute(
                    f"SELECT latitude, longitude, timestamp FROM {TABLE_BIKE_DATA} WHERE device_id = ? ORDER BY id DESC LIMIT 1",
                    (device_id,)
                )
            row = cursor.fetchone()
            if row:
                result = (row[2], row[0], row[1])  # timestamp, latitude, longitude
                self.log_debug(f"Found last data point for device {device_id}: {result}", 
                              LogLevel.DEBUG, LogCategory.QUERY)
                return result
            else:
                self.log_debug(f"No data points found for device {device_id}", 
                              LogLevel.DEBUG, LogCategory.QUERY)
            return None
        except Exception as e:
            self.log_debug(f"Failed to get last bike data point for device {device_id}: {e}", 
                          LogLevel.ERROR, LogCategory.QUERY, include_stack=True)
            raise
        finally:
            conn.close()

    def get_logs(self, limit: Optional[int] = None) -> Tuple[List[Dict], float]:
        """Get bike data logs with optional limit."""
        self.log_debug(f"Retrieving bike data logs with limit={limit}", 
                      LogLevel.DEBUG, LogCategory.QUERY)
        
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            if self.use_sqlserver:
                if limit is None:
                    cursor.execute(f"SELECT * FROM {TABLE_BIKE_DATA} ORDER BY id DESC")
                else:
                    cursor.execute(f"SELECT TOP {limit} * FROM {TABLE_BIKE_DATA} ORDER BY id DESC")
            else:
                query = f"SELECT * FROM {TABLE_BIKE_DATA} ORDER BY id DESC"
                if limit is None:
                    cursor.execute(query)
                else:
                    cursor.execute(query + " LIMIT ?", (limit,))
            
            columns = [column[0] for column in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            cursor.execute(f"SELECT AVG(roughness) FROM {TABLE_BIKE_DATA}")
            avg_row = cursor.fetchone()
            rough_avg = float(avg_row[0]) if avg_row and avg_row[0] is not None else 0.0
            
            self.log_debug(f"Retrieved {len(rows)} bike data logs, avg roughness: {rough_avg}", 
                          LogLevel.DEBUG, LogCategory.QUERY)
            return rows, rough_avg
        except Exception as e:
            self.log_debug(f"Failed to retrieve bike data logs: {e}", 
                          LogLevel.ERROR, LogCategory.QUERY, include_stack=True)
            raise
        finally:
            conn.close()

    def get_filtered_logs(self, device_ids: Optional[List[str]] = None,
                         start_dt: Optional[datetime] = None,
                         end_dt: Optional[datetime] = None) -> Tuple[List[Dict], float]:
        """Get filtered bike data logs."""
        filter_desc = f"device_ids={device_ids}, start={start_dt}, end={end_dt}"
        self.log_debug(f"Retrieving filtered bike data logs: {filter_desc}", 
                      LogLevel.DEBUG, LogCategory.QUERY)
        
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            query = f"SELECT * FROM {TABLE_BIKE_DATA} WHERE 1=1"
            params = []
            
            if device_ids:
                placeholders = ",".join("?" for _ in device_ids)
                query += f" AND device_id IN ({placeholders})"
                params.extend(device_ids)
            
            if start_dt:
                query += " AND timestamp >= ?"
                params.append(start_dt)
            
            if end_dt:
                query += " AND timestamp <= ?"
                params.append(end_dt)
            
            query += " ORDER BY id DESC"
            cursor.execute(query, params)
            
            columns = [column[0] for column in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            # Calculate average for filtered data
            avg_query = f"SELECT AVG(roughness) FROM {TABLE_BIKE_DATA} WHERE 1=1"
            avg_params = []
            if device_ids:
                placeholders = ",".join("?" for _ in device_ids)
                avg_query += f" AND device_id IN ({placeholders})"
                avg_params.extend(device_ids)
            if start_dt:
                avg_query += " AND timestamp >= ?"
                avg_params.append(start_dt)
            if end_dt:
                avg_query += " AND timestamp <= ?"
                avg_params.append(end_dt)
            
            cursor.execute(avg_query, avg_params)
            avg_row = cursor.fetchone()
            rough_avg = float(avg_row[0]) if avg_row and avg_row[0] is not None else 0.0
            
            self.log_debug(f"Retrieved {len(rows)} filtered logs, avg roughness: {rough_avg}", 
                          LogLevel.DEBUG, LogCategory.QUERY)
            return rows, rough_avg
        except Exception as e:
            self.log_debug(f"Failed to retrieve filtered logs: {e}", 
                          LogLevel.ERROR, LogCategory.QUERY, include_stack=True)
            raise
        finally:
            conn.close()

    def get_device_ids_with_nicknames(self) -> List[Dict]:
        """Get list of unique device IDs with optional nicknames."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                SELECT DISTINCT bd.device_id, dn.nickname
                FROM {TABLE_BIKE_DATA} bd
                LEFT JOIN {TABLE_DEVICE_NICKNAMES} dn ON bd.device_id = dn.device_id
                """
            )
            return [
                {"id": row[0], "nickname": row[1]} for row in cursor.fetchall() if row[0]
            ]
        finally:
            conn.close()

    def get_date_range(self, device_ids: Optional[List[str]] = None) -> Tuple[Optional[str], Optional[str]]:
        """Get the oldest and newest timestamps, optionally filtered by device."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            query = f"SELECT MIN(timestamp), MAX(timestamp) FROM {TABLE_BIKE_DATA}"
            params = []
            if device_ids:
                placeholders = ",".join("?" for _ in device_ids)
                query += f" WHERE device_id IN ({placeholders})"
                params.extend(device_ids)
            
            cursor.execute(query, params)
            row = cursor.fetchone()
            start, end = row if row else (None, None)
            
            if start is not None:
                start_str = start.isoformat() if hasattr(start, "isoformat") else str(start)
            else:
                start_str = None
            if end is not None:
                end_str = end.isoformat() if hasattr(end, "isoformat") else str(end)
            else:
                end_str = None
            return start_str, end_str
        finally:
            conn.close()

    def set_device_nickname(self, device_id: str, nickname: str) -> None:
        """Set or update a nickname for a device."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            if self.use_sqlserver:
                cursor.execute(
                    f"""
                    MERGE {TABLE_DEVICE_NICKNAMES} AS target
                    USING (SELECT ? AS device_id, ? AS nickname) AS src
                    ON target.device_id = src.device_id
                    WHEN MATCHED THEN UPDATE SET nickname = src.nickname
                    WHEN NOT MATCHED THEN INSERT (device_id, nickname)
                    VALUES (src.device_id, src.nickname);
                    """,
                    device_id, nickname
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO RCI_device_nicknames (device_id, nickname)
                    VALUES (?, ?)
                    ON CONFLICT(device_id) DO UPDATE SET nickname=excluded.nickname
                    """,
                    (device_id, nickname)
                )
            conn.commit()
        finally:
            conn.close()

    def get_device_nickname(self, device_id: str) -> Optional[str]:
        """Get nickname for a device id."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT nickname FROM RCI_device_nicknames WHERE device_id = ?",
                device_id if self.use_sqlserver else (device_id,)
            )
            row = cursor.fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    def get_database_size(self) -> Tuple[float, Optional[float]]:
        """Return current database size and max size in GB."""
        try:
            if self.use_sqlserver:
                # Get database size in MB
                size_result = self.execute_scalar("SELECT SUM(CAST(size AS BIGINT)) * 8.0 / 1024 FROM sys.database_files")
                size_mb = float(size_result or 0)
                
                # Get max size - use string conversion to handle ODBC type issues
                max_size_result = self.execute_scalar("SELECT CAST(DATABASEPROPERTYEX(DB_NAME(), 'MaxSizeInBytes') AS NVARCHAR(50))")
                max_gb = None
                if max_size_result and max_size_result not in (None, -1, 0, '-1', '0'):
                    try:
                        max_bytes = int(str(max_size_result))
                        if max_bytes > 0:
                            max_gb = max_bytes / (1024 * 1024 * 1024)
                    except (ValueError, TypeError):
                        pass
            else:
                db_file = BASE_DIR / "RCI_local.db"
                size_mb = db_file.stat().st_size / (1024 * 1024)
                max_gb = None
            
            return size_mb, max_gb
        except Exception:
            # Return defaults if there's any error
            return 0.0, None

    def execute_query(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """Execute a query and return results as a list of dictionaries."""
        query_short = query[:100] + "..." if len(query) > 100 else query
        self.log_debug(f"Executing query: {query_short}", LogLevel.DEBUG, LogCategory.QUERY)
        
        try:
            with self.get_connection_context() as conn:
                cursor = conn.cursor()
                start_time = datetime.utcnow()
                
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                # Get column names
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                
                # Fetch all rows and convert to dictionaries
                rows = cursor.fetchall()
                result = [dict(zip(columns, row)) for row in rows] if columns else []
                
                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()
                self.log_debug(f"Query completed in {duration:.3f}s, returned {len(result)} rows", 
                              LogLevel.DEBUG, LogCategory.QUERY)
                return result
        except Exception as e:
            self.log_debug(f"Query failed: {query_short} - Error: {e}", 
                          LogLevel.ERROR, LogCategory.QUERY, include_stack=True)
            raise

    def execute_scalar(self, query: str, params: Optional[Tuple] = None) -> Any:
        """Execute a query and return a single scalar value."""
        query_short = query[:100] + "..." if len(query) > 100 else query
        self.log_debug(f"Executing scalar query: {query_short}", LogLevel.DEBUG, LogCategory.QUERY)
        
        try:
            with self.get_connection_context() as conn:
                start_time = datetime.utcnow()
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                result = cursor.fetchone()
                scalar_result = result[0] if result else None
                
                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()
                self.log_debug(f"Scalar query completed in {duration:.3f}s, result: {scalar_result}", 
                              LogLevel.DEBUG, LogCategory.QUERY)
                return scalar_result
        except Exception as e:
            self.log_debug(f"Scalar query failed: {query_short} - Error: {e}", 
                          LogLevel.ERROR, LogCategory.QUERY, include_stack=True)
            raise

    def execute_non_query(self, query: str, params: Optional[Tuple] = None) -> int:
        """Execute a non-query (INSERT, UPDATE, DELETE) and return affected rows."""
        import time
        start_time = time.time()
        
        # Only log for non-debug-log queries to avoid infinite recursion
        is_debug_log_query = TABLE_DEBUG_LOG in query
        
        if not is_debug_log_query:
            self.log_debug(f"Executing non-query: {query[:100]}{'...' if len(query) > 100 else ''}", 
                          LogLevel.DEBUG, LogCategory.QUERY)
        
        # Determine operation type
        operation_type = "UNKNOWN"
        query_upper = query.upper().strip()
        if query_upper.startswith("INSERT"):
            operation_type = "INSERT"
        elif query_upper.startswith("UPDATE"):
            operation_type = "UPDATE"
        elif query_upper.startswith("DELETE"):
            operation_type = "DELETE"
        elif query_upper.startswith("CREATE"):
            operation_type = "CREATE"
        elif query_upper.startswith("ALTER"):
            operation_type = "ALTER"
        elif query_upper.startswith("DROP"):
            operation_type = "DROP"
        
        try:
            with self.get_connection_context() as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                conn.commit()
                rowcount = cursor.rowcount if hasattr(cursor, 'rowcount') else 0
                
                execution_time = (time.time() - start_time) * 1000
                
                if not is_debug_log_query:
                    self.log_debug(f"Non-query executed successfully, {rowcount} rows affected", 
                                  LogLevel.DEBUG, LogCategory.QUERY)
                    
                    # Log SQL operation for auditing
                    self.log_sql_operation(
                        operation_type=operation_type,
                        query=query,
                        params=params,
                        result_count=rowcount,
                        execution_time_ms=execution_time,
                        success=True
                    )
                
                return rowcount
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            
            if not is_debug_log_query:
                self.log_debug(f"Non-query execution failed: {e}", 
                              LogLevel.ERROR, LogCategory.QUERY, include_stack=True)
                
                # Log failed SQL operation
                self.log_sql_operation(
                    operation_type=operation_type,
                    query=query,
                    params=params,
                    result_count=0,
                    execution_time_ms=execution_time,
                    success=False,
                    error_message=str(e)
                )
            raise

    def execute_management_operation(self, operation_name: str, operation_func):
        """Execute a management operation with proper error handling and logging."""
        self.log_debug(f"Starting management operation: {operation_name}", 
                      LogLevel.INFO, LogCategory.MANAGEMENT)
        try:
            result = operation_func()
            self.log_debug(f"Management operation '{operation_name}' completed successfully", 
                          LogLevel.INFO, LogCategory.MANAGEMENT)
            return result
        except Exception as exc:
            self.log_debug(f"Management operation '{operation_name}' failed: {exc}", 
                          LogLevel.ERROR, LogCategory.MANAGEMENT, include_stack=True)
            raise HTTPException(status_code=500, detail="Database error") from exc

    def test_table_operations(self, table_name: str) -> List[Dict[str, Any]]:
        """Test a table by inserting, reading, and deleting test records."""
        # Only allow tables that start with RCI_
        if not table_name.startswith("RCI_"):
            raise ValueError("Access denied: Only RCI_ tables are allowed")
            
        uid = datetime.utcnow().strftime("test_%Y%m%d%H%M%S%f")
        
        if table_name == TABLE_BIKE_DATA:
            # Insert test records
            for _ in range(2):
                self.execute_non_query(
                    f"""
                    INSERT INTO {TABLE_BIKE_DATA} (latitude, longitude, speed, direction, roughness, distance_m, device_id, ip_address)
                    VALUES (0, 0, 10, 0, 0, 0, ?, '0.0.0.0')
                    """,
                    (uid,)
                )
            
            # Read records
            rows = self.execute_query(
                f"SELECT id, device_id FROM {TABLE_BIKE_DATA} WHERE device_id = ?",
                (uid,)
            )
            
            # Delete test records
            self.execute_non_query(
                f"DELETE FROM {TABLE_BIKE_DATA} WHERE device_id = ?",
                (uid,)
            )
            
        elif table_name == TABLE_DEBUG_LOG:
            # Insert test records
            for _ in range(2):
                self.execute_non_query(
                    f"INSERT INTO {TABLE_DEBUG_LOG} (message) VALUES (?)",
                    (f"{uid} log",)
                )
            
            # Read records
            rows = self.execute_query(
                f"SELECT id, message FROM {TABLE_DEBUG_LOG} WHERE message LIKE ?",
                (f"{uid}%",)
            )
            
            # Delete test records
            self.execute_non_query(
                f"DELETE FROM {TABLE_DEBUG_LOG} WHERE message LIKE ?",
                (f"{uid}%",)
            )
            
        elif table_name == TABLE_DEVICE_NICKNAMES:
            # Insert test records
            for idx in range(2):
                self.execute_non_query(
                    f"""
                    INSERT INTO {TABLE_DEVICE_NICKNAMES} (device_id, nickname, user_agent, device_fp)
                    VALUES (?, 'Test Device', 'test_agent', 'test_fp')
                    """,
                    (f"{uid}_{idx}",)
                )
            
            # Read records
            rows = self.execute_query(
                f"SELECT device_id, nickname FROM {TABLE_DEVICE_NICKNAMES} WHERE device_id LIKE ?",
                (f"{uid}%",)
            )
            
            # Delete test records
            self.execute_non_query(
                f"DELETE FROM {TABLE_DEVICE_NICKNAMES} WHERE device_id LIKE ?",
                (f"{uid}%",)
            )
        else:
            raise ValueError("Unknown table")
            
        return rows

    def backup_table(self, table_name: str) -> str:
        """Create a backup copy of the given table and return the new table name."""
        # Only allow tables that start with RCI_
        if not table_name.startswith("RCI_"):
            raise ValueError("Access denied: Only RCI_ tables are allowed")
            
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        new_table = f"{table_name}_backup_{timestamp}"
        
        self.log_debug(f"Starting backup of table '{table_name}' to '{new_table}'", 
                      LogLevel.INFO, LogCategory.BACKUP)
        
        # Check if table exists
        if self.use_sqlserver:
            exists = self.execute_scalar(
                "SELECT 1 FROM sys.tables WHERE name = ?",
                (table_name,)
            )
        else:
            exists = self.execute_scalar(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,)
            )
        
        if not exists:
            error_msg = f"Table '{table_name}' does not exist"
            self.log_debug(error_msg, LogLevel.ERROR, LogCategory.BACKUP)
            raise ValueError("Unknown table")
        
        try:
            # Create backup
            if self.use_sqlserver:
                self.execute_non_query(f"SELECT * INTO {new_table} FROM {table_name}")
            else:
                self.execute_non_query(f"CREATE TABLE {new_table} AS SELECT * FROM {table_name}")
            
            self.log_debug(f"Successfully created backup table '{new_table}'", 
                          LogLevel.INFO, LogCategory.BACKUP)
            return new_table
        except Exception as e:
            self.log_debug(f"Failed to backup table '{table_name}': {e}", 
                          LogLevel.ERROR, LogCategory.BACKUP, include_stack=True)
            raise

    def archive_logs(self) -> Dict[str, Any]:
        """Move all debug logs from the main debug log table to an archive table."""
        self.log_debug("Starting debug log archiving operation", LogLevel.INFO, LogCategory.MANAGEMENT)
        
        try:
            # Get count of debug log records to be archived
            count_result = self.execute_scalar(f"SELECT COUNT(*) FROM {TABLE_DEBUG_LOG}")
            record_count = count_result if count_result else 0
            
            if record_count == 0:
                self.log_debug("No debug logs to archive", LogLevel.INFO, LogCategory.MANAGEMENT)
                return {
                    "status": "success",
                    "message": "No debug logs to archive",
                    "archived_count": 0
                }
            
            # Create archive table for debug logs if it doesn't exist
            archive_table_name = "RCI_debug_log_archive"
            
            if self.use_sqlserver:
                # SQL Server syntax
                create_archive_query = f"""
                    IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'{archive_table_name}') AND type in (N'U'))
                    CREATE TABLE {archive_table_name} (
                        id INT IDENTITY PRIMARY KEY,
                        timestamp DATETIME DEFAULT GETDATE(),
                        level NVARCHAR(20),
                        category NVARCHAR(50),
                        device_id NVARCHAR(100),
                        message NVARCHAR(4000),
                        stack_trace NVARCHAR(MAX)
                    )
                """
                archive_query = f"""
                    INSERT INTO {archive_table_name} 
                    (timestamp, level, category, device_id, message, stack_trace)
                    SELECT timestamp, level, category, device_id, message, stack_trace
                    FROM {TABLE_DEBUG_LOG}
                """
            else:
                # SQLite syntax
                create_archive_query = f"""
                    CREATE TABLE IF NOT EXISTS {archive_table_name} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        level TEXT,
                        category TEXT,
                        device_id TEXT,
                        message TEXT,
                        stack_trace TEXT
                    )
                """
                archive_query = f"""
                    INSERT INTO {archive_table_name} 
                    (timestamp, level, category, device_id, message, stack_trace)
                    SELECT timestamp, level, category, device_id, message, stack_trace
                    FROM {TABLE_DEBUG_LOG}
                """
            
            # Create archive table
            self.execute_non_query(create_archive_query)
            
            # Insert all debug logs into archive table
            self.execute_non_query(archive_query)
            
            # Clear the main debug log table
            self.execute_non_query(f"DELETE FROM {TABLE_DEBUG_LOG}")
            
            success_msg = f"Successfully archived {record_count} debug log entries to {archive_table_name}"
            self.log_debug(success_msg, LogLevel.INFO, LogCategory.MANAGEMENT)
            
            return {
                "status": "success",
                "message": success_msg,
                "archived_count": record_count
            }
            
        except Exception as e:
            error_msg = f"Failed to archive debug logs: {e}"
            self.log_debug(error_msg, LogLevel.ERROR, LogCategory.MANAGEMENT, include_stack=True)
            raise Exception(error_msg) from e

    def rename_table(self, old_name: str, new_name: str) -> None:
        """Rename a table."""
        # Only allow tables that start with RCI_
        if not old_name.startswith("RCI_") or not new_name.startswith("RCI_"):
            raise ValueError("Access denied: Only RCI_ tables are allowed")
            
        # Check if table exists
        if self.use_sqlserver:
            exists = self.execute_scalar(
                "SELECT 1 FROM sys.tables WHERE name = ?",
                (old_name,)
            )
        else:
            exists = self.execute_scalar(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (old_name,)
            )
        
        if not exists:
            raise ValueError("Unknown table")
        
        # Rename table
        if self.use_sqlserver:
            self.execute_non_query(f"EXEC sp_rename '{old_name}', '{new_name}'")
        else:
            self.execute_non_query(f"ALTER TABLE {old_name} RENAME TO {new_name}")

    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists."""
        # Only allow tables that start with RCI_
        if not table_name.startswith("RCI_"):
            return False
            
        if self.use_sqlserver:
            return bool(self.execute_scalar(
                "SELECT 1 FROM sys.tables WHERE name = ?",
                (table_name,)
            ))
        else:
            return bool(self.execute_scalar(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,)
            ))

    def get_table_summary(self) -> List[Dict[str, Any]]:
        """Get summary information for RCI tables including row count and last update."""
        import re
        
        name_re = re.compile(r"^RCI_[A-Za-z0-9_]+$")  # Only allow RCI_ prefixed tables
        tables = []
        
        # Get all RCI table names
        if self.use_sqlserver:
            table_names = self.execute_query("SELECT name FROM sys.tables WHERE name LIKE 'RCI_%'")
            names = [row['name'] for row in table_names]
        else:
            table_names = self.execute_query("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'RCI_%'")
            names = [row['name'] for row in table_names]
        
        for table in names:
            if not name_re.match(table):
                continue  # Skip any table that doesn't match RCI_* pattern
                continue
                
            try:
                # Get column information
                if self.use_sqlserver:
                    cols_result = self.execute_query(f"SELECT TOP 0 * FROM {table}")
                else:
                    cols_result = self.execute_query(f"SELECT * FROM {table} LIMIT 0")
                
                cols = list(cols_result[0].keys()) if cols_result else []
                
                # Get row count
                count = self.execute_scalar(f"SELECT COUNT(*) FROM {table}")
                count = int(count or 0)
                
                # Get last update timestamp if available
                last_update = None
                if "timestamp" in cols:
                    if self.use_sqlserver:
                        last_ts = self.execute_scalar(f"SELECT TOP 1 timestamp FROM {table} ORDER BY timestamp DESC")
                    else:
                        last_ts = self.execute_scalar(f"SELECT timestamp FROM {table} ORDER BY timestamp DESC LIMIT 1")
                    
                    if last_ts:
                        last_update = last_ts.isoformat() if hasattr(last_ts, 'isoformat') else str(last_ts)
                
                tables.append({
                    "name": table, 
                    "count": count, 
                    "last_update": last_update
                })
                
            except Exception:
                # Skip tables that can't be accessed
                continue
        
        return tables

    def get_last_table_rows(self, table_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the latest rows from a table."""
        import re
        
        name_re = re.compile(r"^[A-Za-z0-9_]+$")
        if not name_re.match(table_name):
            raise ValueError("Invalid table name")
        
        # Only allow tables that start with RCI_
        if not table_name.startswith("RCI_"):
            raise ValueError("Access denied: Only RCI_ tables are allowed")
        
        # Get column information to determine ordering
        if self.use_sqlserver:
            cols_result = self.execute_query(f"SELECT TOP 0 * FROM {table_name}")
        else:
            cols_result = self.execute_query(f"SELECT * FROM {table_name} LIMIT 0")
        
        cols = list(cols_result[0].keys()) if cols_result else []
        
        # Determine ordering column
        order_col = "timestamp" if "timestamp" in cols else ("id" if "id" in cols else None)
        
        # Build query
        if order_col:
            if self.use_sqlserver:
                query = f"SELECT TOP {limit} * FROM {table_name} ORDER BY {order_col} DESC"
                rows = self.execute_query(query)
            else:
                query = f"SELECT * FROM {table_name} ORDER BY {order_col} DESC LIMIT ?"
                rows = self.execute_query(query, (limit,))
        else:
            if self.use_sqlserver:
                query = f"SELECT TOP {limit} * FROM {table_name}"
                rows = self.execute_query(query)
            else:
                query = f"SELECT * FROM {table_name} LIMIT ?"
                rows = self.execute_query(query, (limit,))
        
        return rows


# Global database manager instance
db_manager = DatabaseManager()

# Utility functions for easy access to logging functionality
def set_log_level(level: LogLevel) -> None:
    """Set the global log level for the database manager."""
    db_manager.set_log_level(level)

def set_log_categories(categories: List[LogCategory]) -> None:
    """Set which log categories to record for the database manager."""
    db_manager.set_log_categories(categories)

def get_debug_logs(level_filter: Optional[LogLevel] = None,
                  category_filter: Optional[LogCategory] = None,
                  device_id_filter: Optional[str] = None,
                  limit: Optional[int] = 100) -> List[Dict[str, Any]]:
    """Get debug logs with filtering."""
    return db_manager.get_debug_logs(level_filter, category_filter, device_id_filter, limit)
