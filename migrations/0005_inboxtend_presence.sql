-- Inboxtend task presence is derived only from a complete source snapshot.
-- Legacy cached rows have unknown presence until a complete sync is recorded.
ALTER TABLE inboxtend_tasks ADD COLUMN presence_state TEXT NOT NULL DEFAULT 'unverified'
  CHECK(presence_state IN ('unverified','present','not_returned'));
ALTER TABLE inboxtend_tasks ADD COLUMN last_seen_snapshot TEXT;
CREATE INDEX IF NOT EXISTS idx_inboxtend_tasks_presence
  ON inboxtend_tasks(owner_id,account_key,presence_state);
INSERT OR IGNORE INTO schema_migrations(version) VALUES (5);
