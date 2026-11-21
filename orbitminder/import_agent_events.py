"""Explicit operator-only import of reviewed AgentSteers observation records.

This command reads a *trusted, reviewed* local JSON file. It does not fetch
from AgentSteers or prove that records are authentic; the operator must
verify origin before invoking. No public web endpoint is exposed.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .storage import ProjectStore


def main() -> int:
    parser = argparse.ArgumentParser(description="Import reviewed AgentSteers observations")
    parser.add_argument("--file", required=True, type=Path,
                        help="Private JSON file with an observations array")
    args = parser.parse_args()
    owner = os.environ.get("ORBITMINDER_OWNER_ID", "").strip()
    db = Path(os.environ.get("ORBITMINDER_DB_PATH", ""))
    source = args.file
    if not owner or not db.is_absolute() or not db.is_file():
        print("Private owner/database configuration required", file=sys.stderr)
        return 1
    if not source.is_absolute() or not source.is_file():
        print("Absolute private observation file path required", file=sys.stderr)
        return 1
    try:
        if source.stat().st_size > 512_000:
            raise ValueError("observation input too large")
        payload = json.loads(source.read_text(encoding="utf-8"))
        if (not isinstance(payload, dict) or set(payload) != {"schema_version", "observations"}
                or type(payload["schema_version"]) is not int or payload["schema_version"] != 1):
            raise ValueError("invalid observation import schema")
        items = payload["observations"]
        if not isinstance(items, list):
            raise ValueError("observations must be an array")
        counts = ProjectStore(db).import_agent_observations(owner, items)
    except (OSError, UnicodeError, ValueError, TypeError, json.JSONDecodeError):
        print("Observation import rejected; no source data printed", file=sys.stderr)
        return 1
    print(json.dumps({"mode": "operator_reviewed_observations", **counts}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
