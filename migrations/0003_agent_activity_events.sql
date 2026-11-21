-- Append-only, owner-scoped state observations for already-known AgentSteers jobs.
-- No event is inferred from an Inboxtend task's job reference alone.
CREATE TABLE IF NOT EXISTS agent_activity_events (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL CHECK(length(trim(owner_id)) > 0),
    provider TEXT NOT NULL CHECK(provider='agentsteers'),
    external_job_id TEXT NOT NULL,
    event_key TEXT NOT NULL,
    state TEXT NOT NULL CHECK(length(trim(state)) > 0),
    mode TEXT NOT NULL CHECK(mode IN ('mock','real')),
    observed_at TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    FOREIGN KEY(owner_id,provider,external_job_id)
      REFERENCES agent_activities(owner_id,provider,external_job_id)
      ON DELETE RESTRICT,
    UNIQUE(owner_id,provider,external_job_id,event_key)
);
CREATE INDEX IF NOT EXISTS idx_agent_events_owner_job
    ON agent_activity_events(owner_id,provider,external_job_id,observed_at,id);
INSERT OR IGNORE INTO schema_migrations(version) VALUES (3);
