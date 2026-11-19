"""Read an owner-scoped saved project overview from local SQLite.

The authenticated web server supplies the owner ID; this script never accepts
credentials or performs synchronization. Existing records are historical.
"""
import argparse
import json
import sys
from pathlib import Path

from .storage import ProjectStore


def saved_overview(store, owner_id):
    projects = store.list_projects(owner_id)
    sources = store.list_sources(owner_id)
    source_by_project = {}
    for src in sources:
        if src["project_id"]:
            source_by_project.setdefault(src["project_id"], []).append(src)
    project_rows = []
    for project in projects:
        project_rows.append({
            "id": project["id"], "name": project["name"], "status": project["status"],
            "next_action": project["next_action"], "follow_up_at": project["follow_up_at"],
            "blocker": project["blocker"], "updated_at": project["updated_at"],
            "sources": [
                {"provider": src["provider"], "source_url": src["source_url"],
                 "observed_at": src["observed_at"], "last_success_at": src["last_success_at"],
                 "stored_verification_state": src["verification_state"]}
                for src in source_by_project.get(project["id"], [])
            ],
        })
    # Provider sync state is separate from individual source status.
    scopes = sorted({(src["provider"], src["account_key"]) for src in sources})
    syncs = []
    for provider, account_key in scopes:
        snapshot = store.list_source_freshness(owner_id, provider=provider, account_key=account_key)
        syncs.append({
            "provider": provider, "account_key": account_key,
            "sync_state": snapshot["sync_state"],
            "last_checked_at": snapshot["last_checked_at"],
            "cached_record_count": snapshot["cached_record_count"],
            "is_fully_verified": snapshot["is_fully_verified"],
        })
    return {"mode": "saved_snapshot", "project_count": len(project_rows),
            "projects": project_rows, "sources_count": len(sources), "syncs": syncs,
            "note": "Stored snapshots are historical, not a live provider check."}


def main():
    parser = argparse.ArgumentParser(description="OrbitMinder owner-scoped saved overview")
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--owner", required=True)
    args = parser.parse_args()
    if not args.db.is_absolute() or not args.db.is_file():
        parser.error("A configured initialized SQLite database is required")
    try:
        result = saved_overview(ProjectStore(args.db), args.owner)
    except Exception:
        # Do not expose database path or source data on error.
        print("Saved overview unavailable", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
