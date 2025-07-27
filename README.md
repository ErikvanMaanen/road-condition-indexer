# Road Condition Indexer

This project collects road roughness data from mobile devices and stores it in a database. The backend is built with FastAPI and uses SQLAlchemy for robust database management with Azure SQL Server.

## Database Backend

The application uses a modern SQLAlchemy-based database layer with SQL Server enforcement:

### **Database: Azure SQL Server (Required)**
- **Driver**: SQLAlchemy with pymssql 
- **Connection**: Secure, connection-pooled access to Azure SQL
- **Features**: Production-scale, automatic failover, backup capabilities
- **Configuration**: Set Azure SQL environment variables (see Setup section)
- **Fail-Fast**: Application will not start without proper SQL Server configuration

### **SQL Connectivity Testing**
The application includes comprehensive SQL connectivity testing that runs automatically on startup:
- **Environment Detection**: Automatically detects Azure App Service vs local development
- **Progressive Testing**: DNS resolution → Port connectivity → Authentication → Query execution → Performance benchmarking
- **Detailed Diagnostics**: Provides specific error messages and recommendations for connectivity issues
- **Performance Monitoring**: Measures and reports connection and query performance

See [SQL_CONNECTIVITY_TESTING.md](SQL_CONNECTIVITY_TESTING.md) for detailed documentation.

## Endpoints

- `POST /bike-data` – Submit new bike sensor data. Requires JSON payload with latitude,
  longitude, **speed in km/h**, direction, a device identifier, and a list of
  Z-axis acceleration values. The server computes the
  average speed reported by the client and ignores submissions when that
  speed is below **7 km/h** by default (configurable via `RCI_MIN_SPEED_KMH`).
- `GET /logs` – Fetch recent measurements. Accepts an optional `limit` query
  parameter (default 100).
- `GET /debuglog` – Retrieve backend debug messages.

## Setup

1. **Environment Configuration** (Required):

   **For Local Development:**
   Create a `.env` file with your Azure SQL connection details:
   ```env
   AZURE_SQL_SERVER=your-server.database.windows.net
   AZURE_SQL_DATABASE=your-database-name
   AZURE_SQL_USER=your-username
   AZURE_SQL_PASSWORD=your-password
   AZURE_SQL_PORT=1433
   ```
   
   **For Azure App Service:**
   Set the same variables as Application Settings in your Azure App Service configuration.

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   
   **Key Dependencies**:
   - `sqlalchemy>=2.0.0` - Modern database ORM
   - `pymssql>=2.2.0` - SQL Server driver (no ODBC required)
   - `fastapi>=0.104.0` - Web framework
   - `numpy`, `scipy` - Scientific computing for data processing

3. **Test SQL Connectivity** (Recommended):
   Before starting the application, test your SQL Server connectivity:
   ```bash
   python test_sql_connectivity.py
   ```
   
   This standalone test will:
   - Verify all environment variables are set
   - Test DNS resolution and port connectivity
   - Validate authentication and database access
   - Benchmark connection performance
   - Provide specific troubleshooting recommendations

4. **Environment Verification** (Optional):
   ```bash
   python setup_env.py
   ```
   This will verify your Python environment, check dependencies, and test database connectivity.

5. **Start the API Server**:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0
   ```
   
   The application will automatically run SQL connectivity tests on startup and provide detailed diagnostic information.

## Key Improvements in Database Handling

### **No ODBC Driver Required**
- **Previous**: Required Microsoft ODBC Driver 17/18 for SQL Server
- **Current**: Uses pymssql driver with direct TCP connection
- **Benefit**: Simpler deployment, fewer dependencies, more reliable connections

### **Automatic Fallback**
- **Previous**: Manual configuration required for database selection
- **Current**: Automatic detection and fallback to SQLite
- **Benefit**: Zero-configuration development environment

### **Connection Pooling & Reliability**
- **Previous**: Manual connection management
- **Current**: SQLAlchemy connection pooling with automatic reconnection
- **Benefit**: Better performance, automatic connection recovery

### **Enhanced Error Handling**
- **Previous**: Basic error reporting
- **Current**: Comprehensive logging with detailed error tracking
- **Benefit**: Easier debugging and monitoring

The built-in frontend is served from the `static/` directory under the
`/static` path when the server is running. The main interface is
available at `/`, and you can still visit `/welcome.html` for a simple
welcome page.

The `/maintenance.html` page provides controls to inspect the current database
and Azure App Service plan settings and lets you modify these configurations.

Use the **Update Records** button in the interface to reload the latest
roughness records from the database and refresh the map.

When the API starts it will automatically create all required tables if they 
do not already exist, regardless of which database backend is being used.

## Roughness Pipeline

Submitted Z-axis samples are resampled to a constant rate and filtered with a
0.5–50 Hz Butterworth band-pass. The resulting signal is used to calculate the
root‑mean‑square acceleration which forms the stored roughness value. Additional
metrics like the vibration dose value (VDV) and crest factor are computed for
future analysis, although they are not currently stored in the database. To
avoid noise during stops, reports with an average speed below the configured
threshold (7 km/h by default) still yield a roughness score of zero.

## Database Schema

The application automatically creates the following tables in both SQL Server and SQLite:

### Core Data Tables
```sql
-- Main sensor data storage
CREATE TABLE RCI_bike_data (
  id INT IDENTITY PRIMARY KEY,                    -- Auto-incrementing ID
  timestamp DATETIME DEFAULT GETDATE(),           -- UTC timestamp
  latitude FLOAT,                                 -- GPS latitude
  longitude FLOAT,                                -- GPS longitude
  speed FLOAT,                                    -- Speed in km/h
  direction FLOAT,                                -- Direction in degrees
  roughness FLOAT,                                -- Calculated roughness index
  distance_m FLOAT,                               -- Distance from previous point (meters)
  device_id NVARCHAR(100),                        -- Device identifier
  ip_address NVARCHAR(45),                        -- Client IP address
  elevation FLOAT                                 -- Elevation in meters (if available)
);

-- Raw sensor data for research (optional)
CREATE TABLE RCI_bike_source_data (
  id INT IDENTITY PRIMARY KEY,
  bike_data_id INT,                               -- Foreign key to RCI_bike_data
  z_values NVARCHAR(MAX),                         -- JSON array of Z-axis readings
  speed_kmh FLOAT,                                -- Speed at time of recording
  interval_sec FLOAT,                             -- Time interval for samples
  freq_min FLOAT,                                 -- Filter frequency minimum
  freq_max FLOAT,                                 -- Filter frequency maximum
  timestamp DATETIME DEFAULT GETDATE()
);
```

### Logging and Management Tables
```sql
-- Application debug and error logging
CREATE TABLE RCI_debug_log (
  id INT IDENTITY PRIMARY KEY,
  timestamp DATETIME DEFAULT GETDATE(),           -- UTC timestamp
  level NVARCHAR(20),                             -- Log level (DEBUG, INFO, WARNING, ERROR)
  category NVARCHAR(50),                          -- Log category 
  device_id NVARCHAR(100),                        -- Associated device (if applicable)
  message NVARCHAR(4000),                         -- Log message
  stack_trace NVARCHAR(MAX),                      -- Exception stack trace (if applicable)
  display_time NVARCHAR(50)                       -- Formatted display time
);

-- Device management and nicknames
CREATE TABLE RCI_device_nicknames (
  device_id NVARCHAR(100) PRIMARY KEY,            -- Device identifier
  nickname NVARCHAR(100),                         -- User-friendly name
  user_agent NVARCHAR(256),                       -- Browser/app user agent
  device_fp NVARCHAR(256),                        -- Device fingerprint
  last_seen DATETIME DEFAULT GETDATE(),           -- Last activity timestamp
  total_submissions INT DEFAULT 0                 -- Total data submissions count
);

-- User action auditing
CREATE TABLE RCI_user_actions (
  id INT IDENTITY PRIMARY KEY,
  timestamp DATETIME DEFAULT GETDATE(),           -- UTC timestamp
  action_type NVARCHAR(50),                       -- Type of action performed
  action_description NVARCHAR(500),               -- Detailed description
  user_ip NVARCHAR(45),                           -- User IP address
  user_agent NVARCHAR(256),                       -- Browser/app user agent
  device_id NVARCHAR(100),                        -- Associated device (if applicable)
  session_id NVARCHAR(100),                       -- Session identifier
  additional_data NVARCHAR(MAX),                  -- Additional JSON data
  success BIT DEFAULT 1,                          -- Success/failure flag
  error_message NVARCHAR(1000)                    -- Error details (if applicable)
);

-- Archive for old log data
CREATE TABLE RCI_archive_logs (
  id INT IDENTITY PRIMARY KEY,
  original_table NVARCHAR(100),                   -- Source table name
  archive_date DATETIME DEFAULT GETDATE(),        -- Archive timestamp
  record_count INT,                               -- Number of archived records
  data_json NVARCHAR(MAX)                         -- Archived data in JSON format
);
```

## Security Features

### RCI_ Table Security Filter
The database module includes security filtering to restrict access to only tables that start with the "RCI_" prefix. This prevents unauthorized access to system tables or other application tables.

**Security Benefits:**
- **Isolation** - Prevents accidental access to system or other application tables
- **Data Protection** - Ensures database operations only affect intended tables
- **Audit Trail** - All table operations are logged and restricted to known tables
- **Principle of Least Privilege** - Only grants access to tables needed for functionality

**Affected Methods:**
- `get_table_summary()` - Only returns RCI_ tables
- `get_last_table_rows()` - Rejects non-RCI_ table names
- `test_table_operations()` - Validates table names
- `backup_table()` - Restricted to RCI_ tables only
- `table_exists()` - Returns False for non-RCI_ tables

## Logging and Monitoring

The application includes comprehensive logging capabilities:

- **Enhanced Debug Logging** with filtering by level and category
- **Device ID Tracking** throughout all application logs
- **User Action Logging** for audit trails
- **Startup Process Logging** for system diagnostics
- **Frontend Logging Components** for client-side debugging

For detailed logging documentation, see `LOGGING.md`.

## Testing

The application includes a comprehensive test suite that validates both database operations and API functionality. Tests can run in two modes:

- **Database-only mode** (default): Tests database operations without requiring API server
- **Full mode**: Tests both database and API operations with automatic server management

```bash
# Quick database-only tests
python test_runner.py

# Full test suite (database + API)
python test_runner.py full
```

For detailed testing documentation, see `TESTING.md`.

## Developer Guidelines

For AI assistants and developers working on this project, see `AGENTS.md` for detailed guidelines on:
- Project architecture and components
- Database management and security
- Testing strategies
- Known issues and fixes
- Development workflows
