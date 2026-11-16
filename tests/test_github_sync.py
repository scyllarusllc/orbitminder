import io
import json
import unittest
from urllib.error import HTTPError
from orbitminder.github_sync import GitHubSyncError, fetch_repositories


class _Reply:
    def __init__(self, data):
        self.data = json.dumps(data).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size):
        return self.data[:size]


class GitHubSyncTests(unittest.TestCase):
    def test_public_repositories_are_marked_verified(self):
        seen = []
        def opener(request, timeout):
            seen.append(request.full_url)
            return _Reply([{
                "owner": {"login": "scyllarusllc"},
                "name": "orbitminder",
                "html_url": "https://github.com/scyllarusllc/orbitminder",
                "pushed_at": "2026-11-16T10:00:00Z",
                "private": False, "archived": False
            }])
        repos = fetch_repositories("scyllarusllc", opener=opener)
        self.assertEqual(repos[0]["name"], "orbitminder")
        self.assertEqual(repos[0]["source_status"], "verified")
        self.assertIn("/users/scyllarusllc/repos?", seen[0])

    def test_token_uses_authenticated_endpoint_and_owner_filter(self):
        seen = []
        def opener(request, timeout):
            seen.append(request)
            return _Reply([
                {"owner": {"login": "another"}, "name": "other", "html_url": "https://github.com/another/other"},
                {"owner": {"login": "scyllarusllc"}, "name": "private", "html_url": "https://github.com/scyllarusllc/private", "private": True}
            ])
        repos = fetch_repositories("scyllarusllc", token="test-token", opener=opener)
        self.assertEqual(len(repos), 1)
        self.assertTrue(repos[0]["private"])
        self.assertIn("/user/repos?", seen[0].full_url)
        self.assertEqual(seen[0].get_header("Authorization"), "Bearer test-token")

    def test_rejects_invalid_owner(self):
        with self.assertRaises(ValueError):
            fetch_repositories("../secrets")

    def test_network_failure_is_not_reported_as_empty(self):
        def opener(request, timeout):
            raise HTTPError(request.full_url, 403, "rate limit", {}, None)
        with self.assertRaises(GitHubSyncError):
            fetch_repositories("scyllarusllc", opener=opener)


if __name__ == "__main__":
    unittest.main()
