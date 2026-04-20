# Operations Runbook

This runbook captures setup, startup, operation, and recovery workflows for this repository.

## 1. Prerequisites

- Python runtime compatible with repository dependencies.
- Network access from runtime to Azure SQL (port 1433 unless customized).
- Environment variables configured for database connectivity.

## 2. Required environment variables

Mandatory variables:

- `AZURE_SQL_SERVER`
- `AZURE_SQL_DATABASE`
- `AZURE_SQL_USER`
- `AZURE_SQL_PASSWORD`
- `AZURE_SQL_PORT` (typically `1433`)

Environment model:
- **Local**: loaded from `.env` when available.
- **Azure App Service**: set as App Settings.
- **Codespaces**: set in environment/secrets for workspace.

## 3. Installation workflow

```bash
pip install -r requirements.txt
```

Optional environment verification:

```bash
python setup_env.py
```

## 4. Startup workflow

Local API startup example:

```bash
uvicorn main:app --reload --host 0.0.0.0
```

Startup behavior expectations:
- Environment mode detection logs.
- SQL connectivity checks execute.
- Database layer verifies/creates required tables.
- Static files become available under configured routes.

## 5. Helper scripts

- `startup.sh`: Linux startup helper.
- `azure_startup.sh`: Azure-targeted startup helper.
- `startup_local.ps1`: PowerShell local startup helper.
- `validate-config.ps1`: config validation helper.
- `migrate_db.py`: database migration/adjustment workflow.

## 6. Routine operational workflows

### 6.1 Verify service health
- Call `GET /health`.
- Review startup/system logs (`/system_startup_log`, `/sql_operations_log`).

### 6.2 Validate DB visibility
- Use maintenance endpoints (`/manage/tables`, `/manage/table_summary`, `/manage/last_rows`).
- Confirm expected `RCI_` tables exist and are populated.

### 6.3 Manage logs
- Query logs via `/logs`, `/filteredlogs`, `/debuglog/enhanced`.
- Archive/cleanup via `/manage/archive_logs` and debug log management endpoints.

### 6.4 Operate monitors
- Confirm metadata (`/api/monitors/metadata`).
- Create/update/toggle monitors.
- Trigger on-demand run (`/api/monitors/{id}/run`) during incident checks.

### 6.5 Data repair and recovery
- Run table verification endpoints (`verify_*`).
- Use backup + repair endpoints.
- Use row-level edit/delete endpoints only with explicit audit context.

## 7. Security and safety constraints

- Database table tooling is limited to application table prefixes for isolation.
- Destructive endpoints exist; prefer backups before destructive operations.
- Keep auth/session protections enforced for admin surfaces in production.

## 8. Deployment and environment parity

- Use `DEPLOYMENT.md` for platform-specific deployment details.
- Keep local/test/prod config names aligned to reduce drift.
- Validate schema and connectivity in each environment before releasing feature changes.

## 9. Incident response quick flow

1. Check `/health`.
2. Inspect startup + SQL ops logs.
3. Run DB diagnostics endpoints.
4. Validate monitor subsystem behavior.
5. Confirm core ingestion endpoint status (`/bike-data`) via controlled test payload.
6. Capture findings in incident note and update troubleshooting docs.

## 10. Operational documentation obligations

Whenever operations-related behavior changes (startup, config, scripts, deployment, maintenance API semantics):

- Update this runbook in the same PR.
- Update top-level operational docs (`README.md`, `DEPLOYMENT.md`, `TROUBLESHOOTING.md`) as needed.
- Add a changelog note in the PR description explaining operator impact.
