"""Server-side Inboxtend task-summary import into the existing SQLite cache.

Explicitly invoked by a trusted service, not a public route or scheduler.
The source remains authoritative; cached summaries are not execution commands.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from .inboxtend_contract import InboxtendTaskPage
from .storage import ProjectStore

# The fetcher must use authenticated, owner-scoped HTTPS from trusted configuration.
# A page is validated before this function sees it.
PageFetcher = Callable[[str | None], Awaitable[InboxtendTaskPage]]


async def import_task_summaries(
    *, store: ProjectStore, owner_id: str, account_key: str, fetch_page: PageFetcher,
    max_pages: int = 100,
) -> dict[str, int | str]:
    """Fetch complete pagination first, then cache summaries.

    Any failed or incomplete fetch is marked failed and leaves existing cache intact.
    The store's source-record table stores only title, URL, and freshness for now;
    task status/priority/revision require a separately migrated task snapshot table.
    """
    if not isinstance(owner_id, str) or not owner_id.strip():
        raise ValueError("trusted authenticated owner_id is required")
    if not isinstance(account_key, str) or not account_key.strip():
        raise ValueError("trusted account_key is required")
    if not 1 <= max_pages <= 1000:
        raise ValueError("invalid max_pages")

    seen_ids: set[str] = set()
    seen_cursors: set[str] = set()
    items = []
    cursor = None
    snapshot_at = None
    try:
        for _ in range(max_pages):
            page = await fetch_page(cursor)
            if not isinstance(page, InboxtendTaskPage):
                raise ValueError("expected a validated InboxtendTaskPage")
            if snapshot_at is None:
                snapshot_at = page.snapshot_at
            elif page.snapshot_at != snapshot_at:
                raise ValueError("pagination crossed different snapshots")
            for task in page.items:
                if task.id in seen_ids:
                    raise ValueError("duplicate task across pages")
                seen_ids.add(task.id)
                items.append(task)
            if not page.has_more:
                break
            if page.next_cursor in seen_cursors:
                raise ValueError("repeated pagination cursor")
            seen_cursors.add(page.next_cursor)
            cursor = page.next_cursor
        else:
            raise ValueError("pagination limit reached")

    except Exception:
        # Never misrepresent a network/schema error as a successful empty sync.
        store.record_sync(owner_id, provider="inboxtend", account_key=account_key,
                          state="failed", checked_count=0,
                          last_error="Task feed unavailable or inconsistent")
        raise

    # The existing owner/account-scoped uniqueness constraint makes repeats
    # idempotent. No deletion is inferred from absence in a page or snapshot.
    # Store updates are per record; record partial if a write fails.
    written = 0
    try:
        for task in items:
            store.upsert_source(
                owner_id, provider="inboxtend", account_key=account_key,
                external_id=task.id, title=task.title,
                source_url=str(task.source_url) if task.source_url else None,
                observed_at=task.updated_at.isoformat(),
                verification_state="verified",
            )
            written += 1
    except Exception:
        store.record_sync(owner_id, provider="inboxtend", account_key=account_key,
                          state="partial", checked_count=written,
                          last_error="Task cache write interrupted")
        raise
    store.record_sync(owner_id, provider="inboxtend", account_key=account_key,
                      state="succeeded", checked_count=written)
    return {"state": "succeeded", "checked_count": written}
