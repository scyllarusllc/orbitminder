"""Run local or live GitHub project briefs with read-only sources."""
import argparse
import json
from datetime import date
from pathlib import Path
from .brief import build_brief, format_brief
from .github_sync import GitHubSyncError, fetch_from_environment


def main():
    parser = argparse.ArgumentParser(description="OrbitMinder daily brief")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--data", type=Path, help="Local JSON array of projects")
    source.add_argument("--github-owner", help="GitHub account to read repositories from")
    parser.add_argument("--github-limit", type=int, default=100)
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()
    if args.github_owner:
        try:
            records = fetch_from_environment(args.github_owner, limit=args.github_limit)
        except (GitHubSyncError, ValueError) as exc:
            parser.error(str(exc))
    else:
        records = json.loads(args.data.read_text(encoding="utf-8"))
        if not isinstance(records, list):
            parser.error("Expected a JSON array of projects")
    print(format_brief(build_brief(records, date.fromisoformat(args.date))), end="")


if __name__ == "__main__":
    main()
