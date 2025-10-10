# System Architecture Diagram

## Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Road Condition Indexer                            │
│                     FastAPI Web Application (Python 3.11)                │
└─────────────────────────────────────────────────────────────────────────┘
```

## System Architecture

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                                 CLIENT LAYER                                    │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Mobile     │  │    Web       │  │   External   │  │   Admin      │      │
│  │   Device     │  │   Browser    │  │   API        │  │   User       │      │
│  │ (Data Source)│  │ (Visualization)│ │   Clients    │  │ (Management) │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                  │                  │              │
│         └─────────────────┴──────────────────┴──────────────────┘              │
│                                    │                                           │
└────────────────────────────────────┼───────────────────────────────────────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                           PRESENTATION LAYER                                    │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                      Static Files (14 HTML Pages)                        │  │
│  ├─────────────────────────────────────────────────────────────────────────┤  │
│  │  • index.html      - Data Collection      • memo.html    - Voice Memos  │  │
│  │  • device.html     - Map Visualization    • monitor.html - Monitoring   │  │
│  │  • database.html   - DB Management        • shared.html  - File Sharing │  │
│  │  • maintenance.html - Admin Tools         • tools.html   - Utilities    │  │
│  │  • login.html      - Authentication       • + 6 more pages              │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                      JavaScript Components                               │  │
│  ├─────────────────────────────────────────────────────────────────────────┤  │
│  │  • Leaflet.js      - Interactive Maps     • utils.js    - Utilities     │  │
│  │  • DataTables      - Data Grids           • Custom JS   - App Logic     │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└────────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                           API LAYER (97 Endpoints)                              │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Public     │  │ Authentication│ │   Protected  │  │    Debug     │      │
│  │  Endpoints   │  │   Endpoints   │  │  Endpoints   │  │  Endpoints   │      │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤  ├──────────────┤      │
│  │ /health      │  │ /login       │  │ /manage/*    │  │ /debug/*     │      │
│  │ /bike-data   │  │ /auth_check  │  │ /api/*       │  │ /debuglog    │      │
│  │ /logs        │  └──────────────┘  │ 60+ routes   │  └──────────────┘      │
│  │ /device_ids  │                    └──────────────┘                         │
│  └──────────────┘                                                              │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                   FastAPI Application (main.py)                          │  │
│  ├─────────────────────────────────────────────────────────────────────────┤  │
│  │  • Route Handlers            • Request Validation (Pydantic)            │  │
│  │  • Authentication Middleware • Signal Processing (NumPy/SciPy)          │  │
│  │  • Session Management        • Azure SDK Integration                    │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└────────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                           BUSINESS LOGIC LAYER                                  │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                      Core Processing Functions                           │  │
│  ├─────────────────────────────────────────────────────────────────────────┤  │
│  │  • process_z_values()         - Signal processing (Butterworth filter)  │  │
│  │  • haversine_distance()       - GPS distance calculation                │  │
│  │  • calculate_roughness()      - Road roughness index                    │  │
│  │  • device_tracking()          - Device metadata management              │  │
│  │  • data_validation()          - Input validation and sanitization       │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                      External Services                                   │  │
│  ├─────────────────────────────────────────────────────────────────────────┤  │
│  │  • TranscriptionService       - Audio/video transcription               │  │
│  │  • AzureResourceManagement    - App Plan & SQL SKU management           │  │
│  │  • MonitoringService          - HTTP endpoint monitoring                │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└────────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                           DATA ACCESS LAYER                                     │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                    DatabaseManager (database.py)                         │  │
│  ├─────────────────────────────────────────────────────────────────────────┤  │
│  │                                                                           │  │
│  │  Connection Management          Data Operations          Management      │  │
│  │  ├─ Connection pooling          ├─ insert_bike_data()   ├─ backup_table()│ │
│  │  ├─ Auto-reconnection           ├─ get_logs()           ├─ verify_tables()│ │
│  │  ├─ Transaction handling        ├─ get_filtered_logs()  ├─ archive_logs()│ │
│  │  └─ Health checks               └─ execute_query()      └─ repair_db()   │  │
│  │                                                                           │  │
│  │  Logging & Audit                Device Management        Shared Objects   │  │
│  │  ├─ log_debug()                 ├─ upsert_device_info() ├─ CRUD ops     │  │
│  │  ├─ log_user_action()           ├─ get_device_stats()   ├─ File storage │  │
│  │  ├─ log_sql_operation()         └─ merge_devices()      └─ Base64 encode│  │
│  │  └─ get_debug_logs()                                                     │  │
│  │                                                                           │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                  Logging Utilities (log_utils.py)                        │  │
│  ├─────────────────────────────────────────────────────────────────────────┤  │
│  │  • LogLevel Enum (DEBUG, INFO, WARNING, ERROR, CRITICAL)                │  │
│  │  • LogCategory Enum (DATABASE, API, QUERY, CONNECTION, etc.)            │  │
│  │  • Stack trace capture & formatting                                     │  │
│  │  • In-memory debug ring buffer                                          │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└────────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                           DATABASE LAYER                                        │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                SQLAlchemy ORM + pymssql Driver                           │  │
│  ├─────────────────────────────────────────────────────────────────────────┤  │
│  │  • Connection Pooling (StaticPool)                                       │  │
│  │  • Automatic Reconnection                                                │  │
│  │  • Transaction Management                                                │  │
│  │  • No ODBC Required                                                      │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│                                    ▼                                            │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │              Azure SQL Server Database (11 Tables)                       │  │
│  ├─────────────────────────────────────────────────────────────────────────┤  │
│  │                                                                           │  │
│  │  Core Data Tables              Logging Tables            Feature Tables  │  │
│  │  ├─ RCI_bike_data (main)       ├─ RCI_debug_log         ├─ RCI_shared   │  │
│  │  ├─ RCI_bike_source_data       ├─ RCI_user_actions      ├─ RCI_memos    │  │
│  │  ├─ RCI_device_nicknames       └─ RCI_archive_logs      ├─ memo_archive │  │
│  │  │                                                       ├─ RCI_monitors │  │
│  │  │                                                       └─ RCI_monitor_r│  │
│  │  │                                                                        │  │
│  │  Features:                                                                │  │
│  │  • Automatic schema creation & migrations                                │  │
│  │  • Indexed queries for performance                                       │  │
│  │  • RCI_ prefix security filtering                                        │  │
│  │  • JSON backup support                                                   │  │
│  │  • Integrity checks & repair                                             │  │
│  │                                                                           │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└────────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                          INFRASTRUCTURE LAYER                                   │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                         Azure Web App (Linux)                            │  │
│  ├─────────────────────────────────────────────────────────────────────────┤  │
│  │  • Python 3.11 Runtime                                                   │  │
│  │  • Gunicorn + Uvicorn Workers                                            │  │
│  │  • Environment Variables (App Settings)                                  │  │
│  │  • Automatic Scaling (configurable)                                      │  │
│  │  • Health Check Endpoints                                                │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                         Optional Services                                │  │
│  ├─────────────────────────────────────────────────────────────────────────┤  │
│  │  • Azure Service Principal    - Resource management                      │  │
│  │  • Azure Key Vault            - Secrets management (proposed)            │  │
│  │  • Azure App Insights         - Monitoring (proposed)                    │  │
│  │  • Azure Blob Storage         - File storage (proposed)                  │  │
│  │  • Redis Cache                - Performance (proposed)                   │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└────────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                            CI/CD PIPELINE                                       │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                         GitHub Actions                                   │  │
│  ├─────────────────────────────────────────────────────────────────────────┤  │
│  │                                                                           │  │
│  │  Triggers:              Build:                  Deploy:                  │  │
│  │  ├─ Push to main        ├─ Setup Python 3.11   ├─ Azure Web App        │  │
│  │  ├─ Pull request        ├─ Install deps         ├─ Publish profile      │  │
│  │  └─ Manual dispatch     ├─ Run tests            └─ Environment vars     │  │
│  │                         └─ Create artifact                               │  │
│  │                                                                           │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└────────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Data Collection Flow
```
Mobile Device/Sensor
    │
    ├─ GPS Data (lat, lon, elevation, speed, direction)
    ├─ Accelerometer Data (Z-axis values)
    └─ Device ID
    │
    ▼
POST /bike-data API
    │
    ├─ Validate input (Pydantic)
    ├─ Check speed threshold (>7 km/h)
    └─ Process accelerometer data
        │
        ├─ Resample to constant rate
        ├─ Apply Butterworth filter (0.5-50 Hz)
        ├─ Calculate RMS (roughness)
        └─ Calculate distance (Haversine)
    │
    ▼
DatabaseManager.insert_bike_data()
    │
    ├─ Insert main record (RCI_bike_data)
    ├─ Insert raw data (RCI_bike_source_data)
    ├─ Update device metadata
    └─ Log user action
    │
    ▼
Azure SQL Server Database
    │
    └─ Data stored and indexed
```

### 2. Visualization Flow
```
User opens device.html
    │
    ▼
GET /filteredlogs?device_ids=X&start=Y&end=Z
    │
    ▼
DatabaseManager.get_filtered_logs()
    │
    ├─ Build parameterized query
    ├─ Apply filters (device, date range)
    ├─ Execute query
    └─ Return results
    │
    ▼
JavaScript Map Component
    │
    ├─ Initialize Leaflet map
    ├─ Create markers (color-coded by roughness)
    ├─ Draw polylines (route visualization)
    └─ Display statistics
```

### 3. Authentication Flow
```
User enters credentials
    │
    ▼
POST /login
    │
    ├─ Validate MD5 hash
    ├─ Create session cookie (httponly)
    └─ Log user action
    │
    ▼
Subsequent requests
    │
    ├─ password_dependency() checks cookie
    ├─ Validates hash matches
    └─ Allows/denies access
```

### 4. Monitoring Flow
```
Monitor Configuration (RCI_monitors)
    │
    ├─ URL to check
    ├─ Interval (seconds)
    └─ Enabled flag
    │
    ▼
Background Task (scheduled)
    │
    ├─ Fetch enabled monitors
    ├─ Execute HTTP requests
    ├─ Measure response time
    └─ Check status code
    │
    ▼
Store Results (RCI_monitor_results)
    │
    ├─ Timestamp
    ├─ Status code
    ├─ Response time (ms)
    ├─ Success/failure
    └─ Error message (if any)
    │
    ▼
Display in monitor.html
```

## Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Security Layers                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Network Layer                                            │
│     ├─ HTTPS/TLS encryption                                 │
│     ├─ Azure SQL Server firewall rules                      │
│     └─ IP whitelisting                                      │
│                                                              │
│  2. Application Layer                                        │
│     ├─ Cookie-based authentication (MD5 - to be upgraded)   │
│     ├─ Session management                                   │
│     ├─ Protected endpoints (60+)                            │
│     └─ Input validation (Pydantic)                          │
│                                                              │
│  3. Data Layer                                               │
│     ├─ Parameterized queries (SQL injection prevention)     │
│     ├─ RCI_ prefix filtering (table access control)         │
│     ├─ Connection pooling (resource protection)             │
│     └─ Audit logging (user actions, IPs)                    │
│                                                              │
│  4. Monitoring & Auditing                                    │
│     ├─ User action logging (RCI_user_actions)               │
│     ├─ Debug logging (RCI_debug_log)                        │
│     ├─ SQL operation logging                                │
│     └─ Startup diagnostics                                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Performance Considerations

```
┌─────────────────────────────────────────────────────────────┐
│                  Performance Features                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Database                                                    │
│  ├─ Connection pooling (SQLAlchemy)                         │
│  ├─ Indexed queries (timestamp, device_id, roughness)       │
│  ├─ Efficient data types                                    │
│  └─ Batch operations where possible                         │
│                                                              │
│  Application                                                 │
│  ├─ FastAPI async capabilities                              │
│  ├─ Minimal middleware overhead                             │
│  ├─ Efficient signal processing (NumPy/SciPy)               │
│  └─ Stateless design (scalable)                             │
│                                                              │
│  Frontend                                                    │
│  ├─ Minimal JavaScript libraries                            │
│  ├─ Client-side filtering                                   │
│  ├─ Lazy loading (proposed)                                 │
│  └─ Static asset serving                                    │
│                                                              │
│  Proposed Improvements                                       │
│  ├─ Redis caching layer                                     │
│  ├─ CDN for static assets                                   │
│  ├─ Database read replicas                                  │
│  └─ Response compression (gzip/brotli)                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Scalability Architecture

```
Current: Single Instance                    Proposed: Multi-Instance
┌──────────────────────┐                   ┌──────────────────────┐
│   Azure Web App      │                   │   Azure Front Door   │
│   (Single Instance)  │                   │   (Load Balancer)    │
│         ▼            │                   └──────────┬───────────┘
│   FastAPI App        │                              │
│         ▼            │                   ┌──────────┴───────────┐
│   Azure SQL Server   │                   │                      │
└──────────────────────┘                   ▼                      ▼
                                    ┌──────────────┐      ┌──────────────┐
                                    │  Web App 1   │      │  Web App 2   │
Limitations:                        │  (Instance)  │      │  (Instance)  │
• Single point of failure           └──────┬───────┘      └──────┬───────┘
• Limited concurrent users                 │                     │
• Regional availability only               └─────────┬───────────┘
                                                     │
                                            ┌────────▼────────┐
                                            │   Redis Cache   │
                                            │  (Shared State) │
                                            └────────┬────────┘
                                                     │
                                            ┌────────▼────────┐
                                            │  Azure SQL      │
                                            │  (Read Replicas)│
                                            └─────────────────┘
                                    
                                    Benefits:
                                    • High availability
                                    • Auto-scaling
                                    • Global distribution
                                    • Better performance
```

---

For detailed information, see:
- **FEATURES_AND_IMPROVEMENTS.md** - Complete feature documentation
- **FEATURES_SUMMARY.md** - Quick reference guide
- **DEVELOPMENT.md** - Developer guidelines
- **DEPLOYMENT.md** - Deployment documentation
