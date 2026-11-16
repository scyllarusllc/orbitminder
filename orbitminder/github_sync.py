"""Read-only GitHub repository inventory for OrbitMinder.

Uses public GitHub API without credentials, or GITHUB_TOKEN for repositories
visible to the authenticated account. It never writes to GitHub.
"""
import json
import os
import re
from datetime import date, datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class GitHubSyncError(RuntimeError):
    """GitHub data is unavailable; no fabricated snapshot is returned."""


def _request(url, token, opener):
    headers = {"Accept": "application/vnd.github+json",
               "User-Agent": "OrbitMinder/0.1",
               "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = "Bearer " + token
    try:
        with opener(Request(url, headers=headers), timeout=15) as response:
            payload = response.read(2_000_001)
        if len(payload) > 2_000_000:
            raise GitHubSyncError("GitHub response exceeded size limit")
        result = json.loads(payload)
        if not isinstance(result, list):
            raise GitHubSyncError("GitHub returned an unexpected response")
        return result
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise GitHubSyncError("GitHub read failed; verify access, network and rate limits") from exc


def fetch_repositories(owner, token=None, limit=100, opener=urlopen):
    """Return repository records with source URLs and verified fetch timestamps.

    Authenticated calls use /user/repos to include accessible private repositories
    owned by the requested account; public calls use /users/{owner}/repos.
    """
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})", owner):
        raise ValueError("Invalid GitHub owner")
    if not 1 <= limit <= 1000:
        raise ValueError("limit must be between 1 and 1000")
    base = ("https://api.github.com/user/repos?affiliation=owner"
            if token else "https://api.github.com/users/" + quote(owner) + "/repos?")
    fetched_at = datetime.now(timezone.utc).isoformat()
    records = []
    for page in range(1, (limit + 99) // 100 + 1):
        separator = "&" if "?" in base and not base.endswith("?") else ""
        url = base + separator + f"per_page=100&page={page}&sort=pushed&direction=desc"
        batch = _request(url, token, opener)
        for item in batch:
            if not isinstance(item, dict):
                raise GitHubSyncError("Malformed GitHub repository entry")
            repo_owner = (item.get("owner") or {}).get("login", "")
            if repo_owner.casefold() != owner.casefold():
                continue
            name, html_url = item.get("name"), item.get("html_url")
            if not isinstance(name, str) or not isinstance(html_url, str):
                raise GitHubSyncError("Repository is missing a name or URL")
            records.append({
                "name": name,
                "status": "active" if not item.get("archived") else "done",
                "priority": 5 if not item.get("archived") else 0,
                "next_action": "Review repository changes and outstanding work" if not item.get("archived") else "",
                "source_status": "verified",
                "source_url": html_url,
                "source_checked_at": fetched_at,
                "last_pushed_at": item.get("pushed_at"),
                "private": bool(item.get("private")),
            })
            if len(records) >= limit:
                return records
        if len(batch) < 100:
            break
    return records


def fetch_from_environment(owner, limit=100):
    return fetch_repositories(owner, token=os.environ.get("GITHUB_TOKEN"), limit=limit)
