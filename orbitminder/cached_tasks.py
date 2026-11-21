"""Read cached Inboxtend task summaries without contacting the provider.

Invoked only by the authenticated Next.js server. The owner identifier must be
derived from its session, never client input.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .storage import ProjectStore


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
        "note": "Saved snapshot, not a live task check.",
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
