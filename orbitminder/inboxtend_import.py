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

    A failed or incomplete fetch leaves the previous task snapshot untouched.
    Validated task metadata is written atomically to the additive v2 table;
    source revisions prevent older pages overwriting newer cached versions.
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

    # Save all task summaries in one transaction. A write failure rolls back
    # the entire incoming snapshot and leaves cached data available.
    try:
        written = store.save_inboxtend_tasks(owner_id, account_key, items)
    except Exception:
        store.record_sync(owner_id, provider="inboxtend", account_key=account_key,
                          state="failed", checked_count=0,
                          last_error="Task snapshot write failed")
        raise
    # 'checked_count' counts the records received, including unchanged revisions.
    store.record_sync(owner_id, provider="inboxtend", account_key=account_key,
                      state="succeeded", checked_count=len(items))
    return {"state": "succeeded", "checked_count": len(items),
            "updated_count": written}
