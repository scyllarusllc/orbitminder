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


MIGRATION = Path(__file__).resolve().parent.parent / "migrations" / "0001_initial.sql"


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
            if versions:
                applied = {row[0] for row in db.execute("SELECT version FROM schema_migrations")}
                if any(version > 1 for version in applied):
                    raise RuntimeError("database schema is newer than this application")
                if 1 in applied:
                    return
            script = MIGRATION.read_text(encoding="utf-8")
            # executescript commits a preexisting transaction, so wrap the script itself.
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
                    last_success_at=excluded.last_success_at,updated_at=excluded.updated_at""",
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
        if not isinstance(checked_count, int) or checked_count < 0:
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
