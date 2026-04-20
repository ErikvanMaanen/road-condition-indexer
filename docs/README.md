# Documentation Hub

This `docs/` directory is the canonical guide for understanding, operating, and extending the Road Condition Indexer repository.

## Who this documentation is for
- Developers shipping code changes.
- Operators deploying and maintaining environments.
- QA contributors validating behavior.
- AI agents that need complete project context quickly.

## Document map

1. **[AI Agent Context](./AI_AGENT_CONTEXT.md)**
   - Fast orientation for autonomous agents.
   - Architecture, conventions, and safe-change workflow.
   - Where to look first for specific tasks.

2. **[Feature Catalog](./FEATURE_CATALOG.md)**
   - Comprehensive backend and data feature inventory.
   - API surface grouped by domain.
   - Data processing, logging, monitor services, memo/transcription, and media tooling.

3. **[Website Guide](./WEBSITE_GUIDE.md)**
   - All pages in the `static/` site and what they do.
   - Key client-side modules and user journeys.
   - Notes on partials and static asset routing.

4. **[Operations Runbook](./OPERATIONS_RUNBOOK.md)**
   - Local setup, environment model, startup scripts, and production operation.
   - Database expectations, common workflows, and troubleshooting flow.

5. **[Documentation Maintenance](./DOCUMENTATION_MAINTENANCE.md)**
   - Required process to keep documentation updated.
   - PR checklist and ownership expectations.
   - Change-impact matrix for doc update triggers.

## Existing top-level docs to continue using
- `README.md`: high-level project overview.
- `DEVELOPMENT.md`: engineering and test guidance.
- `DEPLOYMENT.md`: deployment-specific workflow.
- `TROUBLESHOOTING.md`: issue diagnosis and remediation.
- `STATIC_FILES_GUIDE.md`: static file conventions and pitfalls.

## Suggested reading order for onboarding
1. `README.md`
2. `docs/AI_AGENT_CONTEXT.md`
3. `docs/FEATURE_CATALOG.md`
4. `docs/WEBSITE_GUIDE.md`
5. `docs/OPERATIONS_RUNBOOK.md`
6. `docs/DOCUMENTATION_MAINTENANCE.md`

## Maintenance policy
Documentation in this folder is expected to be updated **in the same pull request** as the related code whenever behavior changes.

See [Documentation Maintenance](./DOCUMENTATION_MAINTENANCE.md) for the required process.
