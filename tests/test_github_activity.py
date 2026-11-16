import json
import unittest
from datetime import datetime, timezone

from orbitminder.github_activity import enrich_activity
from orbitminder.github_sync import GitHubSyncError


class _Reply:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        return False

    def read(self, size):
        return self.payload[:size]


class ActivityTests(unittest.TestCase):
    def test_counts_issues_without_pr_duplicates(self):
        seen = []
        def opener(request, timeout):
            seen.append(request.full_url)
            if "/commits?" in request.full_url:
                return _Reply([{"sha": "abc"}])
            if "/pulls?" in request.full_url:
                return _Reply([{"number": 9}])
            return _Reply([{"number": 9, "pull_request": {}}, {"number": 10}])
        result = enrich_activity(
            [{"name": "demo", "status": "active",
              "source_url": "https://github.com/example/demo"}],
            opener=opener, now=datetime(2026, 11, 16, tzinfo=timezone.utc))
        activity = result[0]["activity"]
        self.assertEqual(activity["commits_last_n_days"], 1)
        self.assertEqual(activity["open_pull_requests"], 1)
        self.assertEqual(activity["open_issues"], 1)
        self.assertEqual(result[0]["next_action"], "Review open GitHub issues")
        self.assertEqual(len(seen), 3)
        self.assertIn("since=", seen[0])

    def test_bounded_repository_count_and_archived_skipped(self):
        calls = []
        def opener(request, timeout):
            calls.append(request.full_url)
            return _Reply([])
        repos = [{"name": str(i), "status": "active",
                  "source_url": "https://github.com/a/r" + str(i)}
                 for i in range(3)]
        repos.insert(0, {"name": "old", "status": "done",
                         "source_url": "https://github.com/a/old"})
        result = enrich_activity(repos, max_repos=1, opener=opener)
        self.assertEqual(len(calls), 3)
        self.assertNotIn("activity", result[0])
        self.assertNotIn("activity", result[-1])

    def test_failure_does_not_claim_success(self):
        def opener(request, timeout):
            raise TimeoutError("offline")
        with self.assertRaises(GitHubSyncError):
            enrich_activity([{"name": "demo",
                              "source_url": "https://github.com/a/demo"}],
                            opener=opener)

    def test_rejects_invalid_options(self):
        with self.assertRaises(ValueError):
            enrich_activity([], days=0)
        with self.assertRaises(ValueError):
            enrich_activity([], max_repos=100)

    def test_hundred_items_marks_lower_bound(self):
        def opener(request, timeout):
            if "/commits?" in request.full_url:
                return _Reply([{"sha": str(i)} for i in range(100)])
            return _Reply([])
        result = enrich_activity(
            [{"name": "x", "source_url": "https://github.com/a/x"}],
            opener=opener)
        self.assertTrue(result[0]["activity"]["partial_counts"])


if __name__ == "__main__":
    unittest.main()
