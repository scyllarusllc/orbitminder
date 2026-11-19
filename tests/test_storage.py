import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

from orbitminder.storage import ProjectStore


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "projects.sqlite3"
        self.store = ProjectStore(self.path)
        self.store.initialize()

    def test_migration_applied_and_private_permissions(self):
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT version FROM schema_migrations").fetchone()[0], 1)
            self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])
        if os.name != "nt":
            self.assertEqual(self.path.stat().st_mode & 0o077, 0)
        self.store.initialize()

    def test_persists_projects_and_isolates_owners(self):
        pid = self.store.upsert_project("owner-a", "OrbitMinder")
        another = ProjectStore(self.path)
        self.assertEqual(another.list_projects("owner-a")[0]["id"], pid)
        self.assertEqual(another.list_projects("owner-b"), [])
        with self.assertRaises(PermissionError):
            another.upsert_project("owner-b", "stolen", project_id=pid)

    def test_sources_deduplicate_within_account_not_across_owners(self):
        a = self.store.upsert_source("owner-a", provider="github", account_key="one",
                                     external_id="org/repo", title="first")
        again = self.store.upsert_source("owner-a", provider="github", account_key="one",
                                         external_id="org/repo", title="latest")
        other_account = self.store.upsert_source("owner-a", provider="github", account_key="two",
                                                external_id="org/repo")
        other_owner = self.store.upsert_source("owner-b", provider="github", account_key="one",
                                              external_id="org/repo")
        self.assertEqual(a, again)
        self.assertNotEqual(a, other_account)
        self.assertNotEqual(a, other_owner)
        self.assertEqual(len(self.store.list_sources("owner-a")), 2)
        self.assertEqual(len(self.store.list_sources("owner-b")), 1)

    def test_cross_owner_project_relation_rejected(self):
        pid = self.store.upsert_project("owner-a", "private")
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.upsert_source("owner-b", provider="github", external_id="one",
                                     project_id=pid)

    def test_failure_record_does_not_erase_verified_source(self):
        self.store.upsert_source("owner-a", provider="github", external_id="a",
                                 verification_state="verified")
        self.store.record_sync("owner-a", provider="github", state="failed",
                               last_error="Network unavailable")
        item = self.store.list_sources("owner-a")[0]
        self.assertEqual(item["verification_state"], "verified")
        self.assertIsNotNone(item["last_success_at"])

    def test_invalid_owner_and_relative_path_fail(self):
        with self.assertRaises(ValueError):
            self.store.list_projects("")
        with self.assertRaises(ValueError):
            ProjectStore(Path("relative.sqlite3"))


if __name__ == "__main__":
    unittest.main()
