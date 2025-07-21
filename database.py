"""Database management module for Road Condition Indexer.

This module handles all database operations including:
- Database connection management
- Table creation and schema updates
- Data access layer for bike data, debug logs, and device nicknames
"""

import os
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

try:
    import pyodbc
except ImportError:
    pyodbc = None

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

# Base directory for the application
BASE_DIR = Path(__file__).resolve().parent

# Determine if we should use SQL Server based on environment variables
USE_SQLSERVER = all(
    os.getenv(var)
    for var in (
        "AZURE_SQL_SERVER",
        "AZURE_SQL_PORT",
        "AZURE_SQL_USER",
        "AZURE_SQL_PASSWORD",
        "AZURE_SQL_DATABASE",
    )
) and pyodbc is not None and bool(pyodbc.drivers())


class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self):
        self.use_sqlserver = USE_SQLSERVER
    
    def get_connection(self, database: Optional[str] = None):
        """Return a database connection.

        When the required Azure SQL environment variables are present the
        connection uses ``pyodbc``. Otherwise a local SQLite database named
        ``RCI_local.db`` in the project directory is used. This makes the API usable
        without any external dependencies.
        """
        if self.use_sqlserver:
            server = os.getenv("AZURE_SQL_SERVER")
            port = os.getenv("AZURE_SQL_PORT")
            user = os.getenv("AZURE_SQL_USER")
            password = os.getenv("AZURE_SQL_PASSWORD")
            db_name = database or os.getenv("AZURE_SQL_DATABASE")
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={server},{port};"
                f"DATABASE={db_name};"
                f"UID={user};"
                f"PWD={password}"
            )
            return pyodbc.connect(conn_str)
        # SQLite fallback
        db_file = BASE_DIR / "RCI_local.db"
        return sqlite3.connect(db_file)

    def ensure_database_exists(self) -> None:
        """Ensure the configured database exists."""
        if self.use_sqlserver:
            server = os.getenv("AZURE_SQL_SERVER")
            port = os.getenv("AZURE_SQL_PORT")
            user = os.getenv("AZURE_SQL_USER")
            password = os.getenv("AZURE_SQL_PASSWORD")
            database = os.getenv("AZURE_SQL_DATABASE")

            conn = self.get_connection("master")
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT database_id FROM sys.databases WHERE name = ?",
                    database,
                )
                if not cursor.fetchone():
                    cursor.execute(f"CREATE DATABASE [{database}]")
                    conn.commit()
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
        else:
            # SQLite creates the database file automatically
            db_file = BASE_DIR / "RCI_local.db"
            db_file.touch(exist_ok=True)

    def init_tables(self) -> None:
        """Ensure that required tables exist."""
        try:
            self.ensure_database_exists()
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if self.use_sqlserver:
                self._create_sqlserver_tables(cursor)
            else:
                self._create_sqlite_tables(cursor)
            
            conn.commit()
        except Exception as exc:
            raise Exception(f"Database init error: {exc}")
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _create_sqlserver_tables(self, cursor):
        """Create tables for SQL Server."""
        # Create bike data table
        cursor.execute(
            f"""
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
            """
        )
        
        # Create debug log table
        cursor.execute(
            f"""
            IF NOT EXISTS (
                SELECT 1 FROM sys.tables WHERE name = '{TABLE_DEBUG_LOG}'
            )
            BEGIN
                CREATE TABLE {TABLE_DEBUG_LOG} (
                    id INT IDENTITY PRIMARY KEY,
                    timestamp DATETIME DEFAULT GETDATE(),
                    message NVARCHAR(4000)
                )
            END
            """
        )
        
        # Create device nicknames table
        cursor.execute(
            f"""
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
            """
        )
        
        # Schema migration statements
        self._apply_sqlserver_migrations(cursor)

    def _apply_sqlserver_migrations(self, cursor):
        """Apply schema migrations for SQL Server."""
        # Add ip_address column if it doesn't exist
        cursor.execute(
            f"""
            IF COL_LENGTH('{TABLE_BIKE_DATA}', 'ip_address') IS NULL
                ALTER TABLE {TABLE_BIKE_DATA} ADD ip_address NVARCHAR(45)
            """
        )
        
        # Remove old user_agent column from bike_data
        cursor.execute(
            f"""
            IF COL_LENGTH('{TABLE_BIKE_DATA}', 'user_agent') IS NOT NULL
                ALTER TABLE {TABLE_BIKE_DATA} DROP COLUMN user_agent
            """
        )
        
        # Remove old device_fp column from bike_data
        cursor.execute(
            f"""
            IF COL_LENGTH('{TABLE_BIKE_DATA}', 'device_fp') IS NOT NULL
                ALTER TABLE {TABLE_BIKE_DATA} DROP COLUMN device_fp
            """
        )
        
        # Add distance_m column if it doesn't exist
        cursor.execute(
            f"""
            IF COL_LENGTH('{TABLE_BIKE_DATA}', 'distance_m') IS NULL
                ALTER TABLE {TABLE_BIKE_DATA} ADD distance_m FLOAT
            """
        )
        
        # Remove old version column
        cursor.execute(
            f"""
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
        )
        
        # Add columns to device_nicknames if they don't exist
        cursor.execute(
            f"""
            IF COL_LENGTH('{TABLE_DEVICE_NICKNAMES}', 'user_agent') IS NULL
                ALTER TABLE {TABLE_DEVICE_NICKNAMES} ADD user_agent NVARCHAR(256)
            """
        )
        cursor.execute(
            f"""
            IF COL_LENGTH('{TABLE_DEVICE_NICKNAMES}', 'device_fp') IS NULL
                ALTER TABLE {TABLE_DEVICE_NICKNAMES} ADD device_fp NVARCHAR(256)
            """
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
                message TEXT
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

    def log_debug(self, message: str) -> None:
        """Insert a debug message into the debug log table."""
        timestamp = datetime.utcnow().isoformat()
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                f"INSERT INTO {TABLE_DEBUG_LOG} (message) VALUES (?)",
                f"{timestamp} - {message}"
            )
            conn.commit()
        except Exception:
            pass
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def insert_bike_data(self, latitude: float, longitude: float, speed: float, 
                        direction: float, roughness: float, distance_m: float,
                        device_id: str, ip_address: Optional[str]) -> None:
        """Insert bike data into the database."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                f"INSERT INTO {TABLE_BIKE_DATA} (latitude, longitude, speed, direction, roughness, distance_m, device_id, ip_address)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (latitude, longitude, speed, direction, roughness, distance_m, device_id, ip_address)
            )
            if self.use_sqlserver and cursor.rowcount != 1:
                raise Exception(f"Insert affected {cursor.rowcount} rows")
            conn.commit()
        finally:
            conn.close()

    def upsert_device_info(self, device_id: str, user_agent: Optional[str], 
                          device_fp: Optional[str]) -> None:
        """Insert or update device information."""
        conn = self.get_connection()
        try:
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
                    device_id, user_agent, device_fp
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
        finally:
            conn.close()

    def get_last_bike_data_point(self, device_id: str) -> Optional[Tuple[datetime, float, float]]:
        """Get the last recorded bike data point for a device."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            if self.use_sqlserver:
                cursor.execute(
                    f"SELECT TOP 1 latitude, longitude, timestamp FROM {TABLE_BIKE_DATA} WHERE device_id = ? ORDER BY id DESC",
                    device_id
                )
            else:
                cursor.execute(
                    f"SELECT latitude, longitude, timestamp FROM {TABLE_BIKE_DATA} WHERE device_id = ? ORDER BY id DESC LIMIT 1",
                    (device_id,)
                )
            row = cursor.fetchone()
            if row:
                return (row[2], row[0], row[1])  # timestamp, latitude, longitude
            return None
        finally:
            conn.close()

    def get_logs(self, limit: Optional[int] = None) -> Tuple[List[Dict], float]:
        """Get bike data logs with optional limit."""
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
            
            return rows, rough_avg
        finally:
            conn.close()

    def get_filtered_logs(self, device_ids: Optional[List[str]] = None,
                         start_dt: Optional[datetime] = None,
                         end_dt: Optional[datetime] = None) -> Tuple[List[Dict], float]:
        """Get filtered bike data logs."""
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
            
            return rows, rough_avg
        finally:
            conn.close()

    def get_device_ids_with_nicknames(self) -> List[Dict]:
        """Get list of unique device IDs with optional nicknames."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
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
            
            start_str = start.isoformat() if start else None
            end_str = end.isoformat() if end else None
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
        conn = None
        try:
            if self.use_sqlserver:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT SUM(size) * 8.0 / 1024 FROM sys.database_files")
                size_mb = float(cursor.fetchone()[0] or 0)
                cursor.execute("SELECT DATABASEPROPERTYEX(DB_NAME(), 'MaxSizeInBytes')")
                max_bytes = cursor.fetchone()[0]
                max_gb = None
                if max_bytes not in (None, -1, 0):
                    max_gb = max_bytes / (1024 * 1024 * 1024)
            else:
                db_file = BASE_DIR / "RCI_local.db"
                size_mb = db_file.stat().st_size / (1024 * 1024)
                max_gb = None
            
            return size_mb, max_gb
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

    def execute_query(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """Execute a query and return results as a list of dictionaries."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Get column names
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            
            # Fetch all rows and convert to dictionaries
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows] if columns else []
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def execute_scalar(self, query: str, params: Optional[Tuple] = None) -> Any:
        """Execute a query and return a single scalar value."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def execute_non_query(self, query: str, params: Optional[Tuple] = None) -> int:
        """Execute a non-query (INSERT, UPDATE, DELETE) and return affected rows."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            return cursor.rowcount if hasattr(cursor, 'rowcount') else 0
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def execute_management_operation(self, operation_name: str, operation_func):
        """Execute a management operation with proper error handling and logging."""
        try:
            result = operation_func()
            self.log_debug(f"Management operation '{operation_name}' completed successfully")
            return result
        except Exception as exc:
            self.log_debug(f"Management operation '{operation_name}' failed: {exc}")
            raise HTTPException(status_code=500, detail="Database error") from exc

    def test_table_operations(self, table_name: str) -> List[Dict[str, Any]]:
        """Test a table by inserting, reading, and deleting test records."""
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
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        new_table = f"{table_name}_backup_{timestamp}"
        
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
            raise ValueError("Unknown table")
        
        # Create backup
        if self.use_sqlserver:
            self.execute_non_query(f"SELECT * INTO {new_table} FROM {table_name}")
        else:
            self.execute_non_query(f"CREATE TABLE {new_table} AS SELECT * FROM {table_name}")
        
        return new_table

    def rename_table(self, old_name: str, new_name: str) -> None:
        """Rename a table."""
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
        """Get summary information for all tables including row count and last update."""
        import re
        
        name_re = re.compile(r"^[A-Za-z0-9_]+$")
        tables = []
        
        # Get all table names
        if self.use_sqlserver:
            table_names = self.execute_query("SELECT name FROM sys.tables")
            names = [row['name'] for row in table_names]
        else:
            table_names = self.execute_query("SELECT name FROM sqlite_master WHERE type='table'")
            names = [row['name'] for row in table_names]
        
        for table in names:
            if not name_re.match(table):
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
