# AI Assistant & Engineer Instructions for Road Condition Indexer

## Overview
This is a FastAPI-based application that collects road roughness data from mobile devices and stores it in a database using modern SQLAlchemy architecture. The system processes accelerometer data to calculate road roughness metrics and provides a web interface for data visualization.

## Project Architecture

### Backend (Python/FastAPI)
- **Main Application**: `main.py` - FastAPI server with all API endpoints
- **Database Layer**: `database.py` - SQLAlchemy-based DatabaseManager with automatic backend selection
- **Logging Utilities**: `log_utils.py` - Centralized logging with categories and levels
- **Environment Setup**: `setup_env.py` - Modern environment validation and database connectivity testing

### Frontend (HTML/JavaScript)
- **Main Interface**: `static/index.html` - Primary data collection interface
- **Device View**: `static/device.html` - Leaflet.js map visualization with device filtering
- **Database View**: `static/database.html` - Database query interface
- **Maintenance**: `static/maintenance.html` - Admin tools and API documentation
- **Login**: `static/login.html` - Authentication interface

### Key Dependencies
- **Core**: FastAPI, uvicorn, SQLAlchemy, pymssql, numpy, scipy, python-dotenv
- **Database**: No ODBC driver required - uses pymssql for direct SQL Server connections
- **Frontend**: Leaflet.js for mapping functionality
- **Azure**: Azure SDK components for optional management features

## Database Architecture

### **Modern SQLAlchemy Backend (Current)**
- **Primary**: Azure SQL Server via SQLAlchemy + pymssql driver
- **Fallback**: SQLite via SQLAlchemy for development/testing
- **Benefits**: Connection pooling, automatic reconnection, zero ODBC dependencies

### **Automatic Backend Selection**
```python
# Configured via environment variables
if all Azure SQL variables present:
    → Use SQLAlchemy + pymssql → Azure SQL Server
else:
    → Use SQLAlchemy + SQLite → Local RCI_local.db file
```

### Core Tables
1. **RCI_bike_data**: Primary sensor data (id, timestamp, lat/lon, speed, direction, roughness, distance, device_id, ip, elevation)
2. **RCI_bike_source_data**: Raw sensor data for research (bike_data_id, z_values, speed, interval, frequencies)
3. **RCI_debug_log**: Enhanced logging (id, timestamp, level, category, device_id, message, stack_trace, display_time)
4. **RCI_device_nicknames**: Device management (device_id, nickname, user_agent, device_fp, last_seen, total_submissions)
5. **RCI_user_actions**: User activity auditing (id, timestamp, action_type, user_ip, device_id, success, error_message)
6. **RCI_archive_logs**: Historical data archiving (id, original_table, archive_date, record_count, data_json)

### **Database Migration (Completed)**
- **Previous**: pyodbc with manual connection management
- **Current**: SQLAlchemy with connection pooling and automatic backend selection
- **Impact**: Simpler deployment, better reliability, no ODBC driver dependencies

## Key Features & Recent Developments

### Data Processing Pipeline
- Z-axis acceleration samples are resampled and filtered with a 0.5–50 Hz Butterworth band-pass filter
- RMS acceleration calculation for roughness scoring
- Speed filtering (ignores data below 7 km/h)
- Additional metrics: VDV and crest factor (computed but not stored)

### Device Management
- Device nickname assignment via `/nickname` endpoint
- **CRITICAL BUG**: `device.html` calls `populateDeviceFilter()` but function is named `populateDeviceIds()`
- Device selection with multi-select support
- User agent and device fingerprinting

### Map Visualization
- Leaflet.js integration with OpenStreetMap tiles
- Color-coded roughness visualization (green to red gradient)
- Fullscreen map support with proper resize handling
- Progressive loading with progress indicators
- Dual-range time filtering with synchronized sliders
- **NEW**: Map auto-centers on user location on page load
- **NEW**: Optional "Keep map centered on my location" feature for real-time tracking
- **NEW**: Activity log and debug messages hidden by default with toggle button

### Authentication System
- Cookie-based authentication with MD5 password hashing
- Management endpoints require authentication
- Default password hash: "08457aa99f426e5e8410798acd74c23b" ("fiets")

## API Endpoints

### Public Endpoints
- `POST /bike-data` - Submit measurement data (requires speed ≥7 km/h)
- `GET /logs` - Fetch recent measurements (limit parameter)
- `GET /filteredlogs` - Filtered data retrieval with device/date filters
- `GET /device_ids` - Device list with nicknames
- `GET /date_range` - Available data date range
- `POST /nickname` - Set device nickname
- `GET /gpx` - Generate GPX file export
- `GET /debuglog` - Basic debug log retrieval
- `GET /debuglog/enhanced` - Enhanced logging with filtering

### Management Endpoints (Authentication Required)
- `GET /manage/tables` - Database table information
- `GET /manage/table_rows` - Table row counts
- `POST /manage/insert_testdata` - Test data insertion
- Various Azure management endpoints for scaling

## Testing Strategy

- Run comprehensive tests using `python tests/test_runner.py` for database-only tests
- Use `python tests/test_runner.py full` for complete API and database testing
- Tests are located in the `tests/` folder with comprehensive coverage
- Key test files: `tests/test_comprehensive_data_flow.py`, `tests/test_runner.py`
- Skip tests when making documentation or layout-only updates
- New tests should be created in the `tests/` folder. 

## Known Issues & Fixes

### Fixed Issues
1. **SQLite Journal Cycling**: Resolved with WAL mode and context managers (documented in SQLITE_JOURNAL_FIX.md)
2. **Connection Leaks**: Fixed with proper context management patterns
3. **Logging Performance**: Enhanced with database-level filtering
4. **Device Page Load Failure**: Fixed misplaced closing tags in `static/device.html` that broke script execution and prevented devices and map from loading correctly
5. **Database Page Missing Route**: Added `/database.html` endpoint so the page loads properly

### Current Issues
- No critical bugs currently identified

### Recent UI Improvements (January 2025)
1. **Main Page UI Enhancements**: 
   - Activity log and debug message sections now hidden by default with "Show Logs" toggle button
   - Map automatically centers on user's location when page loads with fallback to Houten, NL
   - Added "Keep map centered on my location" checkbox for real-time location tracking
   - Map view updates to follow user location during active recording when option is enabled

## Development Best Practices

### Database Operations
- Always use `DatabaseManager.get_connection_context()` for database operations
- Implement proper error handling with logging
- Use appropriate log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Categorize logs: GENERAL, DATABASE, CONNECTION, QUERY, MANAGEMENT, MIGRATION, BACKUP

### Frontend Development
- Map operations require `map.invalidateSize()` after container changes
- Progressive loading for large datasets (process in chunks of 100)
- Synchronize slider controls with date inputs
- Handle fullscreen mode properly for map resizing
- **NEW**: Use `userLocation` variable to track current user position
- **NEW**: Check `center-on-user` checkbox state before updating map center
- **NEW**: Toggle log visibility with `toggleLogs()` function

### Security Considerations
- Management endpoints require authentication
- Input validation on all user-submitted data
- Device fingerprinting for tracking
- IP address logging for audit trails

## Environment Setup

1. Create `.env` file with Azure SQL credentials (optional)
2. Install dependencies: `pip install -r requirements.txt`
3. Install Microsoft ODBC Driver for SQL Server
4. Run `python setup_env.py` to verify setup
5. Start server: `uvicorn main:app --reload --host 0.0.0.0`

## File Organization

### Static Files
- HTML templates in `static/` directory
- Leaflet.js assets (leaflet.css, leaflet.js)
- Auto-served under `/static` path

### Configuration
- Environment variables via `.env` file
- Fallback to SQLite if Azure not configured
- Database stored in `RCI_local.db` for SQLite mode

### Documentation
- `README.md` - Basic setup and API documentation
- `LOGGING.md` - Comprehensive logging system documentation
- `SQLITE_JOURNAL_FIX.md` - Database optimization details
- `AGENTS.md` - This file (AI/Engineer instructions)

This file should be updated whenever significant architectural changes, bug fixes, or new features are implemented.

