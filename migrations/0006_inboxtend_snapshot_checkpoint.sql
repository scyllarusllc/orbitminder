-- Last fully validated source snapshot, including successful empty snapshots.
CREATE TABLE IF NOT EXISTS inboxtend_snapshot_checkpoints (
  owner_id TEXT NOT NULL CHECK(length(trim(owner_id)) > 0),
  account_key TEXT NOT NULL CHECK(length(trim(account_key)) > 0),
  snapshot_at TEXT NOT NULL,
  recorded_at TEXT NOT NULL,
  PRIMARY KEY(owner_id,account_key)
);
INSERT OR IGNORE INTO inboxtend_snapshot_checkpoints(
  owner_id,account_key,snapshot_at,recorded_at
)
SELECT owner_id,account_key,MAX(last_seen_snapshot),strftime('%Y-%m-%dT%H:%M:%fZ','now')
FROM inboxtend_tasks WHERE last_seen_snapshot IS NOT NULL
GROUP BY owner_id,account_key;
INSERT OR IGNORE INTO schema_migrations(version) VALUES (6);
