# Feature Catalog

This document inventories the implemented backend and platform features in this repository.

## 1. Core platform responsibilities

The application combines multiple capabilities under one FastAPI service:

- Road-condition ingestion and roughness indexing.
- Device lifecycle and nickname management.
- Data browsing/export and maintenance tooling.
- Debug and operational logging endpoints.
- Website/content monitor scheduler and history.
- Shared-link style records (`/api/shared`).
- Memo management and optional transcription pipeline.
- Audio/video tooling (noise reduction and media download/proxy features).

## 2. Environment-aware boot behavior

At startup, the application resolves configuration mode:

- **Azure Web App mode**: uses app settings environment variables.
- **GitHub Codespaces mode**: uses Codespaces environment variables.
- **Local mode**: attempts to load `.env` via `python-dotenv`.

Connectivity tests for SQL infrastructure are run during startup to fail fast with actionable diagnostics.

## 3. Data ingestion and roughness pipeline

### `POST /bike-data`
Primary endpoint for measurement ingest.

Core behavior:
- Validates payload with GPS + motion data and Z-axis samples.
- Computes average speed and applies a minimum speed threshold (`RCI_MIN_SPEED_KMH`, default 7 km/h).
- Applies preprocessing/filtering to sensor stream and computes roughness metrics.
- Stores standardized records in core tables.
- Supports optional source sample persistence for research/analysis.

Roughness pipeline characteristics:
- Resampling to stable sampling interval.
- Band-pass filtering approximately in the ride vibration range.
- RMS-derived roughness with additional vibration metrics computed for future use.

## 4. Logging, diagnostics, and observability

### Logging ingestion + retrieval
- `POST /log`: client log intake.
- `GET /logs`: recent logs.
- `GET /filteredlogs`: logs with filtering.

### Debug visibility
- `GET /debuglog`
- `GET /debuglog/enhanced`
- `GET /system_startup_log`
- `GET /sql_operations_log`

### Deep diagnostics
- `GET /debug/db_test`
- `GET /debug/db_stats`
- `POST /debug/test_insert`
- `GET /debug/data_flow_test`

### Log lifecycle management
- `GET /manage/debug_logs`
- `DELETE /manage/debug_logs`
- `POST /manage/log_config`
- `GET /manage/log_config`
- `POST /manage/archive_logs`

## 5. Device and identity features

- `GET /device_ids`: discover active/known devices.
- `GET /device_stats`: aggregate metrics by device.
- Nickname lifecycle:
  - `POST /nickname`
  - `GET /nickname`
  - `DELETE /nickname`
- `POST /manage/merge_device_ids`: merge duplicate device identities.
- `DELETE /device_data`: targeted cleanup.

## 6. Data browsing, editing, and maintenance APIs

Data management endpoints under `/manage` include:

- Discovery:
  - `/manage/tables`
  - `/manage/table_schema`
  - `/manage/table_summary`
  - `/manage/last_rows`
- Row/query views:
  - `/manage/table_rows`
  - `/manage/table_range`
  - `/manage/record`
  - `/manage/filtered_records`
- Write operations:
  - `/manage/update_record`
  - `/manage/delete_record`
  - `/manage/delete_filtered_records`
  - `/manage/delete_all`
  - `/manage/insert_testdata`
- Table lifecycle:
  - `/manage/backup_table`
  - `/manage/rename_table`
  - `/manage/test_table`
  - `/manage/repair_database`
- Structural checks:
  - `/manage/verify_tables`
  - `/manage/verify_data`
  - `/manage/verify_indexes`
  - `/manage/verify_constraints`

Security posture:
- Table operations are constrained to project table naming conventions (`RCI_` prefixed), limiting accidental or malicious access to unrelated schema objects.

## 7. Threshold and configuration endpoints

- `GET /api/thresholds`
- `POST /api/thresholds`

Used for runtime threshold visibility/updates where enabled by the frontend workflow.

## 8. Monitor subsystem

Purpose: service, URL, and content monitoring with logs + history.

### Metadata and CRUD
- `GET /api/monitors/metadata`
- `GET /api/monitors`
- `POST /api/monitors`
- `PUT /api/monitors/{monitor_id}`
- `DELETE /api/monitors/{monitor_id}`
- `GET /api/monitors/{monitor_id}`
- `POST /api/monitors/{monitor_id}/toggle`

### Execution and results
- `POST /api/monitors/{monitor_id}/run`
- `GET /api/monitors/{monitor_id}/logs`
- `GET /api/monitors/{monitor_id}/history`

Service types include HTTP/HTTPS, generic URL checks, TCP/UDP ports, DNS, SMTP/IMAP/POP3, FTP/SFTP/SSH, and ICMP ping.

## 9. Shared records feature

- `POST /api/shared`
- `GET /api/shared`
- `GET /api/shared/{shared_id}`
- `PUT /api/shared/{shared_id}/note`
- `DELETE /api/shared/{shared_id}`

Supports persisted shared snippets/records with update + deletion lifecycle.

## 10. Memo + transcription feature set

- `POST /api/memos`
- `GET /api/memos`
- `PUT /api/memos/{memo_id}`
- `DELETE /api/memos/{memo_id}`
- `POST /api/memos/transcribe`

The transcription flow is mediated by `transcription.py` service abstractions and explicit error classes for configuration and service/runtime failures.

## 11. Media tooling

### AV noise reduction
- `POST /api/av/noise-reduction`
- `GET /api/av/noise-reduction/{token}`

Supports asynchronous/queued style processing semantics where a token can be used to retrieve output artifacts.

### Video tooling + external media
- `POST /tools/download_video`
- Dumpert integrations:
  - `GET /api/dumpert/toppers/{page}`
  - `GET /api/dumpert/media-diagnostics`
  - `GET /api/dumpert/media-proxy`

## 12. Health/auth/navigation support endpoints

- Auth/session support:
  - `POST /login`
  - `GET /auth_check`
- Health:
  - `GET /health`
- Navigation/static entrypoints:
  - `/`
  - `/welcome.html`
  - `/shared.html`
  - plus direct static helper routes for assets/partials.

## 13. Export and utility endpoints

- `GET /gpx`: GPX export for ride data traces.
- `GET /date_range`: date bounds for record browsing/filter forms.

## 14. Data model highlights

Core table families include:
- Bike measurements and optional source samples.
- Debug logs and archive logs.
- Device nickname mapping and metadata.
- User action trail.
- Monitor entities and monitor run history/logs.
- Shared and memo records.

The schema is created/verified on startup via the database layer to reduce manual drift.

## 15. Test suite landscape

Test assets are grouped by depth/scope:
- `tests/core`: foundational behavior and subsystem integrity.
- `tests/extended`: larger-scope and connectivity-focused scenarios.
- `tests/legacy`: compatibility/regression cases.
- Top-level tests for connection string behavior and end-to-end style validations.

## 16. Related files and where feature logic lives

- API and app lifecycle: `main.py`
- Database and table management: `database.py`
- Logging utilities: `log_utils.py`
- Transcription abstraction: `transcription.py`
- SQL connectivity startup tests: `tests/sql_connectivity_tests.py`
