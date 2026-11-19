# OrbitMinder normalized data model (OM-006)

Status: **schema design and initial SQLite migration committed; not applied to a live database or verified by tests**. See [migration 0001](../migrations/0001_initial.sql).

## Ownership and source identity

All five record tables carry `owner_id`; read/write API paths **must** filter with authenticated server-derived owner identity, never a caller-supplied owner. Cross-owner links are backed by composite `(owner_id,id)` foreign keys. This schema is **not** a replacement for authorization checks, encrypted storage, or secret management.

- `projects`: canonical project, status, priority, next action, blocker, follow-up timestamp.
- `source_records`: source provenance by owner, provider, account key and external ID; URL, observation time, verification state, last success and sanitized error. Its unique key supports deterministic deduplication.
- `sync_runs`: provider-specific fetch attempts, timing, partial/failure state, count of checked items and sanitized error.
- `follow_ups`: user-reviewable actionable item with optional source evidence link and explicit review/approval timestamps.
- `agent_activities`: remote job identity, mock versus real mode, state, provenance and approval reference; **no executable payload**.

Times are RFC 3339 UTC strings (`2026-11-19T13:00:00Z`); store original calendar timezone separately in a later migration if provider timezone semantics need preservation. IDs are opaque and generated on the server. `account_key` is a non-secret stable account identifier, not an OAuth token. Keep source URLs optional when unavailable.

## Data and state rules

1. A failed fetch creates a `sync_runs` failure but does **not** erase prior verified records or turn missing counts into zero. Reconciliation marks outdated sources `stale`, keeping `last_success_at`.
2. A record is `verified` only when checked successfully by the indicated provider and time. `unchecked`, `stale`, and `error` are never treated as current. A partially completed run must report `partial`.
3. Deduplicate within owner, provider, account and external ID. Never deduplicate different mailbox accounts solely by email subject or GitHub repository display name.
4. Mail content, attachments and external task text are untrusted. They do not authorize sending, code execution or project mutation. Only authenticated approval can authorize delegation.
5. `agent_activities.mode=mock` remains explicitly simulated; `queued_mock` is not `done`. Never infer successful execution from a queue acknowledgement.

## Migration contract

For OM-007, use an explicit transaction around schema application, verify `PRAGMA foreign_key_check`, and record a schema version. Maintain incremental, forward-only migrations and a tested backup/rollback process. Apply database file permissions for the service owner; do not save OAuth credentials or correspondence in these tables. This initial schema does not connect the dashboard or automatically create an on-disk SQLite database.

## Open verification

- [ ] Apply migration on a disposable SQLite database and verify foreign keys and indexes.
- [ ] Verify duplicate provider IDs across owners/accounts, mismatched-owner relationships, and delete behavior.
- [ ] Implement server-only persistence repository with owner-scoped queries (OM-007).
- [ ] Verify partial/failed sync preserves previous observations (OM-008).
- [ ] Confirm operational retention, backups, and actual deployed authentication before public rollout.
