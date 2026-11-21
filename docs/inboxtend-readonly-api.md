# Inboxtend → OrbitMinder: read-only task API contract (draft)

**Recorded:** 2026-11-21. **Status:** proposed integration specification; **not implemented**, deployed, or verified. Inboxtend is an existing daily-use product and must keep working when OrbitMinder is unavailable. This document specifies minimal data sharing, not new Gmail synchronization or Agent execution.

## Scope and ownership

- **Inboxtend is the source of truth** for mailbox connections, messages, attachments, native tasks, and their task status. Its existing Agent execution path remains unchanged.
- **OrbitMinder reads** task summaries and source freshness, optionally assigning separate cross-project labels/priorities without overwriting the originating task.
- **AgentSteers owns its own job lifecycle** only for work explicitly delegated to it. An Inboxtend task already running through its own Agent must **never be submitted a second time**.
- No email bodies, raw headers, attachment payloads, OAuth tokens, prompts containing secrets, or mailbox credentials in this API.

## Proposed endpoints (versioned; read-only)

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/integration/v1/tasks?limit=50&cursor=...` | Paginated task summary snapshot or incremental changes |
| `GET` | `/integration/v1/tasks/{id}` | Current summary and revision for one authorized task |

Optional filters: `updated_since` (UTC RFC3339) for initial sync or compatibility; **prefer an opaque server-issued cursor** for stable pagination across concurrent updates. The exact route prefix can be adapted to Inboxtend's existing router.

**Security:** authenticate the caller server-to-server over TLS with a narrowly scoped read-only credential and resolve the permitted owner/account set **on the server**. Never trust a client-supplied `owner_id` or task ID to authorize access; filter every query by the authorized owner. Support token rotation, audit access, rate limits, bounded limits (1–100), and uniform 404 for non-owned task IDs. The credential must remain server-side, not in browser JS or Git. `Cache-Control: private, no-store` for responses.

## Task summary fields

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `id` | string | yes | Stable Inboxtend task identifier, scoped to its source installation/owner |
| `title` | string | yes | Short user-visible task title, length bounded; potentially sensitive |
| `project` | string/null | no | Native project label (not OrbitMinder's independent project mapping) |
| `status` | enum | yes | Native task status: `new`, `in_progress`, `waiting`, `done` |
| `priority` | enum | yes | `low`, `medium`, `high` |
| `due_at` | RFC3339 datetime/null | no | Exact instant when available; do not invent a deadline |
| `due_timezone` | IANA timezone/null | no | Original timezone for calendar presentation |
| `source_url` | string/null | no | Deep link to an access-controlled Inboxtend view; avoid exposing raw Gmail IDs in public links |
| `review_state` | string | yes | Whether the originating task has been reviewed; mirror Inboxtend vocabulary |
| `assigned_agent` | string/null | no | Native Agent label, not proof that execution happened |
| `executor` | enum/null | no | `inboxtend`, `agentsteers`, or `null` when unassigned/unknown; never infer |
| `agent_job_id` | string/null | no | External job reference, if there is one |
| `agent_status` | string/null | no | Raw executor state; keep mock and real states distinct |
| `updated_at` | UTC RFC3339 datetime | yes | Authoritative source update timestamp |
| `revision` | integer | yes | Monotonically increasing native task version |

The existing Inboxtend SQLite schema uses integer task IDs and `project_label`, `assigned_agent`, `agent_status`, `agentsteers_job_id`, `due_date`, `due_time`, `due_timezone`, and `revision`. The API may map those names to the normalized fields; **do not** assume `agentsteers_job_id` represents an executing or completed real job. Explicitly define the mapping for local Agent runs before implementation. If only a date is known, expose a separate `due_date` and set `due_at=null` rather than manufacturing a time.

## Example JSON (illustrative, NOT real user data)

```json
{
  "source": "inboxtend",
  "schema_version": 1,
  "snapshot_at": "2026-11-21T08:00:00Z",
  "items": [
    {
      "id": "42",
      "title": "Review a draft response",
      "project": "Research",
      "status": "waiting",
      "priority": "medium",
      "due_at": null,
      "due_date": null,
      "due_timezone": "Pacific/Saipan",
      "source_url": null,
      "review_state": "reviewed",
      "assigned_agent": null,
      "executor": null,
      "agent_job_id": null,
      "agent_status": null,
      "updated_at": "2026-11-21T07:30:00Z",
      "revision": 3
    }
  ],
  "next_cursor": null,
  "has_more": false
}
```

The example timestamp, ID and task are fictional. `next_cursor` must represent a stable, authorized continuation. For incremental sync, include a tombstone/deleted record feed or clear documented deletion semantics; otherwise OrbitMinder cannot safely remove stale tasks. Use a deterministic tie-breaker such as `(updated_at, id)` if not using a snapshot cursor, and ensure concurrent writes cannot silently skip rows.

## OrbitMinder ingestion behavior

1. Obtain credentials from private server configuration; check the response schema and owner scope; never expose the token to the client.
2. Upsert by `(source_instance, owner, task_id)`, preserving the last applied `revision` and source timestamp; repeated pages must be idempotent.
3. Store only necessary summary fields, source link, import/snapshot timestamps, and `sync_state`. Do not overwrite OrbitMinder-local project categorization.
4. On `401/403`, timeout, partial pagination or malformed response, surface `unauthorized`/`stale`/`partial`/`failed` correctly and retain prior cached data. **Never convert missing records into `done`**.
5. Deep links still require Inboxtend's own login and authorization. No task dispatch, editing, sending, or deleting via these endpoints.

## Non-duplication and future approved actions

This interface is **GET-only**. A future write/delegation API, if ever added, requires a separate permission scope, explicit user approval bound to task revision, target executor, action and affected resources, an `idempotency_key`, per-owner authorization, and recorded result. If Inboxtend already owns an in-flight Agent job, OrbitMinder only observes it and never re-dispatches it to AgentSteers. Unknown outcomes must be reconciled rather than automatically retried.

## Implementation checklist (not yet completed)

- [ ] Review Inboxtend's existing route/auth/task query patterns; add a backward-compatible read-only endpoint without changing existing production flows.
- [ ] Define precise task mapping and owner/user identity translation; minimize sensitive data.
- [ ] Implement server-side authorization, pagination, deletions/tombstones, validation and rate limiting.
- [ ] Implement OrbitMinder read-only ingestion with provenance and freshness indicators.
- [ ] Manually verify access isolation, pagination under concurrent writes, revoked credentials, failures and staleness before enabling live sync.
- [ ] Keep agent dispatch and Gmail-specific OAuth out of this first milestone.

See [three-product architecture](architecture.md). No existing Inboxtend application code or database is changed by this document.
