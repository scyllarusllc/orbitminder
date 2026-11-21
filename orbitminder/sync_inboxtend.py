"""Operator-triggered Inboxtend task sync (never runs on import or at page load).

Uses one configured source account and server-side credentials only. Reads task
summaries, validates each page, and records sync state in OrbitMinder SQLite.
No email writes, Agent dispatch, browser secrets, or implicit scheduling.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from .inboxtend_contract import InboxtendTaskPage
from .inboxtend_import import import_task_summaries
from .storage import ProjectStore


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"Missing private configuration: {name}")
    return value


def _source_url() -> str:
    value = _required("INBOXTEND_READONLY_BASE_URL").rstrip("/")
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in ("", "/")):
        raise ValueError("Inboxtend base URL must be an HTTPS origin")
    return value


async def sync_from_environment(*, page_limit: int = 50, max_pages: int = 100):
    """Read source pages and import atomically for the configured owner/account."""
    if not 1 <= page_limit <= 100 or not 1 <= max_pages <= 1000:
        raise ValueError("Invalid pagination configuration")
    path = Path(_required("ORBITMINDER_DB_PATH"))
    if not path.is_absolute():
        raise ValueError("ORBITMINDER_DB_PATH must be an absolute path")
    if not path.parent.is_dir():
        raise ValueError("Database directory does not exist")
    owner_id = _required("ORBITMINDER_OWNER_ID")
    account_key = _required("INBOXTEND_ACCOUNT_KEY")
    base_url = _source_url()
    token = _required("INBOXTEND_READONLY_TOKEN")
    store = ProjectStore(path)
    store.initialize()

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=False,
                                 trust_env=False) as client:
        async def fetch_page(cursor: str | None) -> InboxtendTaskPage:
            params: dict[str, int | str] = {"limit": page_limit}
            if cursor:
                params["cursor"] = cursor
            response = await client.get(
                base_url + "/integration/v1/tasks", params=params,
                headers={"Authorization": f"Bearer {token}",
                         "Accept": "application/json"},
            )
            response.raise_for_status()
            return InboxtendTaskPage.model_validate(response.json())

        return await import_task_summaries(
            store=store, owner_id=owner_id, account_key=account_key,
            fetch_page=fetch_page, max_pages=max_pages,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Inboxtend read-only task snapshots")
    parser.add_argument("--page-limit", type=int, default=50)
    parser.add_argument("--max-pages", type=int, default=100)
    args = parser.parse_args()
    try:
        result = asyncio.run(sync_from_environment(
            page_limit=args.page_limit, max_pages=args.max_pages,
        ))
    except Exception:
        # Avoid leaking remote URL, secrets or task titles in diagnostic output.
        print("Inboxtend sync failed; inspect private server configuration and connectivity.",
              file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
