"""Run: python3 -m orbitminder.cli --data examples/projects.json"""
import argparse
import json
from datetime import date
from pathlib import Path
from .brief import build_brief, format_brief


def main():
    parser = argparse.ArgumentParser(description="OrbitMinder daily brief")
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()
    records = json.loads(args.data.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        parser.error("Expected a JSON array of projects")
    print(format_brief(build_brief(records, date.fromisoformat(args.date))), end="")


if __name__ == "__main__":
    main()
