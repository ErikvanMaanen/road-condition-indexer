# Enhanced Logging Documentation

## Overview

The Road Condition Indexer now includes a comprehensive logging system with filtering capabilities, categorization, and efficient error handling throughout all database operations.

## Features

### 1. Log Levels
The system supports five log levels in order of severity:
- `DEBUG`: Detailed information for debugging
- `INFO`: General information about system operation
- `WARNING`: Warning messages for potential issues
- `ERROR`: Error conditions that need attention
- `CRITICAL`: Critical errors that may cause system failure

### 2. Log Categories
Logs are categorized for better organization and filtering:
- `GENERAL`: General application messages
- `DATABASE`: Database-related operations
- `CONNECTION`: Database connection events
- `QUERY`: SQL query execution details
- `MANAGEMENT`: Management operations
- `MIGRATION`: Database schema migrations
- `BACKUP`: Backup and restore operations

### 3. Enhanced Database Logging

All database operations now include comprehensive logging:
- Connection establishment and teardown
- Query execution with timing information
- Error handling with stack traces
- Data insertion and retrieval operations
- Management operations tracking

## API Endpoints

### Enhanced Debug Log Retrieval
```
GET /debuglog/enhanced?level=INFO&category=QUERY&device_id=device123&limit=100
```

Parameters:
- `level` (optional): Minimum log level to retrieve
- `category` (optional): Filter by specific category
- `device_id` (optional): Filter by specific device ID
- `limit` (optional): Maximum number of logs (default: 100)

### Log Configuration Management
```
POST /manage/log_config
{
  "level": "INFO",
  "categories": ["DATABASE", "QUERY", "MANAGEMENT"]
}
```

```
GET /manage/log_config
```

### Clear Debug Logs
```
DELETE /manage/debug_logs
```

## Programming Interface

### Basic Logging
```python
from database import log_info, log_warning, log_error

log_info("Application started successfully")
log_warning("Low disk space detected")
log_error("Failed to connect to external service")

# With device context
log_info("Data processed successfully", device_id="device123")
log_error("Upload failed", device_id="device456")
```

### Advanced Logging with Categories
```python
from database import DatabaseManager, LogLevel, LogCategory

db = DatabaseManager()
db.log_debug("Query executed in 0.15s", LogLevel.INFO, LogCategory.QUERY)
db.log_debug("Connection pool exhausted", LogLevel.WARNING, LogCategory.CONNECTION)
db.log_debug("Migration failed", LogLevel.ERROR, LogCategory.MIGRATION, include_stack=True)

# With device context
db.log_debug("Data inserted successfully", LogLevel.INFO, LogCategory.DATABASE, device_id="device123")
db.log_debug("Connection timeout", LogLevel.WARNING, LogCategory.CONNECTION, device_id="device456")
```

### Configuration
```python
from database import DatabaseManager, LogLevel, LogCategory

# Initialize with custom log level and categories
db = DatabaseManager(
    log_level=LogLevel.WARNING,
    log_categories=[LogCategory.DATABASE, LogCategory.QUERY]
)

# Change configuration at runtime
db.set_log_level(LogLevel.INFO)
db.set_log_categories([LogCategory.GENERAL, LogCategory.MANAGEMENT])
```

### Retrieving Logs
```python
from database import get_debug_logs, LogLevel, LogCategory

# Get all logs
all_logs = get_debug_logs()

# Filter by level (ERROR and above)
error_logs = get_debug_logs(level_filter=LogLevel.ERROR)

# Filter by category
query_logs = get_debug_logs(category_filter=LogCategory.QUERY)

# Filter by device ID
device_logs = get_debug_logs(device_id_filter="device123")

# Combined filtering with limit
recent_errors = get_debug_logs(
    level_filter=LogLevel.ERROR,
    category_filter=LogCategory.DATABASE,
    device_id_filter="device123",
    limit=50
)
```

## Database Schema

The enhanced logging system uses an updated debug log table schema:

### SQL Server
```sql
CREATE TABLE RCI_debug_log (
    id INT IDENTITY PRIMARY KEY,
    timestamp DATETIME DEFAULT GETDATE(),
    level NVARCHAR(20),
    category NVARCHAR(50),
    device_id NVARCHAR(100),
    message NVARCHAR(4000),
    stack_trace NVARCHAR(MAX)
)
```

### SQLite
```sql
CREATE TABLE RCI_debug_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    level TEXT,
    category TEXT,
    device_id TEXT,
    message TEXT,
    stack_trace TEXT
)
```

## Performance Considerations

1. **Efficient Filtering**: Log filtering is performed at the database level using SQL WHERE clauses
2. **Stack Trace Optimization**: Stack traces are only captured for ERROR and CRITICAL levels by default
3. **Query Timing**: All database queries include execution timing for performance monitoring
4. **Circular Logging**: The in-memory debug log is limited to 100 entries to prevent memory issues

## Best Practices

1. **Use Appropriate Log Levels**:
   - DEBUG for detailed debugging information
   - INFO for normal operation messages
   - WARNING for potential issues
   - ERROR for actual errors that need attention
   - CRITICAL for system-threatening errors

2. **Choose Correct Categories**:
   - Use specific categories for better filtering
   - DATABASE for schema operations
   - QUERY for SQL execution
   - CONNECTION for database connectivity
   - MANAGEMENT for admin operations

3. **Include Context**:
   - Add relevant details like device IDs, operation names, or error codes
   - Use include_stack=True for errors that need debugging

4. **Monitor Performance**:
   - Check query execution times in logs
   - Watch for connection issues
   - Monitor error patterns

## Example Usage

### Application Startup
```python
from database import DatabaseManager, LogLevel, LogCategory, log_info

# Initialize with appropriate logging level for production
db = DatabaseManager(log_level=LogLevel.INFO)

log_info("Road Condition Indexer starting up", LogCategory.GENERAL)
db.init_tables()  # This will log all table creation operations
log_info("Database initialization complete", LogCategory.DATABASE)
```

### Error Handling in Data Processing
```python
try:
    db.insert_bike_data(lat, lon, speed, direction, roughness, distance, device_id, ip)
    log_info(f"Data stored successfully for device {device_id}", LogCategory.QUERY)
except Exception as e:
    log_error(f"Failed to store data for device {device_id}: {e}", LogCategory.DATABASE)
    raise
```

### Monitoring and Debugging
```python
# Check recent errors
recent_errors = get_debug_logs(level_filter=LogLevel.ERROR, limit=20)
for error in recent_errors:
    print(f"[{error['timestamp']}] {error['message']}")

# Monitor query performance
query_logs = get_debug_logs(category_filter=LogCategory.QUERY, limit=100)
slow_queries = [log for log in query_logs if 'completed in' in log['message'] and float(log['message'].split('completed in ')[1].split('s')[0]) > 1.0]
```

This enhanced logging system provides comprehensive visibility into the application's operation while maintaining high performance and flexibility for different deployment scenarios.
