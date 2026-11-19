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


    def test_sync_freshness_reports_failed_and_partial_without_zeroing_cache(self):
        self.store.upsert_source("owner-a", provider="github", account_key="main",
                                 external_id="org/repo", verification_state="verified")
        before = self.store.list_source_freshness("owner-a", provider="github", account_key="main")
        self.assertEqual(before["sync_state"], "unchecked")
        self.assertEqual(before["records"][0]["verification_state"], "unchecked")
        self.assertIsNone(before["checked_count"])
        self.store.record_sync("owner-a", provider="github", account_key="main",
                               state="succeeded", checked_count=1)
        good = self.store.list_source_freshness("owner-a", provider="github", account_key="main")
        self.assertTrue(good["is_fully_verified"])
        self.assertEqual(good["records"][0]["verification_state"], "verified")

        self.store.record_sync("owner-a", provider="github", account_key="main",
                               state="failed", last_error="request_failed")
        failed = self.store.list_source_freshness("owner-a", provider="github", account_key="main")
        self.assertEqual(failed["sync_state"], "failed")
        self.assertFalse(failed["is_fully_verified"])
        self.assertEqual(failed["records"][0]["verification_state"], "stale")
        self.assertEqual(failed["cached_record_count"], 1)
        self.assertEqual(failed["checked_count"], 0)
        self.assertIsNotNone(failed["records"][0]["last_success_at"])

        self.store.record_sync("owner-a", provider="github", account_key="main",
                               state="partial", checked_count=1)
        partial = self.store.list_source_freshness("owner-a", provider="github", account_key="main")
        self.assertEqual(partial["sync_state"], "partial")
        self.assertEqual(partial["records"][0]["verification_state"], "stale")
        self.assertFalse(partial["is_fully_verified"])

    def test_latest_sync_isolated_by_owner_and_account(self):
        self.store.record_sync("owner-a", provider="gmail", account_key="one", state="failed")
        self.assertIsNone(self.store.latest_sync("owner-b", provider="gmail", account_key="one"))
        self.assertIsNone(self.store.latest_sync("owner-a", provider="gmail", account_key="two"))
        self.assertEqual(self.store.latest_sync("owner-a", provider="gmail",
                                                account_key="one")["state"], "failed")

    def test_unverified_upsert_retains_last_success(self):
        args = dict(provider="github", external_id="org/repo")
        self.store.upsert_source("owner-a", **args, verification_state="verified")
        initial = self.store.list_sources("owner-a")[0]["last_success_at"]
        self.store.upsert_source("owner-a", **args, verification_state="stale")
        item = self.store.list_sources("owner-a")[0]
        self.assertEqual(item["last_success_at"], initial)
        self.assertEqual(item["verification_state"], "stale")


if __name__ == "__main__":
    unittest.main()
