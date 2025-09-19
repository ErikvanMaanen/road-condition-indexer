# Road Condition Indexer - Development Guide

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
- **Tools**: `static/tools.html` - Utility tools for data processing and analysis

**Static File Guidelines**: When adding new frontend features, follow the patterns in 
[`STATIC_FILES_GUIDE.md`](STATIC_FILES_GUIDE.md) to ensure proper static file handling 
and avoid CORB/loading issues.

### Key Dependencies
- **Core**: FastAPI, uvicorn, SQLAlchemy, pymssql, numpy, scipy, python-dotenv
- **Database**: No ODBC driver required - uses pymssql for direct SQL Server connections
- **Frontend**: Leaflet.js for mapping functionality
- **Azure**: Azure SDK components for optional management features

## Database Architecture

### SQL Server Only Architecture
- **Database**: Azure SQL Server via SQLAlchemy + pymssql driver (required)
- **Features**: Connection pooling, automatic reconnection, robust error handling
- **Configuration**: All five Azure SQL environment variables must be set
- **Migration**: Migrated from pyodbc to SQLAlchemy for better reliability

**Important**: The application requires Azure SQL Server configuration and will not start without it. No fallback databases are supported.

### Database Tables
1. **RCI_bike_data**: Main data table with GPS coordinates, speed, direction, roughness
2. **RCI_bike_source_data**: Raw accelerometer data for detailed analysis
3. **RCI_debug_log**: Application logs with categorization and filtering
4. **RCI_device_nicknames**: Device registration and user-friendly names
5. **RCI_debug_log_archive**: Archived logs for historical analysis

## Development Setup

### 1. Environment Configuration

**Azure SQL Server Configuration (Required)**:
Create a `.env` file with all required Azure SQL connection details:
```env
AZURE_SQL_SERVER=your-server.database.windows.net
AZURE_SQL_DATABASE=your-database-name
AZURE_SQL_USER=your-username
AZURE_SQL_PASSWORD=your-password
AZURE_SQL_PORT=1433
```

**Note**: All five environment variables are mandatory. The application will fail to start if any are missing.
Create a `.env` file for local development:
```env
AZURE_SQL_SERVER=your-server.database.windows.net
AZURE_SQL_DATABASE=your-database-name
AZURE_SQL_USER=your-username
AZURE_SQL_PASSWORD=your-password
AZURE_SQL_PORT=1433
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Development Server
```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Code Architecture Principles

### Function Centralization
All common JavaScript functions have been centralized in `utils.js`:
- **Time and date utilities**: `formatDutchTime`, `toCESTDateTimeLocal`, `fromCESTDateTimeLocal`
- **Logging utilities**: `addLog`, `addDebug`, `loadLogsPartial`
- **Map utilities**: `colorForRoughness`, map initialization functions
- **API utilities**: Authentication helpers, data formatting
- **Common constants**: `LABEL_COUNT`, `ROUGHNESS_NAMES`

### Authentication System
- **Cookie-based authentication**: Uses MD5 hash for secure session management
- **Protected endpoints**: All management endpoints require authentication
- **Frontend validation**: Client-side authentication checks prevent unauthorized access
- **Session persistence**: Maintains login state across page refreshes

### Logging System

#### Log Levels (in order of severity)
- `DEBUG`: Detailed information for debugging
- `INFO`: General information about system operation
- `WARNING`: Warning messages for potential issues
- `ERROR`: Error conditions that need attention
- `CRITICAL`: Critical errors that may cause system failure

#### Log Categories
- `GENERAL`: General application messages
- `DATABASE`: Database-related operations
- `CONNECTION`: Database connection events
- `QUERY`: SQL query execution details
- `MANAGEMENT`: Management operations
- `MIGRATION`: Database schema migrations
- `BACKUP`: Backup and restore operations
- `USER_ACTION`: User interactions and API calls
- `STARTUP`: Application startup and initialization

## Testing

### Minimal Test Suite (Lean Mode)
The repository has been simplified to a fast, low‑maintenance test set focused on import sanity and core helper behavior. Heavy integration / connectivity diagnostics were removed to reduce noise and speed up CI.

Current tests (in `tests/core/`):
- `test_imports.py` – Verifies key modules import successfully with dummy environment variables.
- `test_database_config.py` – Checks `DatabaseManager` basic properties (e.g., `use_sqlserver`, log level change mechanics) without opening real connections.
- `test_logging_basic.py` – Ensures in‑memory debug ring buffer appends and logging helpers execute without exceptions.
- `sql_connectivity_tests.py` (root) – Lightweight stub preserving the historic public API (returns immediate SUCCESS) so `main.py` startup imports still work.

Removed legacy artifacts:
- Comprehensive data flow integration test harness
- Custom `test_runner.py`
- Extended connectivity benchmarking + legacy enforcement tests

### Running Tests
Pytest is used for simplicity:
```bash
pytest -q
```

### Design Principles of Minimal Suite
- **Fast**: No network, database, or external API calls.
- **Deterministic**: Uses fixed dummy environment vars; no timing or random variability.
- **Safety**: Never attempts to create engines or touch production resources during unit tests.

### Extending Tests (Optional)
If you later need richer validation:
1. Add new file under `tests/` (e.g., `tests/integration/…`).
2. Gate real DB usage behind explicit markers:
   ```python
   import os, pytest
   pytest.skip("needs real DB", allow_module_level=True) if not os.getenv("RCI_REAL_DB") else None
   ```
3. Use `pytest -m integration` with custom markers to separate slow tests.

### Why the Reduction?
The previous suite mixed diagnostics and unit testing, increasing maintenance cost and producing flaky results in constrained environments. The lean approach keeps confidence for core imports and utilities while avoiding setup complexity.

## Browser Compatibility

### Critical JavaScript APIs
1. **Device Motion API**: For accelerometer data capture
   - ✅ Chrome/Edge (Android/iOS): Full support
   - ✅ Safari (iOS): Requires permission request (iOS 13+)
   - ❌ Desktop browsers: Limited/No support
   - ⚠️ Firefox Android: Partial support

2. **Geolocation API**: For GPS coordinate collection
   - ✅ All modern browsers with user permission
   - 🔒 Requires HTTPS in production

3. **Fetch API**: For data submission to backend
   - ✅ All modern browsers (IE11+ with polyfill)

### Timezone Handling
- **Storage**: All data stored in UTC
- **Display**: Converted to Amsterdam time (CEST/CET) for user interface
- **Input handling**: Automatic timezone conversion for datetime inputs
- **Consistency**: Unified timezone handling across all components

## API Endpoints

### Data Collection
- `POST /bike-data`: Submit new sensor data with GPS and accelerometer values
- `POST /log`: Deprecated endpoint (maintained for backward compatibility)

### Data Retrieval
- `GET /logs`: Fetch recent measurements with optional limit
- `GET /filteredlogs`: Advanced filtering by device ID and date range
- `GET /device_ids`: List all devices with nicknames
- `GET /device_stats`: Detailed statistics for specific devices
- `GET /date_range`: Get available data time range

### Authentication
- `POST /login`: Authenticate and set session cookie
- `GET /auth_check`: Validate current session
- `GET /health`: Application health check

### Management (Authenticated)
- `GET /manage/tables`: Database table information
- `GET /manage/table_summary`: Table statistics and last update times
- `POST /manage/verify_*`: Schema and data verification endpoints
- `GET /debuglog/enhanced`: Enhanced debug logs with filtering

## Development Guidelines

### Code Style
- Follow PEP 8 for Python code
- Use meaningful variable names and comments
- Implement proper error handling with specific exception types
- Use type hints where applicable

### Database Operations
- Always use SQLAlchemy ORM methods through `db_manager`
- Implement proper transaction handling for multi-step operations
- Use connection pooling for better performance
- Log all database operations for debugging

### Frontend Development
- Use semantic HTML5 elements
- Implement responsive design principles
- Centralize common functions in `utils.js`
- Handle errors gracefully with user-friendly messages
- Implement proper loading states for async operations

### Security Considerations
- Never expose database credentials in frontend code
- Validate all user inputs on both client and server side
- Use HTTPS in production environments
- Implement proper session management
- Sanitize all user-generated content

## Performance Optimization

### Database
- Use connection pooling for better resource management
- Implement query optimization with proper indexing
- Use pagination for large result sets
- Cache frequently accessed data

### Frontend
- Minimize HTTP requests through bundling
- Implement lazy loading for large datasets
- Use efficient map rendering techniques
- Optimize image assets and use appropriate formats

### API
- Implement proper caching headers
- Use compression for large responses
- Implement rate limiting for abuse prevention
- Monitor response times and optimize slow endpoints
