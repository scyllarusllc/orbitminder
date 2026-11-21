"""Owner-scoped, local SQLite persistence for OrbitMinder (OM-007).

No network calls, tokens, email content, or agent execution. The caller MUST
derive owner_id from an authenticated server session; never browser input.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import os
import sqlite3
from uuid import uuid4


MIGRATIONS = {
    1: Path(__file__).resolve().parent.parent / "migrations" / "0001_initial.sql",
    2: Path(__file__).resolve().parent.parent / "migrations" / "0002_inboxtend_tasks.sql",
    3: Path(__file__).resolve().parent.parent / "migrations" / "0003_agent_activity_events.sql",
}


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _owner(owner_id):
    if not isinstance(owner_id, str) or not owner_id.strip():
        raise ValueError("authenticated owner_id is required")
    return owner_id


class ProjectStore:
    """Synchronous service-side repository; never expose to unauthenticated routes."""

    def __init__(self, path):
        self.path = Path(path)
        if not self.path.is_absolute():
            raise ValueError("database path must be absolute")
        if not self.path.parent.is_dir():
            raise ValueError("database parent directory does not exist")

    def _connect(self):
        connection = sqlite3.connect(str(self.path), timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=10000")
        return connection

    def initialize(self):
        # Create private database atomically; never chmod an existing operator file.
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
        except FileExistsError:
            pass
        else:
            os.close(fd)
        with self._connect() as db:
            versions = db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
            ).fetchone()
            applied = ({row[0] for row in db.execute("SELECT version FROM schema_migrations")}
                       if versions else set())
            if any(version not in MIGRATIONS for version in applied):
                raise RuntimeError("database schema is newer than this application")
            for version, migration in MIGRATIONS.items():
                if version not in applied:
                    script = migration.read_text(encoding="utf-8")
                    db.executescript("BEGIN IMMEDIATE;\n" + script + "\nCOMMIT;")
            errors = db.execute("PRAGMA foreign_key_check").fetchall()
            if errors:
                raise RuntimeError("database foreign key verification failed")

    def upsert_project(self, owner_id, name, *, project_id=None, status="active",
                       priority=0, next_action=None, follow_up_at=None, blocker=None):
        owner_id = _owner(owner_id)
        if not isinstance(name, str) or not name.strip():
            raise ValueError("project name is required")
        project_id = project_id or uuid4().hex
        now = _now()
        with self._connect() as db:
            # Existing IDs cannot be reassigned across owners.
            previous = db.execute("SELECT owner_id FROM projects WHERE id=?", (project_id,)).fetchone()
            if previous and previous["owner_id"] != owner_id:
                raise PermissionError("project does not belong to owner")
            db.execute(
                """INSERT INTO projects
                   (id,owner_id,name,status,priority,next_action,follow_up_at,blocker,created_at,updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET
                     name=excluded.name,status=excluded.status,priority=excluded.priority,
                     next_action=excluded.next_action,follow_up_at=excluded.follow_up_at,
                     blocker=excluded.blocker,updated_at=excluded.updated_at
                   WHERE projects.owner_id=excluded.owner_id""",
                (project_id, owner_id, name.strip(), status, priority, next_action,
                 follow_up_at, blocker, now, now),
            )
        return project_id

    def list_projects(self, owner_id):
        owner_id = _owner(owner_id)
        with self._connect() as db:
            return [dict(row) for row in db.execute(
                "SELECT * FROM projects WHERE owner_id=? ORDER BY updated_at DESC,id",
                (owner_id,),
            )]

    def upsert_source(self, owner_id, *, provider, external_id, account_key="",
                      project_id=None, source_url=None, title=None,
                      observed_at=None, verification_state="verified"):
        owner_id = _owner(owner_id)
        if not all(isinstance(x, str) and x.strip() for x in (provider, external_id)):
            raise ValueError("provider and external_id are required")
        if not isinstance(account_key, str):
            raise ValueError("account_key must be a string")
        if verification_state not in ("unchecked", "verified", "stale", "error"):
            raise ValueError("invalid verification_state")
        now = _now()
        if verification_state == "verified" and not observed_at:
            observed_at = now
        with self._connect() as db:
            existing = db.execute(
                """SELECT id FROM source_records
                   WHERE owner_id=? AND provider=? AND account_key=? AND external_id=?""",
                (owner_id, provider, account_key, external_id),
            ).fetchone()
            source_id = existing["id"] if existing else uuid4().hex
            db.execute(
                """INSERT INTO source_records
                  (id,owner_id,project_id,provider,account_key,external_id,source_url,title,
                   observed_at,verification_state,last_error,last_success_at,created_at,updated_at)
                  VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                  ON CONFLICT(owner_id,provider,account_key,external_id) DO UPDATE SET
                    project_id=excluded.project_id,source_url=excluded.source_url,
                    title=excluded.title,observed_at=excluded.observed_at,
                    verification_state=excluded.verification_state,last_error=NULL,
                    last_success_at=CASE WHEN excluded.verification_state='verified'
                      THEN excluded.last_success_at
                      ELSE source_records.last_success_at END,
                    updated_at=excluded.updated_at""",
                (source_id, owner_id, project_id, provider, account_key, external_id,
                 source_url, title, observed_at, verification_state, None,
                 observed_at if verification_state == "verified" else None, now, now),
            )
            return source_id

    def list_sources(self, owner_id, *, provider=None):
        owner_id = _owner(owner_id)
        query = "SELECT * FROM source_records WHERE owner_id=?"
        args = [owner_id]
        if provider is not None:
            query += " AND provider=?"
            args.append(provider)
        query += " ORDER BY created_at DESC,id"
        with self._connect() as db:
            return [dict(row) for row in db.execute(query, args)]

    def record_sync(self, owner_id, *, provider, state, account_key="", checked_count=0,
                    last_error=None):
        owner_id = _owner(owner_id)
        if state not in ("succeeded", "partial", "failed"):
            raise ValueError("sync run requires a terminal state")
        if not isinstance(provider, str) or not provider.strip():
            raise ValueError("provider is required")
        if not isinstance(account_key, str):
            raise ValueError("account_key must be a string")
        if type(checked_count) is not int or checked_count < 0:
            raise ValueError("invalid checked_count")
        run_id, now = uuid4().hex, _now()
        with self._connect() as db:
            db.execute(
                """INSERT INTO sync_runs
                   (id,owner_id,provider,account_key,started_at,finished_at,state,checked_count,last_error)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (run_id, owner_id, provider, account_key, now, now, state,
                 checked_count, str(last_error)[:200] if last_error else None),
            )
        return run_id

    def latest_sync(self, owner_id, *, provider, account_key=""):
        """Last finished sync for a single owner/provider/account, or None."""
        owner_id = _owner(owner_id)
        with self._connect() as db:
            row = db.execute(
                """SELECT id,provider,account_key,started_at,finished_at,state,
                          checked_count,last_error
                   FROM sync_runs
                   WHERE owner_id=? AND provider=? AND account_key=?
                   ORDER BY rowid DESC LIMIT 1""",
                (owner_id, provider, account_key),
            ).fetchone()
            return dict(row) if row else None

    def list_source_freshness(self, owner_id, *, provider, account_key=""):
        """Read-only snapshot; failures cannot be disguised as zero activity.

        A successful provider run does not itself prove every cached record was
        checked. Distinguish stored source verification from provider sync state.
        """
        owner_id = _owner(owner_id)
        run = self.latest_sync(owner_id, provider=provider, account_key=account_key)
        with self._connect() as db:
            records = [dict(row) for row in db.execute(
                """SELECT id,project_id,provider,account_key,external_id,source_url,
                          title,observed_at,verification_state,last_error,last_success_at
                   FROM source_records
                   WHERE owner_id=? AND provider=? AND account_key=?
                   ORDER BY updated_at DESC,id""",
                (owner_id, provider, account_key),
            )]
        run_state = run["state"] if run else "unchecked"
        for record in records:
            record["stored_verification_state"] = record.pop("verification_state")
            if run_state in ("failed", "partial"):
                record["verification_state"] = "stale"
            elif run_state == "unchecked":
                record["verification_state"] = "unchecked"
            else:
                record["verification_state"] = record["stored_verification_state"]
        return {
            "provider": provider,
            "account_key": account_key,
            "sync_state": run_state,
            "last_checked_at": run["finished_at"] if run else None,
            "checked_count": run["checked_count"] if run else None,
            "last_error": run["last_error"] if run else None,
            "cached_record_count": len(records),
            "records": records,
            "is_fully_verified": run_state == "succeeded" and
                all(item["verification_state"] == "verified" for item in records),
        }

    def save_inboxtend_tasks(self, owner_id, account_key, tasks):
        """Atomically cache validated task snapshots; older revisions never win."""
        owner_id = _owner(owner_id)
        if not isinstance(account_key, str) or not account_key.strip():
            raise ValueError("account_key is required")
        now = _now()
        written = 0
        with self._connect() as db:
            for task in tasks:
                values = (
                    owner_id, account_key, task.id, task.title, task.project,
                    task.status, task.priority,
                    task.due_at.isoformat() if task.due_at else None,
                    task.due_date.isoformat() if task.due_date else None,
                    task.due_timezone, str(task.source_url) if task.source_url else None,
                    task.review_state, task.assigned_agent, task.executor,
                    task.agent_job_id, task.agent_status,
                    task.updated_at.isoformat(), task.revision, now,
                )
                result = db.execute(
                    """INSERT INTO inboxtend_tasks (
                        owner_id,account_key,external_id,title,project_label,
                        status,priority,due_at,due_date,due_timezone,source_url,
                        review_state,assigned_agent,executor,agent_job_id,
                        agent_status,source_updated_at,revision,observed_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(owner_id,account_key,external_id) DO UPDATE SET
                        title=excluded.title,project_label=excluded.project_label,
                        status=excluded.status,priority=excluded.priority,
                        due_at=excluded.due_at,due_date=excluded.due_date,
                        due_timezone=excluded.due_timezone,source_url=excluded.source_url,
                        review_state=excluded.review_state,
                        assigned_agent=excluded.assigned_agent,
                        executor=excluded.executor,agent_job_id=excluded.agent_job_id,
                        agent_status=excluded.agent_status,
                        source_updated_at=excluded.source_updated_at,
                        revision=excluded.revision,observed_at=excluded.observed_at
                    WHERE excluded.revision > inboxtend_tasks.revision
                      OR (excluded.revision = inboxtend_tasks.revision
                          AND excluded.source_updated_at >= inboxtend_tasks.source_updated_at)
                    """, values,
                )
                written += result.rowcount
        return written

    def list_inboxtend_tasks(self, owner_id, account_key, *, limit=100):
        """Owner/account-filtered cached summaries; never include message content."""
        owner_id = _owner(owner_id)
        if not isinstance(account_key, str) or not account_key.strip():
            raise ValueError("account_key is required")
        if type(limit) is not int or not 1 <= limit <= 500:
            raise ValueError("invalid limit")
        with self._connect() as db:
            return [dict(row) for row in db.execute(
                """SELECT external_id,title,project_label,status,priority,due_at,
                          due_date,due_timezone,source_url,review_state,assigned_agent,
                          executor,agent_job_id,agent_status,source_updated_at,
                          revision,observed_at
                   FROM inboxtend_tasks
                   WHERE owner_id=? AND account_key=?
                   ORDER BY source_updated_at DESC,external_id LIMIT ?""",
                (owner_id, account_key, limit),
            )]

    def list_inboxtend_agent_activity(self, owner_id, account_key, *, limit=100):
        """Match cached AgentSteers job IDs to stored activity within one owner.

        A task's reported job ID alone is not proof of execution. Only an
        independently stored agent_activities row is returned. No mailbox data,
        approval credentials, or private errors are returned to the web UI.
        """
        owner_id = _owner(owner_id)
        if not isinstance(account_key, str) or not account_key.strip():
            raise ValueError("account_key is required")
        if type(limit) is not int or not 1 <= limit <= 500:
            raise ValueError("invalid limit")
        with self._connect() as db:
            rows = db.execute(
                """SELECT t.external_id AS task_id, a.external_job_id AS job_id,
                          a.provider, a.mode, a.state, a.observed_at, a.updated_at
                   FROM inboxtend_tasks AS t
                   JOIN agent_activities AS a
                     ON a.owner_id=t.owner_id
                    AND a.provider='agentsteers'
                    AND a.external_job_id=t.agent_job_id
                   WHERE t.owner_id=? AND t.account_key=?
                     AND t.executor='agentsteers'
                     AND t.agent_job_id IS NOT NULL
                   ORDER BY a.updated_at DESC,t.external_id LIMIT ?""",
                (owner_id, account_key, limit),
            ).fetchall()
            return [dict(row) for row in rows]

    def append_agent_observation(self, owner_id, *, external_job_id, event_key,
                                 state, mode, observed_at):
        """Append an independently observed state for an existing AgentSteers job.

        A trusted importer must verify event_key and observed_at at the source.
        Never synthesize events from cached task labels or an unverified job ID.
        """
        owner_id = _owner(owner_id)
        for value in (external_job_id, event_key, state, observed_at):
            if not isinstance(value, str) or not value.strip():
                raise ValueError("validated observation fields are required")
        if mode not in ("mock", "real"):
            raise ValueError("invalid execution mode")
        timestamp = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        with self._connect() as db:
            found = db.execute(
                """SELECT 1 FROM agent_activities
                   WHERE owner_id=? AND provider='agentsteers' AND external_job_id=?""",
                (owner_id, external_job_id),
            ).fetchone()
            if not found:
                raise ValueError("matching stored AgentSteers job required")
            result = db.execute(
                """INSERT OR IGNORE INTO agent_activity_events
                   (id,owner_id,provider,external_job_id,event_key,state,
                    mode,observed_at,recorded_at)
                   VALUES (?,?,'agentsteers',?,?,?,?,?,?)""",
                (uuid4().hex, owner_id, external_job_id, event_key,
                 state, mode, timestamp.isoformat(), _now()),
            )
            return bool(result.rowcount)

    def list_inboxtend_agent_events(self, owner_id, account_key, *, limit=100):
        """Show only persisted, same-owner job observations linked to cached tasks."""
        owner_id = _owner(owner_id)
        if not isinstance(account_key, str) or not account_key.strip():
            raise ValueError("account_key is required")
        if type(limit) is not int or not 1 <= limit <= 500:
            raise ValueError("invalid limit")
        with self._connect() as db:
            return [dict(row) for row in db.execute(
                """SELECT e.id,t.external_id AS task_id,
                          e.external_job_id AS job_id,e.state,e.mode,
                          e.observed_at,e.recorded_at
                   FROM agent_activity_events AS e
                   JOIN inboxtend_tasks AS t
                     ON t.owner_id=e.owner_id
                    AND t.agent_job_id=e.external_job_id
                    AND t.executor='agentsteers'
                   WHERE e.owner_id=? AND t.account_key=?
                   ORDER BY e.observed_at DESC,e.id LIMIT ?""",
                (owner_id, account_key, limit),
            )]

    def import_agent_observations(self, owner_id, observations):
        """Atomically ingest operator-reviewed observations for existing jobs.

        Replays of identical source event keys are no-ops; divergent replays
        fail and roll back the batch. This does not authenticate the source:
        provenance must be checked before invoking this method.
        """
        owner_id = _owner(owner_id)
        if not isinstance(observations, list) or not 1 <= len(observations) <= 500:
            raise ValueError("expected 1 to 500 validated observations")
        prepared = []
        keys = set()
        for item in observations:
            if not isinstance(item, dict) or set(item) != {
                "external_job_id", "event_key", "state", "mode", "observed_at"
            }:
                raise ValueError("unexpected observation fields")
            job, key, state, mode, observed = (
                item["external_job_id"], item["event_key"], item["state"],
                item["mode"], item["observed_at"]
            )
            if any(not isinstance(v, str) or not v.strip() or len(v) > 200
                   for v in (job, key, state, observed)):
                raise ValueError("invalid observation value")
            if mode not in ("mock", "real"):
                raise ValueError("invalid observation mode")
            timestamp = datetime.fromisoformat(observed.replace("Z", "+00:00"))
            if timestamp.tzinfo is None:
                raise ValueError("observation timestamp requires a timezone")
            normalized = timestamp.astimezone(timezone.utc).isoformat()
            if (job, key) in keys:
                raise ValueError("duplicate event key in batch")
            keys.add((job, key))
            prepared.append((job, key, state, mode, normalized))

        inserted = 0
        with self._connect() as db:
            for job, key, state, mode, observed in prepared:
                parent = db.execute(
                    """SELECT mode FROM agent_activities
                       WHERE owner_id=? AND provider='agentsteers'
                         AND external_job_id=?""", (owner_id, job)
                ).fetchone()
                if not parent:
                    raise ValueError("observation requires an existing AgentSteers job")
                if parent["mode"] != mode:
                    raise ValueError("observation mode conflicts with stored job")
                existing = db.execute(
                    """SELECT state,mode,observed_at FROM agent_activity_events
                       WHERE owner_id=? AND provider='agentsteers'
                         AND external_job_id=? AND event_key=?""",
                    (owner_id, job, key),
                ).fetchone()
                if existing:
                    if (existing["state"], existing["mode"], existing["observed_at"]) != (
                        state, mode, observed
                    ):
                        raise ValueError("conflicting observation replay")
                    continue
                db.execute(
                    """INSERT INTO agent_activity_events (
                        id,owner_id,provider,external_job_id,event_key,
                        state,mode,observed_at,recorded_at
                    ) VALUES (?,?,'agentsteers',?,?,?,?,?,?)""",
                    (uuid4().hex, owner_id, job, key, state, mode, observed, _now()),
                )
                inserted += 1
        return {"accepted": len(prepared), "inserted": inserted}
