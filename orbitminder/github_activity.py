"""Read-only GitHub activity summary with bounded requests and explicit evidence.

No GitHub writes, no commands taken from repository content, no token logging.
"""
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from .github_sync import GitHubSyncError, _request, fetch_repositories


def _read(url, token, opener):
    return _request(url, token, opener)


def enrich_activity(repositories, *, token=None, days=7, max_repos=10,
                    opener=None, now=None):
    """Fetch recent commits and currently open PRs/issues for a bounded subset.

    Summaries do not infer issue urgency or completion from titles. An API failure
    aborts the entire report rather than presenting incomplete data as verified.
    """
    from urllib.request import urlopen
    opener = opener or urlopen
    if not 1 <= days <= 90:
        raise ValueError("days must be between 1 and 90")
    if not 1 <= max_repos <= 25:
        raise ValueError("max_repos must be between 1 and 25")
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must have a timezone")
    cutoff = (now.astimezone(timezone.utc) - timedelta(days=days)).isoformat().replace("+00:00", "Z")
    result = [dict(r) for r in repositories]
    selected = [r for r in result if r.get("status") != "done"][:max_repos]
    for record in selected:
        owner_repo = record.get("source_url", "").removeprefix("https://github.com/")
        parts = owner_repo.split("/")
        if len(parts) != 2 or not all(parts):
            raise GitHubSyncError("Invalid repository source URL")
        owner, name = parts
        base = "https://api.github.com/repos/" + quote(owner, safe="") + "/" + quote(name, safe="")
        commits = _read(base + "/commits?per_page=100&since=" + quote(cutoff, safe=""), token, opener)
        prs = _read(base + "/pulls?state=open&per_page=100", token, opener)
        issues = _read(base + "/issues?state=open&per_page=100", token, opener)
        if not all(isinstance(item, dict) for data in (commits, prs, issues) for item in data):
            raise GitHubSyncError("Unexpected GitHub activity item")
        open_issues = [i for i in issues if "pull_request" not in i]
        record["activity"] = {
            "commits_last_n_days": len(commits),
            "open_pull_requests": len(prs),
            "open_issues": len(open_issues),
            "window_days": days,
            "partial_counts": any(len(data) == 100 for data in (commits, prs, issues)),
            "checked_at": now.isoformat(),
        }
        # A list with 100 entries may have more pages: count is only a lower bound.
        if open_issues:
            record["next_action"] = "Review open GitHub issues"
        elif prs:
            record["next_action"] = "Review open pull requests"
        elif commits:
            record["next_action"] = "Review recent commits"
        else:
            record["next_action"] = "No recent commits or open PRs/issues in the checked API pages"
        record["priority"] = (20 if open_issues else 10 if prs else 5 if commits else 1)
    return result


def fetch_activity_from_environment(owner, *, limit=30, days=7, max_repos=10):
    token = os.environ.get("GITHUB_TOKEN")
    repositories = fetch_repositories(owner, token=token, limit=limit)
    return enrich_activity(repositories, token=token, days=days, max_repos=max_repos)
