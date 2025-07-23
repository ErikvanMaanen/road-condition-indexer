# AI Assistant & Engineer Instructions for Road Condition Indexer

## Overview
This is a FastAPI-based application that collects road roughness data from mobile devices and stores it in either Azure SQL Database or SQLite. The system processes accelerometer data to calculate road roughness metrics and provides a web interface for data visualization.

## Project Architecture

### Backend (Python/FastAPI)
- **Main Application**: `main.py` - FastAPI server with all API endpoints
- **Database Layer**: `database.py` - DatabaseManager class with dual SQL Server/SQLite support
- **Environment Setup**: `setup_env.py` - Environment validation and database connectivity testing

### Frontend (HTML/JavaScript)
- **Main Interface**: `static/index.html` - Primary data collection interface
- **Device View**: `static/device.html` - Leaflet.js map visualization with device filtering
- **Database View**: `static/db.html` - Database query interface
- **Maintenance**: `static/maintenance.html` - Admin tools and API documentation
- **Login**: `static/login.html` - Authentication interface

### Key Dependencies
- FastAPI, uvicorn, pyodbc, numpy, scipy, python-dotenv
- Microsoft ODBC Driver for SQL Server (versions 17 or 18)
- Leaflet.js for mapping functionality

## Database Architecture

### Dual Database Support
The application automatically falls back from Azure SQL to SQLite if Azure credentials are not provided.

### Core Tables
1. **RCI_bike_data**: Primary data storage (id, timestamp, lat/lon, speed, direction, roughness, distance, device_id, ip)
2. **RCI_debug_log**: Enhanced logging with levels and categories (id, timestamp, level, category, message, stack_trace)
3. **RCI_device_nicknames**: Device management (device_id, nickname, user_agent, device_fp)

### Recent Database Improvements
- **SQLite Optimization**: Implemented WAL mode, context managers, and optimized PRAGMA settings
- **Connection Management**: Added proper context management to prevent connection leaks
- **Enhanced Logging**: Multi-level logging with categories (GENERAL, DATABASE, CONNECTION, QUERY, MANAGEMENT, MIGRATION, BACKUP)

## Key Features & Recent Developments

### Data Processing Pipeline
- Z-axis acceleration samples are resampled and filtered with a 0.5–50 Hz Butterworth band-pass filter
- RMS acceleration calculation for roughness scoring
- Speed filtering (ignores data below 5 km/h)
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
- Default password hash: "df5f648063a4a2793f5f0427b210f4f7"

## API Endpoints

### Public Endpoints
- `POST /log` - Submit measurement data (requires speed ≥5 km/h)
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

- Run `pytest -q` whenever Python functionality changes (any `.py` files outside of `tests/`)
- Skip tests when making documentation or layout-only updates
- Key test files: `test_improvements.py`, `test_journal.py`, `test_logging.py`, `test_simple.py`

## Known Issues & Fixes

### Fixed Issues
1. **SQLite Journal Cycling**: Resolved with WAL mode and context managers (documented in SQLITE_JOURNAL_FIX.md)
2. **Connection Leaks**: Fixed with proper context management patterns
3. **Logging Performance**: Enhanced with database-level filtering
4. **Device Page Load Failure**: Fixed misplaced closing tags in `static/device.html` that broke script execution and prevented devices and map from loading correctly

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

