# Troubleshooting Guide

## Common Issues and Solutions

### Database Connectivity Issues

#### Problem: "Database error" on startup
**Symptoms:**
- Application fails to start
- Error messages about database connection
- 500 errors on API endpoints

**Solutions:**
1. **Check Environment Variables**:
   ```bash
   # Verify all required variables are set
   AZURE_SQL_SERVER=your-server.database.windows.net
   AZURE_SQL_DATABASE=your-database-name
   AZURE_SQL_USER=your-username
   AZURE_SQL_PASSWORD=your-password
   AZURE_SQL_PORT=1433
   ```

2. **Test DNS Resolution**:
   ```bash
   nslookup your-server.database.windows.net
   ```

3. **Check Firewall Rules**:
   - Ensure Azure SQL Server firewall allows App Service IPs
   - Add "Allow Azure services" rule if needed

4. **Validate Credentials**:
   - Test login using SQL Server Management Studio
   - Check for expired passwords or locked accounts

#### Problem: "Connection timeout" errors
**Symptoms:**
- Intermittent database connection failures
- Slow response times
- Connection pool exhaustion

**Solutions:**
1. **Increase Connection Timeout**:
   ```python
   # Add to database configuration
   connection_timeout=30
   ```

2. **Optimize Connection Pool**:
   - Monitor active connections
   - Adjust pool size based on load
   - Enable connection recycling

3. **Check Network Latency**:
   - Test network connectivity between App Service and SQL Database
   - Consider using Azure SQL Database in same region

### Authentication Issues

#### Problem: Unable to access protected pages
**Symptoms:**
- Redirected to login page repeatedly
- 401 Unauthorized errors
- Session not persisting

**Solutions:**
1. **Check Cookie Configuration**:
   ```javascript
   // Ensure cookies are properly set
   document.cookie // Should contain auth cookie
   ```

2. **Verify Password Hash**:
   ```python
   import hashlib
   password = "your-password"
   hash_value = hashlib.md5(password.encode()).hexdigest()
   # Should match PASSWORD_HASH in main.py
   ```

3. **Clear Browser Cache**:
   - Clear cookies and local storage
   - Try incognito/private browsing mode

#### Problem: Static files not loading
**Symptoms:**
- Missing CSS styles
- JavaScript not executing
- 404 errors for static assets

**Solutions:**
1. **Check Route Configuration**:
   - Verify static file routes in main.py
   - Ensure proper file paths

2. **File Permissions**:
   ```bash
   # Check file permissions
   ls -la static/
   chmod 644 static/*.css static/*.js
   ```

### Frontend Issues

#### Problem: Map not displaying
**Symptoms:**
- Blank map container
- JavaScript errors in console
- Missing Leaflet resources

**Solutions:**
1. **Check Leaflet Dependencies**:
   ```html
   <!-- Ensure proper loading order -->
   <link rel="stylesheet" href="leaflet.css" />
   <script src="leaflet.js"></script>
   <script src="map-components.js"></script>
   ```

2. **Verify Map Container**:
   ```javascript
   // Check if map container exists
   const mapContainer = document.getElementById('map-container');
   if (!mapContainer) {
       console.error('Map container not found');
   }
   ```

3. **Check Network Access**:
   - Verify internet connectivity for tile loading
   - Check for CORS issues with tile servers

#### Problem: Device motion not working
**Symptoms:**
- No accelerometer data captured
- Permission denied errors
- iOS Safari not requesting permission

**Solutions:**
1. **Request Permissions (iOS)**:
   ```javascript
   if (typeof DeviceMotionEvent.requestPermission === 'function') {
       DeviceMotionEvent.requestPermission().then(response => {
           if (response === 'granted') {
               // Start listening for motion events
           }
       });
   }
   ```

2. **Check HTTPS Requirement**:
   - Device Motion API requires HTTPS in production
   - Use localhost for development testing

3. **Browser Compatibility**:
   - Test on mobile devices (desktop browsers have limited support)
   - Check browser console for API availability

### Timezone Handling Issues

#### Problem: Incorrect time display
**Symptoms:**
- Times showing in wrong timezone
- Inconsistent time formatting
- Filter not working with correct time range

**Solutions:**
1. **Check Timezone Conversion Functions**:
   ```javascript
   // Verify utils.js functions are loaded
   console.log(typeof formatDutchTime); // Should be 'function'
   console.log(typeof toCESTDateTimeLocal); // Should be 'function'
   ```

2. **Validate Time Conversion**:
   ```javascript
   // Test timezone conversion
   const utcTime = '2025-07-28T12:00:00Z';
   const amsterdamTime = toCESTDateTimeLocal(utcTime);
   console.log(amsterdamTime); // Should show Amsterdam local time
   ```

3. **Check Browser Timezone**:
   ```javascript
   // Verify browser timezone detection
   console.log(Intl.DateTimeFormat().resolvedOptions().timeZone);
   ```

### Performance Issues

#### Problem: Slow API responses
**Symptoms:**
- Long loading times
- Request timeouts
- Poor user experience

**Solutions:**
1. **Database Query Optimization**:
   ```sql
   -- Add indexes on frequently queried columns
   CREATE INDEX IX_bike_data_device_id ON RCI_bike_data(device_id);
   CREATE INDEX IX_bike_data_timestamp ON RCI_bike_data(timestamp);
   ```

2. **Enable Query Logging**:
   ```python
   # Monitor slow queries
   db_manager.log_debug("Query execution time: {:.2f}s".format(duration))
   ```

3. **Connection Pool Tuning**:
   - Monitor connection pool usage
   - Adjust pool size based on load patterns
   - Enable connection recycling

#### Problem: High memory usage
**Symptoms:**
- Application restarts due to memory limits
- Slow garbage collection
- OutOfMemory errors

**Solutions:**
1. **Monitor Memory Usage**:
   ```python
   import psutil
   import gc
   
   # Log memory usage
   memory_info = psutil.Process().memory_info()
   log_debug(f"Memory usage: {memory_info.rss / 1024 / 1024:.2f} MB")
   ```

2. **Optimize Data Processing**:
   - Process large datasets in chunks
   - Use generators for large result sets
   - Clear unused variables explicitly

3. **Garbage Collection**:
   ```python
   import gc
   
   # Force garbage collection
   gc.collect()
   ```

### Migration Issues

#### Problem: Database schema mismatch
**Symptoms:**
- Table not found errors
- Column doesn't exist errors
- Type conversion failures

**Solutions:**
1. **Run Database Migration**:
   ```bash
   python migrate_db.py
   ```

2. **Check Table Schema**:
   ```sql
   -- Verify table structure
   SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE 
   FROM INFORMATION_SCHEMA.COLUMNS 
   WHERE TABLE_NAME = 'RCI_bike_data';
   ```

3. **Manual Schema Updates**:
   ```sql
   -- Add missing columns if needed
   ALTER TABLE RCI_bike_data ADD COLUMN new_column VARCHAR(255);
   ```

#### Problem: Data type incompatibilities
**Symptoms:**
- Type conversion errors
- Invalid data format errors
- Query execution failures

**Solutions:**
1. **Check Data Types**:
   ```python
   # Verify data types in Python
   import sqlalchemy as sa
   from database import db_manager
   
   metadata = sa.MetaData()
   table = sa.Table('RCI_bike_data', metadata, autoload_with=db_manager.engine)
   for column in table.columns:
       print(f"{column.name}: {column.type}")
   ```

2. **Update Type Mappings**:
   ```python
   # Ensure proper type conversion
   value = float(value) if isinstance(value, str) else value
   ```

### Logging and Debugging

#### Problem: Missing log entries
**Symptoms:**
- Expected log messages not appearing
- Debug information not available
- Troubleshooting difficulties

**Solutions:**
1. **Check Log Level Configuration**:
   ```python
   from log_utils import LogLevel, log_debug
   
   # Ensure debug logging is enabled
   log_debug("Debug message test", LogLevel.DEBUG)
   ```

2. **Verify Database Log Table**:
   ```sql
   -- Check if logs are being stored
   SELECT TOP 10 * FROM RCI_debug_log ORDER BY timestamp DESC;
   ```

3. **Enable Enhanced Logging**:
   ```python
   # Use enhanced logging with categories
   from log_utils import LogCategory
   log_info("Test message", LogCategory.DATABASE)
   ```

### SQL Connectivity Testing

#### Problem: Connectivity tests failing
**Symptoms:**
- Application startup fails
- Database connectivity warnings
- Performance degradation

**Solutions:**
1. **Run Manual Connectivity Test**:
   ```python
   from tests.sql_connectivity_tests import run_startup_connectivity_tests
   
   result = run_startup_connectivity_tests(timeout_seconds=30)
   print(result.overall_status)
   print(result.summary)
   ```

2. **Check Network Connectivity**:
   ```bash
   # Test port connectivity
   telnet your-server.database.windows.net 1433
   
   # Test DNS resolution
   nslookup your-server.database.windows.net
   ```

3. **Validate Authentication**:
   ```python
   # Test SQL authentication
   import pymssql
   
   try:
       conn = pymssql.connect(
           server='your-server.database.windows.net',
           user='your-username',
           password='your-password',
           database='your-database',
           port=1433
       )
       print("Connection successful")
   except Exception as e:
       print(f"Connection failed: {e}")
   ```

## Error Code Reference

### HTTP Status Codes
- **401 Unauthorized**: Authentication required or invalid credentials
- **403 Forbidden**: Valid authentication but insufficient permissions  
- **404 Not Found**: Endpoint or resource not found
- **500 Internal Server Error**: Database connection or query error
- **503 Service Unavailable**: Health check failure or system overload

### Database Error Codes
- **18456**: Login failed for user (incorrect credentials)
- **2**: Named pipe provider error (network connectivity)
- **53**: Network path not found (firewall or DNS issue)
- **40613**: Database unavailable (Azure SQL specific)

### Custom Application Errors
- **DB_CONNECTION_FAILED**: Database connection could not be established
- **AUTH_INVALID**: Authentication token invalid or expired
- **DEVICE_PERMISSION_DENIED**: Device motion permission not granted
- **TIMEZONE_CONVERSION_ERROR**: Timezone conversion failed

## Recovery Procedures

### Database Recovery
1. **Check Azure SQL Database Status** in Azure Portal
2. **Review Recent Backups** and point-in-time recovery options
3. **Test Connection** using SQL Server Management Studio
4. **Restore from Backup** if necessary
5. **Update Connection Strings** if server details changed

### Application Recovery
1. **Check App Service Status** in Azure Portal
2. **Review Application Logs** for error patterns
3. **Restart App Service** to clear temporary issues
4. **Redeploy Application** if code issues identified
5. **Update Configuration** if environment variables changed

### Complete System Recovery
1. **Assess Scope of Issue** (database, application, or both)
2. **Implement Database Recovery** following database procedures
3. **Deploy Application** from known good version
4. **Test All Functionality** including authentication and data submission
5. **Monitor System** for stability and performance
6. **Document Incident** and update procedures as needed

## Database Migration Issues

### Problem: Migration from pyodbc to SQLAlchemy
**Symptoms:**
- ODBC driver errors during deployment
- Connection string compatibility issues
- Performance degradation after migration

**Migration Benefits:**
- **No ODBC Driver Required**: Direct pymssql connection to SQL Server
- **Connection Pooling**: Better performance and reliability
- **Simplified Deployment**: Fewer dependencies and configuration steps
- **Cross-Platform**: Works on Windows, Linux, and macOS without driver issues
- **SQL Server Only**: Enforced production-grade database architecture

**Migration Steps:**
1. **Update Dependencies**:
   ```bash
   # Remove old dependencies (if present)
   pip uninstall pyodbc
   
   # Install new dependencies
   pip install -r requirements.txt
   ```

2. **Update Environment Configuration**:
   ```env
   # Required for Azure SQL Server
   AZURE_SQL_SERVER=your-server.database.windows.net
   AZURE_SQL_DATABASE=your-database-name
   AZURE_SQL_USER=your-username
   AZURE_SQL_PASSWORD=your-password
   AZURE_SQL_PORT=1433
   ```

3. **Update Code Patterns**:
   ```python
   # Old pattern (pyodbc)
   import pyodbc
   conn = pyodbc.connect(connection_string)
   cursor = conn.cursor()
   cursor.execute(query)
   results = cursor.fetchall()
   conn.close()
   
   # New pattern (SQLAlchemy)
   from database import db_manager
   results = db_manager.execute_query(query)
   ```

4. **Test Migration**:
   ```bash
   # Verify environment and test database connection
   python setup_env.py
   ```

### Problem: Docker deployment issues after migration
**Symptoms:**
- Container build failures
- Missing ODBC driver errors
- Runtime connection issues

**Solutions:**
1. **Simplified Dockerfile**:
   ```dockerfile
   # Before: Complex ODBC driver installation
   # RUN apt-get update && apt-get install -y curl apt-transport-https
   # RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
   # ... complex ODBC setup
   
   # After: Just install Python dependencies
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   # No additional driver installation needed
   ```

2. **Verify Environment Variables**:
   ```bash
   # Check which backend is being used
   curl https://your-app.azurewebsites.net/health
   ```

### Migration Rollback Plan
If issues occur during migration:
1. Restore previous version with pyodbc code
2. Ensure ODBC drivers are installed in deployment environment
3. Revert to previous `requirements.txt`
4. Address migration issues and retry
