"""Read cached Inboxtend task summaries without contacting the provider.

Invoked only by the authenticated Next.js server. The owner identifier must be
derived from its session, never client input.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from .storage import ProjectStore

def freshness(run):
    """Conservative UI-only freshness assessment, never proof of live accuracy."""
    if not run:
        return {"state": "never_synced", "age_hours": None}
    if run["state"] != "succeeded":
        return {"state": "sync_failed_or_incomplete", "age_hours": None}
    try:
        checked = datetime.fromisoformat(run["finished_at"].replace("Z", "+00:00"))
        if checked.tzinfo is None:
            raise ValueError("timezone required")
        age = datetime.now(timezone.utc) - checked.astimezone(timezone.utc)
        if age < timedelta(0):
            return {"state": "invalid_timestamp", "age_hours": None}
        hours = round(age.total_seconds() / 3600, 1)
        return {"state": "aged_over_24h" if age > timedelta(hours=24) else "recent_cache",
                "age_hours": hours}
    except (ValueError, TypeError, OverflowError, AttributeError):
        return {"state": "invalid_timestamp", "age_hours": None}


def main():
    parser = argparse.ArgumentParser(description="Read owner-scoped cached Inboxtend tasks")
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--account", required=True)
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    if not args.db.is_absolute() or not args.db.is_file() or not 1 <= args.limit <= 200:
        parser.error("An initialized private database and a valid limit are required")
    try:
        store = ProjectStore(args.db)
        records = store.list_inboxtend_tasks(args.owner, args.account, limit=args.limit)
        run = store.latest_sync(args.owner, provider="inboxtend", account_key=args.account)
        activities = store.list_inboxtend_agent_activity(args.owner, args.account, limit=200)
        events = store.list_inboxtend_agent_events(args.owner, args.account, limit=200)
    except Exception:
        print("Cached task snapshot unavailable", file=sys.stderr)
        return 1
    print(json.dumps({
        "mode": "cached_inboxtend_tasks",
        "items": records,
        "agent_activities": activities,
        "agent_events": events,
        "sync_state": run["state"] if run else "unchecked",
        "last_checked_at": run["finished_at"] if run else None,
        "checked_count": run["checked_count"] if run else None,
        "last_error": run["last_error"] if run else None,
        "count": len(records),
        "freshness": freshness(run),
        "note": "Saved snapshot, not a live task check.",
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
