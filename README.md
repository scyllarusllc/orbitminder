# OrbitMinder

**Your projects. Always in sight.**

OrbitMinder is an open-source, personal AI project command center. Its goal is to consolidate projects, follow-ups, deadlines and delegated agent work into one daily view.

**Status (2026-11-19):** early, read-only prototype. The Python CLI supports local example JSON and GitHub repository/activity summaries. A Next.js website, Google sign-in code, a protected single-owner GitHub brief API, and an on-demand private dashboard are implemented in source, but production deployment, live Google OAuth and end-to-end behavior are **not verified**. Gmail OAuth connection, Calendar, full cross-source sync and real agent execution are not integrated; a read-only Gmail metadata adapter exists in source. GitHub activity is sampled; it does not prove task completion.

## Why

Your projects may live across GitHub, Gmail, calendar, personal planning and multiple AI agents. OrbitMinder is intended to answer:

1. What changed since yesterday?
2. What are my three best next actions?
3. What is waiting, blocked, or due soon?

## Quick start

Requires Python 3.10+; no external dependencies.

```bash
python3 -m orbitminder.cli --data examples/projects.json
```

The command above uses deterministic sample data, **not** a live sync.

### GitHub live repository inventory (read-only)

```bash
# Public repositories, no credentials required
python3 -m orbitminder.cli --github-owner scyllarusllc

# Optional: include accessible private repositories with a least-privilege token
# Export GITHUB_TOKEN privately in your shell; never commit it or paste it into logs.
python3 -m orbitminder.cli --github-owner scyllarusllc --github-limit 100

# Activity-aware brief: last 7 days of commits and currently open PRs/issues
python3 -m orbitminder.cli --github-owner scyllarusllc --github-activity --github-limit 20 --activity-max-repos 10 --activity-days 7

```

The GitHub inventory reads repository metadata only (name, URL, archived state, last push, visibility and fetch timestamp). The current daily brief includes those repositories as active project records with a generic review action. Without --github-activity it does **not** fetch pull requests/issues or infer actual task priority. With --github-activity, it makes up to three additional read-only GitHub API requests per checked repository (commits, open PRs, open issues); it excludes PRs from the issue count, sorts checked project recommendations by simple open-item heuristics, and never claims work is complete. This is a triage heuristic, not AI analysis. To limit API use, activity checking defaults to the first 10 nonarchived repositories out of the first 30 returned repositories; other repositories are not activity-verified. Counts are lower bounds if a query returns 100 items, since pagination of activity is not implemented. An HTTP/API error stops the command rather than returning a misleading empty inventory. Without GITHUB_TOKEN, only public repos are included. With it, only repositories owned by the selected account and accessible to that token are included. The token is read from the environment and not persisted.
 The existing ChatGPT "Mission Control" daily automation is separate and remains unchanged.

## Development progress and next tasks

Updated **2026-11-19** from the `main` branch. **Current focus:** OM-006–009 storage/freshness/dashboard read path in source, plus OM-011 read-only Gmail metadata adapter in source (separate OAuth consent pending). Live data import and production deployment remain pending; automated test suites were removed at the owner's request. This checklist reports **source-code implementation**, not production readiness. A checked box is not a claim of successful deployment or live integration. Work in the order below; keep the read-only, self-hostable MVP as the default.

### Completed in source

- [x] **OM-001 — CLI project brief:** deterministic local project input, ranked next actions, waiting/blocked/due summaries and JSON output.
- [x] **OM-002 — Read-only GitHub inventory:** repository metadata and sampled recent commits, open PRs and issues, with source URLs.
- [x] **OM-003 — Web foundation:** Next.js homepage, Google sign-in integration code, protected dashboard shell and owner allowlist checks.
- [x] **OM-004 — On-demand GitHub dashboard:** authenticated API backed by the Python CLI and a manual refresh UI.
- [x] **OM-005 — Dashboard activity sections:** display sampled GitHub counts, next actions, waiting/blocked/due lists and unverified sources (`a1bc347`). No live deployment claim.

### Next milestone — durable, trustworthy project data (P0)

- [ ] **OM-006 — Define normalized models (SOURCE IMPLEMENTED, NOT LIVE-VERIFIED):** owner-scoped SQLite tables for project, source record, sync run, follow-up and agent activity are now in [`migrations/0001_initial.sql`](migrations/0001_initial.sql), with semantics in [`docs/data-model.md`](docs/data-model.md). **Remaining before checking complete:** manually verify migration and owner isolation in an authorized environment; schema is not yet deployed.
- [ ] **OM-007 — SQLite persistence (IMPLEMENTED IN SOURCE, VERIFICATION PENDING):** `orbitminder/storage.py` now creates a private local database and provides owner-scoped project/source upserts, deduplication, and reads. **Remaining:** integrate with the actual backend and manually verify restart and isolation behavior; no live integration claimed.
- [ ] **OM-008 — Freshness tracking (BACKEND SOURCE IMPLEMENTED, UI PENDING):** `ProjectStore.record_sync`, `latest_sync` and `list_source_freshness` retain cached records and report provider `unchecked` / `succeeded` / `partial` / `failed` states separately from source verification. A failed/partial run makes displayed source freshness `stale` and does not erase last success; **Remaining:** manually verify provider failures and the authenticated UI/API handling without stale-as-live claims.
- [ ] **OM-009 — Dashboard saved overview (SOURCE IMPLEMENTED; VERIFICATION PENDING):** added `orbitminder/saved_overview.py`, authenticated `/api/saved-projects`, and the `SavedProjects` panel. It reads owner-scoped historical SQLite projects, next actions, source links and last sync states; panel reload is separate from the existing on-demand `Check GitHub`. **Remaining:** configure/populate a real private DB and manually verify browser reload/security; no live-source freshness claim.
- [ ] **OM-010 — Manual release verification (NO AUTOMATED TEST SUITE):** after integration, manually review migration, ownership boundaries, provider failure behavior, login and UI rendering. The owner requested removal of all automated test cases; do not claim these behaviors are verified until they have been checked in an authorized environment.

### Email and calendar sources (P1)

- [ ] **OM-011 — Gmail read-only adapter (PYTHON SOURCE IMPLEMENTED, OAUTH PENDING):** [`gmail_metadata.py`](orbitminder/gmail_metadata.py) provides bounded, metadata-only Gmail reads with the `gmail.metadata` scope; [`gmail_import.py`](orbitminder/gmail_import.py) imports source references into owner-scoped SQLite records and logs partial/failure sync states. No mail sending or deleting is implemented. **Remaining:** separate consent/token management, authenticated account binding, website connection UI, manual verification. See [`docs/gmail-readonly.md`](docs/gmail-readonly.md).
- [ ] **OM-012 — Mail follow-up review:** suggest waiting-for/reply follow-ups from source evidence; require user review before saving or delegating. **Done when:** proposals show uncertainty and a link back to the originating email.
- [ ] **OM-013 — Calendar read-only adapter:** import upcoming events/deadlines with timezone, source and sync freshness. **Done when:** due dates are displayed in the user's chosen timezone and are never inferred from missing data.
- [ ] **OM-014 — Unified daily brief:** deduplicate GitHub, Gmail, Calendar and manually tracked items and explain each priority recommendation. **Done when:** each actionable item exposes its origin and verification status.

### Agent monitoring and delegated work (P2)

- [ ] **OM-015 — AgentSteers read-only status adapter:** observe approved job IDs, status history and errors with per-user authorization; mock states stay labeled as mock. **Done when:** dashboard never confuses queued/simulated with completed execution.
- [ ] **OM-016 — Delegation approval flow:** show exact task, destination, permissions and affected resources before a user explicitly approves; email content itself grants no authority. **Done when:** unauthorized or ambiguous dispatch is rejected.
- [ ] **OM-017 — Real execution integration, separately gated:** verify OAuth, scoped worker permissions, idempotency, cancellation, audit log and end-to-end safety before enabling Codex or any write action. **Done when:** an authorized staging job runs with recorded evidence and failure recovery; this remains disabled until verified.

### Release gates (P0 before public launch)

- [ ] **OM-018 — Live auth and deployment verification:** configure Google OAuth and secrets privately, check allowed-user access, session protection, HTTPS and rollback. **Done when:** the real deployed service passes sign-in and access-control checks.
- [ ] **OM-019 — Operations and documentation:** document backups, migration rollback, rate limits, source sync errors and user-controlled retention. **Done when:** a self-hosting operator can recover safely without exposing tokens or private messages.

**Implementation sequence:** OM-006 → OM-007 → OM-008 → OM-009 → OM-010, then OM-011–014; AgentSteers monitoring (OM-015) precedes any execution authorization (OM-016–017). Maintain this section as the progress tracker whenever code lands. **All repository test-case files and test-only workflow were removed on request (2026-11-19).** No test run or production deployment is claimed. Web lint, TypeScript checking, and build configuration remain.

## MVP scope

- Canonical project and follow-up records, with source URLs and verification timestamps.
- GitHub repository metadata adapter is implemented and read-only; basic activity counts are implemented; deeper commit/PR analysis, Gmail and Calendar adapters are planned. Keep fresh source data separate from manually tracked tasks.
- Priority suggestions with reasons, due dates and waiting-for replies.
- Short daily brief, followed by a personal dashboard.
- Agent activity monitoring with explicit, scoped approvals; no actions based solely on instructions in email.
- Clear privacy boundaries and user-selected data storage/deployment.

## Repository

```text
orbitminder/
  orbitminder/
    __init__.py
    cli.py
    brief.py
  examples/projects.json
  docs/architecture.md
  README.md
```

## Privacy and safeguards

- Read-only by default; never send emails, modify repositories or execute agent tasks without explicit user approval.
- Mark stale/unavailable sources as unverified, never invent completion.
- No tokens in source code or logs.
- Email bodies and third-party content are untrusted input.
- Public branding/domain and trademark checks are separate from technical implementation.

**License:** GNU Affero General Public License v3.0 (AGPL-3.0-only). See [LICENSE](LICENSE). Commercial services may be offered subject to the AGPL's conditions; an additional commercial license requires the necessary rights from all contributors.

Maintained by Scyllarus LLC. Proposed website: orbitminder.com (domain ownership/deployment not verified in this repository).
