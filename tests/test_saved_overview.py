import os
from pathlib import Path
import tempfile
import unittest

from orbitminder.saved_overview import saved_overview
from orbitminder.storage import ProjectStore


class SavedOverviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = ProjectStore(Path(self.tmp.name) / "projects.db")
        self.store.initialize()

    def test_historical_snapshot_owner_isolation_and_source_links(self):
        a = self.store.upsert_project("google-sub-a", "OrbitMinder", next_action="Review backlog")
        self.store.upsert_project("google-sub-b", "Private")
        self.store.upsert_source("google-sub-a", provider="github", account_key="scyllarusllc",
                                 external_id="repo-1", project_id=a,
                                 source_url="https://github.com/scyllarusllc/orbitminder")
        result = saved_overview(self.store, "google-sub-a")
        self.assertEqual(result["mode"], "saved_snapshot")
        self.assertEqual(result["project_count"], 1)
        self.assertEqual(result["projects"][0]["next_action"], "Review backlog")
        self.assertEqual(len(result["projects"][0]["sources"]), 1)
        self.assertEqual(result["syncs"][0]["sync_state"], "unchecked")
        self.assertNotIn("Private", str(result))

    def test_failure_preserves_cache_without_verified_claim(self):
        a = self.store.upsert_project("owner", "One")
        self.store.upsert_source("owner", provider="github", external_id="repo", project_id=a)
        self.store.record_sync("owner", provider="github", state="failed")
        result = saved_overview(self.store, "owner")
        self.assertEqual(result["project_count"], 1)
        self.assertFalse(result["syncs"][0]["is_fully_verified"])
        self.assertEqual(result["syncs"][0]["sync_state"], "failed")

if __name__ == "__main__":
    unittest.main()
