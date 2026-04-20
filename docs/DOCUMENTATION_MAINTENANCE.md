# Documentation Maintenance Policy

This policy defines how documentation must be maintained as the repository evolves.

## 1. Core rule

**Any behavior change must include documentation updates in the same pull request.**

Behavior change includes:
- API contract changes.
- Data model/schema changes.
- Setup/deployment/startup changes.
- Frontend page/flow/UI changes.
- Logging/monitoring/admin process changes.

## 2. Ownership model

- PR author owns initial documentation updates.
- Reviewer verifies docs are accurate and complete before approval.
- Maintainers enforce policy during merge review.

## 3. Required doc touchpoints by change type

### API and backend logic
Update:
- `docs/FEATURE_CATALOG.md`
- `README.md` (if externally visible behavior changed)
- `DEVELOPMENT.md` (if workflow/testing guidance changed)

### Website/frontend behavior
Update:
- `docs/WEBSITE_GUIDE.md`
- `STATIC_FILES_GUIDE.md` (if static conventions/routing changed)

### Operations/setup/deployment
Update:
- `docs/OPERATIONS_RUNBOOK.md`
- `README.md`
- `DEPLOYMENT.md` or `TROUBLESHOOTING.md` where applicable

### AI/developer workflow
Update:
- `docs/AI_AGENT_CONTEXT.md`

## 4. PR template checklist (copy into PR descriptions)

- [ ] I updated docs for all changed behavior.
- [ ] I updated endpoint listings if API surface changed.
- [ ] I updated website docs if pages/JS flows changed.
- [ ] I updated operations docs if setup/startup/deployment changed.
- [ ] I verified old instructions were removed or corrected.
- [ ] I included migration/compatibility notes when relevant.

## 5. Monthly documentation review cadence

Perform a repo-level documentation audit at least once per month:

1. Compare `main.py` routes vs `docs/FEATURE_CATALOG.md`.
2. Compare `static/` pages/modules vs `docs/WEBSITE_GUIDE.md`.
3. Compare startup scripts/env handling vs `docs/OPERATIONS_RUNBOOK.md` and `README.md`.
4. Verify troubleshooting entries match currently observed failure modes.
5. Open follow-up issues for stale docs and label as `documentation-debt`.

## 6. Release-time documentation gate

Before a release tag/deployment:
- Confirm no pending doc updates remain in open PR comments.
- Confirm configuration examples are still valid for current environments.
- Confirm monitor/tooling pages listed in docs still exist and are reachable.

## 7. Quality standards for docs

Documentation should be:
- Accurate (matches current code behavior).
- Actionable (contains specific commands/paths/endpoints).
- Discoverable (linked from hub docs and top-level docs).
- Concise but complete (enough for humans and AI agents to act safely).

## 8. Handling breaking changes

When a change is breaking:
- Add an explicit “Breaking Change” section in updated docs.
- Include migration steps and rollback notes.
- Mark removed endpoints/pages/processes as deprecated then removed, where feasible.

## 9. Fast stale-doc detection workflow

Use these quick checks:
- Route drift: scan `@app.<method>(...)` in `main.py` against feature catalog.
- Static drift: compare `static/*.html` and `static/*.js` against website guide lists.
- Script drift: compare startup/migration script behavior against runbook instructions.

## 10. Non-compliance handling

If PR behavior changes without doc updates:
- Block merge.
- Request explicit doc updates.
- Require follow-up patch only if emergency change had to ship first.
