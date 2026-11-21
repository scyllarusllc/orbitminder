-- Explicit provenance for each persisted AgentSteers observation.
-- Existing records predate provenance tracking; never label them verified.
ALTER TABLE agent_activity_events
  ADD COLUMN verification_method TEXT NOT NULL DEFAULT 'legacy_unknown'
  CHECK(verification_method IN ('legacy_unknown','operator_reviewed','shared_key_hmac'));
CREATE INDEX IF NOT EXISTS idx_agent_event_verification
  ON agent_activity_events(owner_id,verification_method,observed_at);
INSERT OR IGNORE INTO schema_migrations(version) VALUES (4);
