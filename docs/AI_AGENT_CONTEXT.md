# AI Agent Context Playbook

Use this document as a fast-operating context pack before making changes in this repository.

## 1. Repository intent

Road Condition Indexer is a multi-purpose FastAPI application centered on road-condition ingest and indexing, with extended operational tooling, diagnostics, monitoring, memo/transcription utilities, and media workflows.

## 2. High-signal file map

- `main.py`: API routes, startup lifecycle, and app orchestration.
- `database.py`: table constants, persistence layer, data access and safety filters.
- `log_utils.py`: unified logging helpers and log level/category conventions.
- `transcription.py`: transcription service and error model.
- `static/`: all website pages/assets/js used by the served frontend.
- `tests/`: test suites grouped by scope (`core`, `extended`, `legacy`, top-level).

## 3. Feature domains and likely edit targets

- Ingestion/roughness: `main.py`, `database.py`, data table schema docs.
- UI behavior: `static/*.html`, `static/*.js`, `static/site.css`, route exposure in `main.py`.
- Monitor subsystem: monitor endpoints in `main.py`, corresponding monitor UI scripts.
- Maintenance/admin behavior: `/manage/*` routes + maintenance pages.
- Memo/transcription: memo routes in `main.py`, service code in `transcription.py`, memo page scripts.

## 4. Operational assumptions

- Azure SQL configuration is required for full runtime operation.
- Startup executes SQL connectivity checks and reports diagnostics.
- Static pages are expected to be directly routable under explicit endpoints.
- The app mixes end-user features and admin/debug surfaces in one process.

## 5. Safe change workflow for agents

1. Read relevant docs first:
   - `README.md`
   - `DEVELOPMENT.md`
   - `docs/FEATURE_CATALOG.md`
   - `docs/WEBSITE_GUIDE.md`
2. Locate exact call sites/routes/static integrations before editing.
3. Make smallest change set that satisfies the request.
4. Update documentation in the same PR when behavior changes.
5. Run tests only when functionality changes (skip for doc-only updates when instructed).

## 6. Documentation update contract

If code/behavior changes, update at least one of:
- `docs/FEATURE_CATALOG.md` (backend/API/data behavior)
- `docs/WEBSITE_GUIDE.md` (page/UX/module behavior)
- `docs/OPERATIONS_RUNBOOK.md` (setup/ops/startup/deployment behavior)
- `README.md` (project-level behavior changes)

## 7. Agent checklist before commit

- [ ] Changed files are scoped and intentional.
- [ ] Docs updated for all behavior changes.
- [ ] No accidental endpoint naming drift.
- [ ] Static asset paths and routes stay consistent.
- [ ] Destructive admin endpoints were not modified without safety notes.
- [ ] Commit message summarizes both code and documentation impact.

## 8. Rapid task routing for AI agents

- “Add endpoint” → `main.py`, request model, db usage, docs update.
- “Fix table query bug” → `database.py`, related route(s), tests, docs.
- “Update monitor UI” → `static/monitor.*`, monitor API route checks, docs.
- “Add page” → new `static/*.html`, route in `main.py`, CSS/JS updates, docs.
- “Deploy issue” → `DEPLOYMENT.md`, startup scripts, env vars, troubleshooting docs.

## 9. Change impact matrix

| Change type | Must update docs |
|---|---|
| New/changed endpoint | `docs/FEATURE_CATALOG.md` (+ `README.md` if user-visible) |
| New/changed page/UI flow | `docs/WEBSITE_GUIDE.md` |
| Setup/config/startup change | `docs/OPERATIONS_RUNBOOK.md` + `README.md` |
| New troubleshooting path | `TROUBLESHOOTING.md` |
| Static asset loading/routing change | `STATIC_FILES_GUIDE.md` + `docs/WEBSITE_GUIDE.md` |

## 10. Definition of done for agent-driven repository updates

A change is not done until:
- implementation is complete,
- related docs are updated,
- and commit/PR text explains what changed and why.
