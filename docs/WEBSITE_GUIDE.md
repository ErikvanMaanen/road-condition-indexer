# Website Guide

This guide documents the web UI delivered from `static/` and mapped by FastAPI routes.

## 1. Website architecture

The website is server-hosted static content with API-driven dynamic behavior.

- HTML pages live in `static/`.
- Shared JS modules provide UI behavior and API calls.
- FastAPI serves the pages directly via explicit routes and also mounts `static/` assets.
- Feature pages call backend endpoints for data retrieval, updates, diagnostics, and tooling workflows.

## 2. Primary pages and their purpose

### Core experience
- `static/index.html`: main interface for map/data workflows.
- `static/map-partial.html`: map-focused content used as shared UI fragment.
- `static/logs-partial.html`: log-viewing fragment.
- `static/shared.html`: shared record rendering and interactions.

### Authentication and access
- `static/login.html`: sign-in page wired to `/login` and `/auth_check` behavior.

### Operational/admin pages
- `static/maintenance.html`: database + infrastructure management views.
- `static/database.html`: data and schema-focused operations.
- `static/device.html`: device-centric management and visibility.
- `static/tools.html`: general-purpose utilities and operational helpers.

### Feature-specific pages
- `static/memo.html`: memo CRUD and transcription entrypoint UI.
- `static/monitor.html`: monitor creation, toggling, execution, and history display.
- `static/av-tools.html`: media/noise-reduction tooling UI.
- `static/dumpert.html`: Dumpert content browsing.
- `static/dumpert-player.html`: media playback/proxy consumption view.

### Supporting/special pages
- `static/solution.html`, `static/chris.html`, `static/timezone-test.html`: environment/support pages used for specific workflows or testing.

## 3. Frontend JavaScript modules

- `static/utils.js`: common helper utilities used across pages.
- `static/map-components.js`: map rendering and map UI composition.
- `static/memo.js`: memo page feature logic.
- `static/monitor.js`: monitor UI and API interactions.
- `static/av-tools.js`: media tool page API orchestration.

## 4. Styling and assets

- `static/site.css`: main project styling.
- `static/leaflet.css`, `static/leaflet.js`: map dependency assets.
- `static/logo.png`, `static/favicon.ico`: branding/icons.
- `static/lib/`: additional local library resources.

## 5. Navigation model

Common user journeys:
1. Login / auth check.
2. Main map + logs for core road-condition data visibility.
3. Device/database/maintenance views for administration.
4. Feature-specific tools (monitor, memos, AV tools, Dumpert).

## 6. Frontend-to-backend integration patterns

Patterns used across pages:
- JSON API requests via `fetch`.
- Partial loading for composable UI sections (`map-partial`, `logs-partial`).
- Polling/refresh for logs, monitor results, and long-running media tasks.
- CRUD form patterns for records, nicknames, memos, and monitors.

## 7. Static file conventions

When adding/updating static resources:
- Place new page/component files under `static/`.
- Keep JavaScript modular and feature-focused.
- Ensure route exposure in `main.py` if direct serving route is needed.
- Follow `STATIC_FILES_GUIDE.md` to avoid MIME/CORB/caching pitfalls.

## 8. Website change checklist

For every perceptible UI or UX change:
- Update this file’s page/module descriptions.
- Update API dependencies in `docs/FEATURE_CATALOG.md` if endpoint usage changed.
- Update `README.md` and/or `STATIC_FILES_GUIDE.md` when setup or static conventions change.
- Include screenshots in PRs for visual changes (where tooling is available).

## 9. Known integration dependencies

- Login-dependent sections depend on auth endpoints and session behavior.
- Map views depend on location + roughness data retrieval endpoints.
- Maintenance/database pages depend on `/manage/*` APIs.
- Monitor page depends on `/api/monitors/*` endpoints and service metadata.
- Memo page depends on memo endpoints and optional transcription provider configuration.
