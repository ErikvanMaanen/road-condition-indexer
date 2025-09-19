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

## Frontend Theming & Styling System

All pages now share a centralized design system defined in `static/site.css`. This system replaces prior inline and per‑page embedded styles, enabling consistent light/dark theming, component reuse, and easier accessibility compliance.

### Design Tokens (CSS Custom Properties)
Defined at `:root` (light) and `[data-theme="dark"]` scopes:
- Color Core: `--rci-primary`, `--rci-primary-accent`, semantic status colors (`--rci-danger`, `--rci-warning`), success / error surfaces & text (`--rci-success-*`, `--rci-error-*`).
- Surfaces & Structure: `--rci-bg`, `--rci-bg-alt`, `--rci-surface`, `--rci-surface-alt`, `--rci-border`, `--rci-shadow`.
- Typography: `--rci-font`, `--rci-text`, `--rci-text-muted`, `--rci-link`.
- Auth Gradient / Specialized: `--rci-auth-gradient-start`, `--rci-auth-gradient-end`, `--rci-auth-card-bg`, `--rci-auth-card-shadow`.
- Focus: `--rci-focus-ring` (box‑shadow applied on focusable elements via `.focus-ring:focus`).

When adding new tokens:
1. Prefer semantic naming (e.g. `--rci-danger-accent`) over direct hues (`--rci-red-500`).
2. Define BOTH light and dark values (place dark mode inside `[data-theme="dark"]`).
3. Reference tokens (e.g. `color:var(--rci-text)`) instead of raw hex in component rules.

### Theme Switching
Handled in shared JavaScript (`utils.js`):
1. Reads persisted preference from `localStorage` key `theme`.
2. Falls back to system preference via `matchMedia('(prefers-color-scheme: dark)')`.
3. Applies `document.documentElement.dataset.theme = 'dark' | 'light'`.
4. Toggle buttons use the `.theme-toggle` class and simply invert the stored value.

To add a toggle to a new page:
```html
<button id="themeToggle" class="theme-toggle" type="button">Toggle Theme</button>
<script>/* ensure utils.js loaded globally */</script>
```
If the shared nav partial already injects it, do not duplicate.

### Utility Classes (Selected)
Spacing & Layout: `.mb-1`, `.mb-05`, `.mt-05`, `.mt-1`, `.flex`, `.flex-wrap`, `.flex-1`, `.gap-05`, `.gap-035`, `.items-center`, `.w-100`, `.w-120`, `.w-80`, `.w-60`, `.inline-block`, `.mr-05`, `.ml-05`.
Containers / Surfaces: `.rci-card`, `.panel-soft`, `.border`, `.rounded-4`, `.bg-surface`, `.bg-alt`, `.json-editor-container`.
Typography: `.mono`, `.mono-tiny`, `.text-sm`, `.text-xs`, `.white-pre`.
Visibility / State: `.hidden`, `.hidden-initial` (script will reveal), `.status-message`, `.status-success`, `.status-error`.
Auth / Theming: `.auth-screen`, `.auth-card`, `.theme-toggle`, `.focus-ring`.

Principles:
- Utilities stay atomic; avoid combining unrelated concerns (e.g., no multi‑property catch‑alls).
- If a pattern is used ≥3 times and is semantic ("panel", "card"), promote it to a component class.
- Use utilities for layout tweaks; component classes own structural styling.

### Component Patterns
Implemented components (not exhaustive):
- Modal: `.modal`, `.modal-content` (shared surface, tokenized border/shadow).
- Collapsible Sections: `.section`, `.section-header`, `.section-content` (Tools page & logs/settings panels reuse pattern).
- Time Range Slider: `.time-range-*` classes (range handles, track, labels) fully tokenized.
- Logs Table: `.logs-table`, `.log-level.*`, `.log-filters` (monospace rows + sticky header).
- Diff Viewer: `.diff-panel`, `.diff-added|removed|modified|unchanged` (light/dark adaptive backgrounds with high contrast borders).
- JSON Tree: `.json-*` with semantic color classes for data types.
- Map Component: `#map`, `.fullscreen-btn`, roughness filter layout (`#roughness-filter-container`, `.range-filter`, `.range-display`).
- Auth Layout: `.auth-screen`, `.auth-card`, `.auth-message` variants (supports dark mode automatically via tokens).

When creating a new component:
1. Start with semantic container class (e.g., `.statistics-panel`).
2. Use child element classes for structure (`.statistics-panel-header`, `.statistics-panel-body`).
3. Use only token refs and existing utilities; avoid new hardcoded color values.
4. Consider required states (hover, focus, expanded) up front to avoid inline patches later.

### Extending Dark Mode
Most components inherit automatically. Only define dark overrides when the light palette uses translucent or very light backgrounds that would lose contrast on dark surfaces.

Pattern for overrides:
```css
[data-theme="dark"] .my-component { background:var(--rci-surface-alt); }
```
Avoid duplicating properties that already inherit appropriately.

### Accessibility Guidelines
Contrast Targets:
- Text vs background: WCAG AA (≥ 4.5:1 for normal text, ≥ 3:1 for large / UI inactive states acceptable with context).
- Interactive states (buttons, toggles, links) must have a visible :hover and :focus style distinct from rest state.

Implemented Features:
- Focus ring via `.focus-ring` + `--rci-focus-ring` shadow.
- Color alone not used for log severity (border-left + level badge label text).
- Selects and file inputs in tools & logs panels include `aria-label` when no `<label>` present.
- Status messages have both color and icon potential (future enhancement: add inline SVGs if needed).

Recommended Testing Steps:
1. Temporarily force dark mode: `document.documentElement.dataset.theme='dark'`.
2. Tab through interactive elements verifying ring visibility on low-contrast displays.
3. Use a contrast checker on primary text vs `--rci-surface` and badge backgrounds.
4. Zoom to 200% to confirm layout integrity (flex & grid components should wrap gracefully).

### Adding New Utilities
Add only if:
- The style is small (1–2 properties) AND
- It appears or is projected to appear in ≥3 distinct components.
Prefer semantic component evolution over a proliferation of one-off utilities.

### Removing Legacy Inline Styles
All major pages/partials have been cleaned. If new inline styles are introduced during rapid prototyping, migrate them into either:
- A component class (preferred if tightly coupled to a feature) OR
- An existing utility combination.

### Example: Creating a New Panel
```html
<div class="statistics-panel rci-card mb-1">
   <div class="statistics-panel-header flex-row space-between">
      <h3 class="m-0">Live Metrics</h3>
      <button class="btn btn-small focus-ring" type="button">Refresh</button>
   </div>
   <div class="statistics-panel-body mono text-sm">Loading…</div>
</div>
```
```css
.statistics-panel-header { border-bottom:1px solid var(--rci-border); padding:4px 8px; }
.statistics-panel-body { padding:8px; }
```

### Performance Considerations
- Centralized stylesheet reduces duplicate CSS bytes and improves caching.
- Avoid expensive universal selectors (`*`) or deep descendant chains in new additions.
- Group related component rules; keep token declarations flat (no nested calc chains) for faster render.

### Lint / Consistency Checklist
- No hex colors outside token blocks.
- Component selectors prefixed or scoped to prevent collision with vendor libs (`.rci-*` for generic utilities/patterns).
- Light/Dark parity verified (if a light token is added, dark counterpart must be added unless intentionally identical).

---
This section will evolve as new UI modules are added. Treat `site.css` as the canonical design layer; keep JS strictly for behavior, not presentation.

