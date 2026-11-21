-- Additive v2 Inboxtend task snapshots. Do not alter v1 source records.
CREATE TABLE IF NOT EXISTS inboxtend_tasks (
    owner_id TEXT NOT NULL,
    account_key TEXT NOT NULL,
    external_id TEXT NOT NULL,
    title TEXT NOT NULL,
    project_label TEXT,
    status TEXT NOT NULL CHECK(status IN ('new','in_progress','waiting','done')),
    priority TEXT NOT NULL CHECK(priority IN ('low','medium','high')),
    due_at TEXT,
    due_date TEXT,
    due_timezone TEXT,
    source_url TEXT,
    review_state TEXT NOT NULL,
    assigned_agent TEXT,
    executor TEXT CHECK(executor IN ('inboxtend','agentsteers') OR executor IS NULL),
    agent_job_id TEXT,
    agent_status TEXT,
    source_updated_at TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK(revision >= 0),
    observed_at TEXT NOT NULL,
    PRIMARY KEY(owner_id,account_key,external_id),
    CHECK(length(trim(owner_id)) > 0),
    CHECK(length(trim(account_key)) > 0)
);
CREATE INDEX IF NOT EXISTS idx_inboxtend_tasks_owner_status
    ON inboxtend_tasks(owner_id,account_key,status,source_updated_at);
INSERT OR IGNORE INTO schema_migrations(version) VALUES (2);
