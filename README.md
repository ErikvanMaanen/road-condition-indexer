# Road Condition Indexer

This project collects road roughness data from mobile devices and stores it in an Azure SQL database. The backend is built with FastAPI.

## Endpoints

- `POST /log` – Submit a new measurement. Requires JSON payload with latitude,
  longitude, **speed in km/h**, direction, a device identifier, and a list of
  Z-axis acceleration values. The server computes the
  average speed reported by the client and ignores submissions when that
  speed is below **7 km/h** by default (configurable via `RCI_MIN_SPEED_KMH`).
- `GET /logs` – Fetch recent measurements. Accepts an optional `limit` query
  parameter (default 100).
- `GET /debuglog` – Retrieve backend debug messages.

## Setup

1. Create an `.env` file based on `.env.template` and fill in your Azure SQL connection details.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   This project requires the Microsoft ODBC Driver for SQL Server
   (version 17 or 18). If you see an error like `Can't open lib 'ODBC Driver'`
   when running `setup_env.py`, install the driver for your operating system.

   If the Azure SQL environment variables are not provided the API will
   automatically fall back to a local SQLite database stored in
   `local.db`. This allows running the server without any external
   database service.
3. (Optional) Run `python setup_env.py` to verify environment variables and database connectivity.
4. Start the API server:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0
   ```

The built-in frontend is served from the `static/` directory under the
`/static` path when the server is running. The main interface is
available at `/`, and you can still visit `/welcome.html` for a simple
welcome page.


The `/maintenance.html` page provides controls to inspect the current SQL
database size and Azure App Service plan and lets you modify these settings.

Use the **Update Records** button in the interface to reload the latest
roughness records from the database and refresh the map.

When the API starts it will automatically create the `RCI_bike_data` and
`RCI_debug_log` tables if they do not already exist.

## Roughness Pipeline

Submitted Z-axis samples are resampled to a constant rate and filtered with a
0.5–50 Hz Butterworth band-pass. The resulting signal is used to calculate the
root‑mean‑square acceleration which forms the stored roughness value. Additional
metrics like the vibration dose value (VDV) and crest factor are computed for
future analysis, although they are not currently stored in the database. To
avoid noise during stops, reports with an average speed below the configured
threshold (7 km/h by default) still yield a roughness score of zero.

## Database Schema

```
CREATE TABLE RCI_bike_data (
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
);

CREATE TABLE RCI_debug_log (
  id INT IDENTITY PRIMARY KEY,
  timestamp DATETIME DEFAULT GETDATE(),
  level NVARCHAR(20),
  category NVARCHAR(50),
  device_id NVARCHAR(100),
  message NVARCHAR(4000),
  stack_trace NVARCHAR(MAX)
);

CREATE TABLE RCI_device_nicknames (
  device_id NVARCHAR(100) PRIMARY KEY,
  nickname NVARCHAR(100),
  user_agent NVARCHAR(256),
  device_fp NVARCHAR(256)
);

CREATE TABLE RCI_user_actions (
  id INT IDENTITY PRIMARY KEY,
  timestamp DATETIME DEFAULT GETDATE(),
  action_type NVARCHAR(50),
  action_description NVARCHAR(500),
  user_ip NVARCHAR(45),
  user_agent NVARCHAR(256),
  device_id NVARCHAR(100),
  session_id NVARCHAR(100),
  additional_data NVARCHAR(MAX),
  success BIT,
  error_message NVARCHAR(1000)
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
