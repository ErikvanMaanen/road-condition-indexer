# Database Migration Guide - pyodbc to SQLAlchemy

This document explains the migration from pyodbc-based database handling to SQLAlchemy with automatic backend selection.

## What Changed

### Before (pyodbc-based)
```python
import pyodbc

# Manual connection management
conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server},{port};..."
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()
cursor.execute("SELECT * FROM table")
results = cursor.fetchall()
conn.close()
```

### After (SQLAlchemy-based)
```python
from database import db_manager

# Automatic backend selection and connection management
results = db_manager.execute_query("SELECT * FROM table")
# Connection pooling and cleanup handled automatically
```

## Key Benefits

1. **No ODBC Driver Required**: Direct pymssql connection to SQL Server
2. **Automatic Fallback**: SQLite for development when Azure SQL not configured
3. **Connection Pooling**: Better performance and reliability
4. **Simplified Deployment**: Fewer dependencies and configuration steps
5. **Cross-Platform**: Works on Windows, Linux, and macOS without driver issues

## Environment Variables

### Required for Azure SQL Server
```env
AZURE_SQL_SERVER=your-server.database.windows.net
AZURE_SQL_DATABASE=your-database-name
AZURE_SQL_USER=your-username
AZURE_SQL_PASSWORD=your-password
AZURE_SQL_PORT=1433
```

### Automatic SQLite Fallback
If any Azure SQL variables are missing, the application automatically uses SQLite:
- Database file: `RCI_local.db` (created automatically)
- Zero configuration required
- Perfect for development and testing

## Migration Steps for Developers

### 1. Update Dependencies
```bash
# Remove old dependencies (if present)
pip uninstall pyodbc

# Install new dependencies
pip install -r requirements.txt
```

### 2. Update Environment Configuration
- Copy `.env.template` to `.env`
- Fill in Azure SQL details for production
- For development, you can leave Azure SQL variables empty (SQLite fallback)

### 3. Test Database Connectivity
```bash
# Verify environment and test database connection
python setup_env.py
```

### 4. Code Changes
If you have custom database code, migrate to use the `db_manager`:

**Old pattern:**
```python
import pyodbc
conn = pyodbc.connect(connection_string)
cursor = conn.cursor()
cursor.execute(query)
results = cursor.fetchall()
conn.close()
```

**New pattern:**
```python
from database import db_manager
results = db_manager.execute_query(query)
```

## Deployment Changes

### Azure App Service Configuration

**Removed Requirements:**
- Microsoft ODBC Driver installation
- Complex driver configuration
- Platform-specific setup

**Simplified Configuration:**
1. Set environment variables in App Service Configuration
2. Use simple startup command: `uvicorn main:app --host 0.0.0.0 --port 8000`
3. No additional setup required

### Docker/Container Deployment

**Before:**
```dockerfile
# Complex ODBC driver installation
RUN apt-get update && apt-get install -y curl apt-transport-https
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
RUN curl https://packages.microsoft.com/config/ubuntu/20.04/prod.list > /etc/apt/sources.list.d/mssql-release.list
RUN apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql17
```

**After:**
```dockerfile
# Just install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt
# No additional driver installation needed
```

## Testing

### Local Development
```bash
# Test with SQLite (no configuration needed)
uvicorn main:app --reload

# Test with Azure SQL (set environment variables)
export AZURE_SQL_SERVER=your-server.database.windows.net
export AZURE_SQL_DATABASE=your-database
export AZURE_SQL_USER=your-username
export AZURE_SQL_PASSWORD=your-password
uvicorn main:app --reload
```

### Production Verification
```bash
# Check which backend is being used
curl https://your-app.azurewebsites.net/health

# Response includes database backend information
{
  "status": "healthy",
  "timestamp": "2024-01-20T10:30:00",
  "database": "connected"
}
```

## Troubleshooting

### Common Issues

1. **Connection Errors with Azure SQL**
   - Verify all environment variables are set correctly
   - Check firewall settings allow Azure App Service IP ranges
   - Ensure SQL user has appropriate permissions

2. **SQLite Permission Issues (Local Development)**
   - Ensure write permissions in application directory
   - Check if `RCI_local.db` can be created

3. **Performance Issues**
   - SQLAlchemy connection pooling should improve performance
   - Monitor connection counts in Azure SQL metrics

### Getting Help

1. Run environment verification: `python setup_env.py`
2. Check application logs for database backend selection messages
3. Verify health endpoint: `/health`
4. Review Azure App Service logs in Application Insights

## Migration Checklist

- [ ] Update `requirements.txt` dependencies
- [ ] Configure environment variables (`.env` or App Service Configuration)
- [ ] Test local development with SQLite fallback
- [ ] Test Azure SQL connection with environment verification script
- [ ] Update deployment scripts (remove ODBC driver installation)
- [ ] Verify health check endpoint works
- [ ] Update any custom database code to use `db_manager`
- [ ] Test data submission and retrieval
- [ ] Monitor performance in production

## Rollback Plan

If issues occur, you can temporarily rollback:

1. Restore previous version with pyodbc code
2. Ensure ODBC drivers are installed in deployment environment
3. Revert to previous `requirements.txt`
4. Address migration issues and retry

However, the new SQLAlchemy-based approach is more robust and should resolve most deployment and connectivity issues.
