-- OrbitMinder local persistence schema v1 (OM-006).
-- Apply with SQLite 3.37+ using an operator-controlled database and transaction.
-- No OAuth tokens, raw email bodies, attachment bytes, or third-party instructions.
CREATE TABLE IF NOT EXISTS schema_migrations (
  version INTEGER PRIMARY KEY,
  applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL CHECK (length(trim(owner_id)) > 0),
  name TEXT NOT NULL CHECK (length(trim(name)) > 0),
  status TEXT NOT NULL DEFAULT 'unknown' CHECK (status IN ('unknown','active','waiting','blocked','done','archived')),
  priority INTEGER NOT NULL DEFAULT 0,
  next_action TEXT,
  follow_up_at TEXT,
  blocker TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE (owner_id,id)
);
CREATE INDEX IF NOT EXISTS idx_projects_owner_status ON projects(owner_id,status);

CREATE TABLE IF NOT EXISTS source_records (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL CHECK (length(trim(owner_id)) > 0),
  project_id TEXT,
  provider TEXT NOT NULL CHECK (length(trim(provider)) > 0),
  account_key TEXT NOT NULL DEFAULT '',
  external_id TEXT NOT NULL CHECK (length(trim(external_id)) > 0),
  source_url TEXT,
  title TEXT,
  observed_at TEXT,
  verification_state TEXT NOT NULL DEFAULT 'unchecked'
    CHECK (verification_state IN ('unchecked','verified','stale','error')),
  last_error TEXT,
  last_success_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(owner_id,project_id) REFERENCES projects(owner_id,id) ON DELETE RESTRICT,
  UNIQUE(owner_id,id),
  UNIQUE(owner_id,provider,account_key,external_id)
);
CREATE INDEX IF NOT EXISTS idx_sources_owner_project ON source_records(owner_id,project_id);
CREATE INDEX IF NOT EXISTS idx_sources_owner_freshness ON source_records(owner_id,verification_state,observed_at);

CREATE TABLE IF NOT EXISTS sync_runs (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL CHECK (length(trim(owner_id)) > 0),
  provider TEXT NOT NULL,
  account_key TEXT NOT NULL DEFAULT '',
  started_at TEXT NOT NULL,
  finished_at TEXT,
  state TEXT NOT NULL DEFAULT 'running'
    CHECK (state IN ('running','succeeded','partial','failed')),
  checked_count INTEGER NOT NULL DEFAULT 0 CHECK (checked_count >= 0),
  last_error TEXT
);
CREATE INDEX IF NOT EXISTS idx_sync_owner_provider ON sync_runs(owner_id,provider,account_key,started_at);

CREATE TABLE IF NOT EXISTS follow_ups (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL CHECK (length(trim(owner_id)) > 0),
  project_id TEXT NOT NULL,
  source_record_id TEXT,
  title TEXT NOT NULL,
  details TEXT,
  due_at TEXT,
  status TEXT NOT NULL DEFAULT 'proposed'
    CHECK(status IN ('proposed','reviewed','waiting','done','cancelled')),
  approved_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(owner_id,project_id) REFERENCES projects(owner_id,id) ON DELETE CASCADE,
  FOREIGN KEY(owner_id,source_record_id) REFERENCES source_records(owner_id,id) ON DELETE RESTRICT,
  UNIQUE(owner_id,id)
);
CREATE INDEX IF NOT EXISTS idx_followups_owner_due ON follow_ups(owner_id,status,due_at);

CREATE TABLE IF NOT EXISTS agent_activities (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL CHECK (length(trim(owner_id)) > 0),
  project_id TEXT,
  follow_up_id TEXT,
  provider TEXT NOT NULL,
  external_job_id TEXT NOT NULL,
  mode TEXT NOT NULL CHECK(mode IN ('mock','real')),
  state TEXT NOT NULL,
  approval_reference TEXT,
  source_url TEXT,
  observed_at TEXT,
  last_error TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(owner_id,project_id) REFERENCES projects(owner_id,id) ON DELETE RESTRICT,
  FOREIGN KEY(owner_id,follow_up_id) REFERENCES follow_ups(owner_id,id) ON DELETE RESTRICT,
  UNIQUE(owner_id,provider,external_job_id)
);
CREATE INDEX IF NOT EXISTS idx_agent_owner_state ON agent_activities(owner_id,state,observed_at);

INSERT OR IGNORE INTO schema_migrations(version) VALUES (1);
