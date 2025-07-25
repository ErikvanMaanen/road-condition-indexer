"""Logging utilities for Road Condition Indexer.

This module centralizes all logging functionality including:
- Log levels and categories
- Database logging operations
- Time formatting utilities
- JavaScript logging functions for frontend
"""

import os
import json
import logging
import traceback
import time
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
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

def get_dutch_time(utc_time: datetime = None) -> str:
    """Convert UTC time to Dutch time (Europe/Amsterdam) with daylight saving."""
    try:
        if utc_time is None:
            utc_time = datetime.utcnow()
        
        # Set UTC timezone
        utc_time = utc_time.replace(tzinfo=pytz.UTC)
        
        # Convert to Dutch time
        dutch_tz = pytz.timezone('Europe/Amsterdam')
        dutch_time = utc_time.astimezone(dutch_tz)
        
        return dutch_time.isoformat()
    except Exception:
        # Fallback to UTC if timezone conversion fails
        return (utc_time or datetime.utcnow()).isoformat()

def _get_dutch_time_for_db(utc_time: datetime = None, use_sqlserver: bool = False) -> str:
    """Convert UTC time to Dutch time (Europe/Amsterdam) with daylight saving for database storage."""
    try:
        if utc_time is None:
            utc_time = datetime.utcnow()
        
        # Set UTC timezone
        utc_time = utc_time.replace(tzinfo=pytz.UTC)
        
        # Convert to Dutch time
        dutch_tz = pytz.timezone('Europe/Amsterdam')
        dutch_time = utc_time.astimezone(dutch_tz)
        
        # Return format compatible with SQL Server (remove timezone info)
        if use_sqlserver:
            return dutch_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]  # SQL Server likes milliseconds, not microseconds
        else:
            return dutch_time.isoformat()
    except Exception:
        # Fallback to UTC if timezone conversion fails
        fallback_time = utc_time or datetime.utcnow()
        if use_sqlserver:
            return fallback_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        else:
            return fallback_time.isoformat()

def log_debug(message: str, device_id: Optional[str] = None) -> None:
    """Append message to debug log with timestamp. If message contains 'error' or 'exception', log as error in DB."""
    from database import db_manager  # Import here to avoid circular imports
    
    timestamp = get_dutch_time()
    formatted_message = f"{timestamp} - {message}"
    
    # Add device ID to message if provided
    if device_id:
        formatted_message = f"{timestamp} - [DEVICE:{device_id}] {message}"
    
    DEBUG_LOG.append(formatted_message)
    
    # Also print to console for immediate debugging (can be removed in production)
    print(f"DEBUG: {formatted_message}")
    
    # keep only last 100 messages
    if len(DEBUG_LOG) > 100:
        del DEBUG_LOG[:-100]
        
    # Log to DB as error if message contains 'error' or 'exception', else as debug
    try:
        lower_msg = message.lower()
        if 'error' in lower_msg or 'exception' in lower_msg or '❌' in message:
            log_error(message, device_id=device_id)
        else:
            db_manager.log_debug(message, LogLevel.DEBUG, LogCategory.GENERAL, device_id=device_id)
    except Exception as db_log_exc:
        # If database logging fails, at least we have console output
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

# JavaScript logging functions for frontend
JAVASCRIPT_LOGGING_FUNCTIONS = """
// JavaScript logging functions for frontend

function formatDutchTime(isoString) {
    try {
        const date = new Date(isoString);
        return date.toLocaleString('nl-NL', {
            timeZone: 'Europe/Amsterdam',
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    } catch (error) {
        return isoString; // Fallback to original string
    }
}

function formatShortDateTime() {
    const now = new Date();
    const cesTime = new Date(now.toLocaleString("en-US", {timeZone: "Europe/Amsterdam"}));
    const month = String(cesTime.getMonth() + 1).padStart(2, '0');
    const day = String(cesTime.getDate()).padStart(2, '0');
    const hours = String(cesTime.getHours()).padStart(2, '0');
    const minutes = String(cesTime.getMinutes()).padStart(2, '0');
    const seconds = String(cesTime.getSeconds()).padStart(2, '0');
    return `${month}/${day} ${hours}:${minutes}:${seconds}`;
}

// Enhanced logging functions with device ID support
let allLogMessages = [];
let deviceId = '';

// Initialize device ID from localStorage or generate new one
function initializeDeviceId() {
    deviceId = localStorage.getItem('deviceId') || '';
    if (!deviceId) {
        deviceId = crypto.randomUUID ? crypto.randomUUID() : 'unknown-' + Date.now();
        localStorage.setItem('deviceId', deviceId);
    }
    // Take only last 8 characters for display
    deviceId = deviceId.slice(-8);
}

// Add message to activity log (simple display)
function addLog(msg) {
    const div = document.getElementById('log');
    if (div) {
        const shortTime = formatShortDateTime();
        div.textContent += `${shortTime} - ${msg}\\n`;
        div.scrollTop = div.scrollHeight;
    }
    // Also add to all messages with INFO level
    addMessage(msg, 'INFO', 'General');
}

// Add debug message (legacy function for compatibility)
function addDebug(msg, category = 'Debug', level = 'DEBUG') {
    addMessage(msg, level, category);
}

// Add message to all messages with full details
function addMessage(msg, level = 'INFO', category = 'General') {
    const timestamp = formatShortDateTime();
    const logEntry = {
        timestamp: timestamp,
        level: level,
        category: category,
        message: msg,
        deviceId: deviceId
    };
    
    allLogMessages.push(logEntry);
    
    // Limit to last 1000 messages to prevent memory issues
    if (allLogMessages.length > 1000) {
        allLogMessages = allLogMessages.slice(-1000);
    }
    
    if (typeof updateDebugDisplay === 'function') {
        updateDebugDisplay();
    }
    if (typeof updateLogStats === 'function') {
        updateLogStats();
    }
}

// Clear all log messages
function clearAllMessages() {
    allLogMessages = [];
    if (typeof updateDebugDisplay === 'function') {
        updateDebugDisplay();
    }
    if (typeof updateLogStats === 'function') {
        updateLogStats();
    }
}

// Export messages to CSV
function exportMessages() {
    const levelFilter = document.getElementById('log-level-filter')?.value || '';
    const categoryFilter = document.getElementById('log-category-filter')?.value || '';
    
    let filteredMessages = allLogMessages;
    
    if (levelFilter) {
        filteredMessages = filteredMessages.filter(msg => msg.level === levelFilter);
    }
    
    if (categoryFilter) {
        filteredMessages = filteredMessages.filter(msg => msg.category === categoryFilter);
    }
    
    const csvContent = 'Timestamp,Level,Category,Device ID,Message\\n' +
        filteredMessages.map(msg => 
            `"${msg.timestamp}","${msg.level}","${msg.category}","${msg.deviceId}","${msg.message.replace(/"/g, '""')}"`
        ).join('\\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const timestamp = formatShortDateTime().replace(/[\\/:\\s]/g, '-');
    a.download = `log-messages-${timestamp}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
}

// Toggle logs visibility
function toggleLogs() {
    const logsSection = document.getElementById('logs');
    const toggleButton = document.getElementById('toggle-logs');
    
    if (logsSection && toggleButton) {
        if (logsSection.style.display === 'none') {
            logsSection.style.display = 'block';
            toggleButton.textContent = 'Hide Logs';
        } else {
            logsSection.style.display = 'none';
            toggleButton.textContent = 'Show Logs';
        }
    }
}

// Fallback logging functions for when partial doesn't load
function createFallbackLogFunctions() {
    if (!window.addLog) {
        window.addLog = function(msg) {
            console.log('Log:', msg);
        };
    }
    if (!window.addDebug) {
        window.addDebug = function(msg, category = 'Debug', level = 'DEBUG') {
            console.log(`Debug [${level}] [${category}]:`, msg);
        };
    }
    if (!window.addMessage) {
        window.addMessage = function(msg, level = 'INFO', category = 'General') {
            console.log(`Message [${level}] [${category}]:`, msg);
        };
    }
    if (!window.toggleLogs) {
        window.toggleLogs = function() {
            console.log('Logs toggle requested but partial not loaded');
        };
    }
}

// Initialize device ID when script loads
initializeDeviceId();
"""

def get_javascript_logging_functions() -> str:
    """Return JavaScript logging functions for embedding in HTML files."""
    return JAVASCRIPT_LOGGING_FUNCTIONS

# Export the DEBUG_LOG for compatibility
__all__ = [
    'LogLevel',
    'LogCategory', 
    'DEBUG_LOG',
    'get_dutch_time',
    'log_debug',
    'log_info',
    'log_warning', 
    'log_error',
    'get_debug_logs',
    'get_javascript_logging_functions',
    '_get_dutch_time_for_db'
]
