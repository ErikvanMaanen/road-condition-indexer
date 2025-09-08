"""Logging utilities for Road Condition Indexer.

This module centralizes all logging functionality including:
- Log levels and categories
- Database logging operations (stored in UTC)
- Time formatting utilities (displayed in Europe/Amsterdam timezone)
- JavaScript logging functions for frontend

All logs are stored with UTC timestamps and displayed in Europe/Amsterdam timezone
using a short format (MM/DD HH:MM:SS).
"""

import json
import logging
import os
import time
import traceback
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import pytz

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available, continue without it
    pass

# Log levels and categories for filtering
class LogLevel(Enum):
    """Debug log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class LogCategory(Enum):
    """Debug log categories for filtering."""
    DATABASE = "DATABASE"
    CONNECTION = "CONNECTION"
    QUERY = "QUERY"
    MANAGEMENT = "MANAGEMENT"
    MIGRATION = "MIGRATION"
    BACKUP = "BACKUP"
    GENERAL = "GENERAL"
    STARTUP = "STARTUP"
    USER_ACTION = "USER_ACTION"
    SQL_OPERATION = "SQL_OPERATION"

# Global debug log list for compatibility
DEBUG_LOG = []

def get_utc_timestamp() -> str:
    """Get current UTC timestamp in ISO format for database storage (timezone-aware)."""
    return datetime.now(UTC).isoformat()

def format_display_time(utc_timestamp: Optional[str] = None) -> str:
    """Convert UTC timestamp to short Amsterdam time format for display (MM/DD HH:MM:SS)."""
    try:
        if utc_timestamp is None:
            utc_time = datetime.now(UTC)
        else:
            utc_time = datetime.fromisoformat(utc_timestamp.replace('Z', ''))
        
        # Convert to Amsterdam time
        if utc_time.tzinfo is None:
            utc_time = utc_time.replace(tzinfo=pytz.UTC)
        amsterdam_tz = pytz.timezone('Europe/Amsterdam')
        amsterdam_time = utc_time.astimezone(amsterdam_tz)
        
        # Return short format: MM/DD HH:MM:SS
        return amsterdam_time.strftime('%m/%d %H:%M:%S')
    except Exception:
        # Fallback to current UTC time in short format
        return datetime.now(UTC).strftime('%m/%d %H:%M:%S')

def log_debug(message: str, device_id: Optional[str] = None) -> None:
    """Log a debug message. Stores in UTC, displays in Amsterdam time."""
    from database import db_manager  # Import here to avoid circular imports
    
    utc_timestamp = get_utc_timestamp()
    display_time = format_display_time(utc_timestamp)
    formatted_message = f"{display_time} - {message}"
    
    # Add device ID to message if provided
    if device_id:
        formatted_message = f"{display_time} - [DEVICE:{device_id}] {message}"
    
    DEBUG_LOG.append(formatted_message)
    
    # Print to console for immediate debugging
    print(f"DEBUG: {formatted_message}")
    
    # Keep only last 100 messages
    if len(DEBUG_LOG) > 100:
        del DEBUG_LOG[:-100]
        
    # Log to database with appropriate level
    try:
        lower_msg = message.lower()
        if 'error' in lower_msg or 'exception' in lower_msg or '❌' in message:
            db_manager.log_debug(message, LogLevel.ERROR, LogCategory.GENERAL, device_id=device_id)
        else:
            db_manager.log_debug(message, LogLevel.DEBUG, LogCategory.GENERAL, device_id=device_id)
    except Exception as db_log_exc:
        print(f"DB_LOG_ERROR: Failed to log to database: {db_log_exc}")

def log_info(message: str, category: LogCategory = LogCategory.GENERAL, device_id: Optional[str] = None) -> None:
    """Log an info message."""
    from database import db_manager  # Import here to avoid circular imports
    db_manager.log_debug(message, LogLevel.INFO, category, device_id=device_id)

def log_warning(message: str, category: LogCategory = LogCategory.GENERAL, device_id: Optional[str] = None) -> None:
    """Log a warning message."""
    from database import db_manager  # Import here to avoid circular imports
    db_manager.log_debug(message, LogLevel.WARNING, category, device_id=device_id)

def log_error(message: str, category: LogCategory = LogCategory.GENERAL, include_stack: bool = True, device_id: Optional[str] = None) -> None:
    """Log an error message."""
    from database import db_manager  # Import here to avoid circular imports
    db_manager.log_debug(message, LogLevel.ERROR, category, include_stack, device_id=device_id)

def get_debug_logs(level_filter: Optional[LogLevel] = None,
                  category_filter: Optional[LogCategory] = None,
                  device_id_filter: Optional[str] = None,
                  limit: Optional[int] = 100) -> List[Dict[str, Any]]:
    """Get debug logs with filtering."""
    from database import db_manager  # Import here to avoid circular imports
    return db_manager.get_debug_logs(level_filter, category_filter, device_id_filter, limit)

# Additional utility functions for log management
def add_debug_message(message: str, category: LogCategory = LogCategory.GENERAL, level: LogLevel = LogLevel.DEBUG, device_id: Optional[str] = None) -> None:
    """Add a debug message to the system (Python equivalent of addDebug)."""
    from database import db_manager
    db_manager.log_debug(message, level, category, device_id=device_id)

def clear_debug_logs() -> None:
    """Clear all debug logs from memory (Python equivalent of clearAllMessages)."""
    global DEBUG_LOG
    DEBUG_LOG.clear()

def export_debug_logs(level_filter: Optional[LogLevel] = None, category_filter: Optional[LogCategory] = None, device_id_filter: Optional[str] = None) -> str:
    """Export debug logs as CSV format (Python equivalent of exportMessages)."""
    logs = get_debug_logs(level_filter, category_filter, device_id_filter)
    csv_lines = ['UTC Timestamp,Display Time,Level,Category,Device ID,Message']
    
    for log in logs:
        # Escape quotes in message
        message = str(log.get('message', '')).replace('"', '""')
        csv_line = f'"{log.get("timestamp", "")}","{log.get("display_time", "")}","{log.get("level", "")}","{log.get("category", "")}","{log.get("device_id", "")}","{message}"'
        csv_lines.append(csv_line)
    
    return '\n'.join(csv_lines)

# Export the DEBUG_LOG for compatibility
__all__ = [
    'LogLevel',
    'LogCategory', 
    'DEBUG_LOG',
    'get_utc_timestamp',
    'format_display_time',
    'log_debug',
    'log_info',
    'log_warning', 
    'log_error',
    'get_debug_logs',
    'add_debug_message',
    'clear_debug_logs',
    'export_debug_logs'
]
