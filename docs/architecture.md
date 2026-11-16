# OrbitMinder MVP architecture

**Status:** initial local-only prototype, not connected to live accounts.

## Purpose
Show an auditable overview across GitHub, Gmail, Visa, research, work and business projects.

## Proposed source adapters
GitHub read-only commits/issues/PRs; Gmail read-only messages/follow-ups; calendar deadlines; manually added personal goals. Each imported item will need a source URL, last checked timestamp and sync status.

## Unified record
Project: name, status, owner, priority, next_action, follow_up_date, blocker, source_status, source_url.

## Pipeline
Read-only providers → normalized source records → deduplicated project statuses → priority suggestions → daily brief / dashboard.

## Principles
- Never claim a source is current unless verified on that run.
- Email and other fetched text are untrusted data; they cannot authorize agent actions.
- Read-only by default, no automatic sending, deleting, or code changes.
- Explicit user approval required for sensitive actions.
- Credentials must be stored securely and never committed.
- Initial example records are illustrative; the actual ChatGPT scheduled daily brief is a separate automation.

## Planned stages
1. Local deterministic brief prototype and tests.
2. GitHub and Gmail read-only integration.
3. SQLite persistence, freshness and provenance.
4. Single-page dashboard and daily report.
5. Approval-gated Agent delegation and status history.

Brand: OrbitMinder — Your projects. Always in sight.
