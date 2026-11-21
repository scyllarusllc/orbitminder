"""Operator-only local signing of independently reviewed Agent observations.

No network connection or AgentSteers claim. Private secret never goes to
the browser or into command-line arguments.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

from .agent_event_signing import sign_envelope


def main() -> int:
    parser = argparse.ArgumentParser(description="Sign independently reviewed Agent observations")
    parser.add_argument("--file", required=True, type=Path, help="Absolute reviewed unsigned JSON")
    parser.add_argument("--output", required=True, type=Path, help="New private signed JSON path")
    args = parser.parse_args()
    owner = os.environ.get("ORBITMINDER_OWNER_ID", "").strip()
    secret = os.environ.get("ORBITMINDER_AGENT_EVENT_SIGNING_KEY")
    source, dest = args.file, args.output
    if (not owner
            or not source.is_absolute() or not source.is_file()
            or not dest.is_absolute() or not dest.parent.is_dir()
            or dest.exists() or source == dest):
        print("Trusted private input/output configuration required", file=sys.stderr)
        return 1
    try:
        if source.stat().st_size > 512_000:
            raise ValueError("observation file too large")
        payload = json.loads(source.read_text(encoding="utf-8"))
        if (not isinstance(payload, dict)
                or set(payload) != {"schema_version", "observations"}
                or type(payload["schema_version"]) is not int
                or payload["schema_version"] != 1):
            raise ValueError("expected reviewed unsigned v1 envelope")
        observations = payload["observations"]
        # Validate input shape before signing; importing remains responsible
        # for checking existing owner-scoped jobs and event replay conflicts.
        if not isinstance(observations, list) or not 1 <= len(observations) <= 500:
            raise ValueError("invalid batch size")
        for item in observations:
            if (not isinstance(item, dict) or set(item) !=
                    {"external_job_id", "event_key", "state", "mode", "observed_at"}):
                raise ValueError("invalid observation schema")
            if (any(not isinstance(item[key], str) or not item[key].strip()
                    or len(item[key]) > 200
                    for key in ("external_job_id", "event_key", "state", "observed_at"))
                    or item["mode"] not in ("mock", "real")):
                raise ValueError("invalid observation values")
            seen_at = datetime.fromisoformat(item["observed_at"].replace("Z", "+00:00"))
            if seen_at.tzinfo is None or seen_at.astimezone(timezone.utc) > datetime.now(timezone.utc):
                raise ValueError("invalid observation timestamp")
        if secret is None:
            raise ValueError("signing key not configured")
        envelope = sign_envelope(owner, observations, secret)
        # Fail closed if local serialization diverges from consumer verification.
        from .agent_event_signing import verify_envelope
        verify_envelope(envelope, owner, secret)
        data = json.dumps(envelope, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        if len(data.encode("utf-8")) > 512_000:
            raise ValueError("signed output too large")
        # Exclusive private creation; never replace an existing file.
        with os.fdopen(os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600),
                       "w", encoding="utf-8") as stream:
            stream.write(data + "\n")
    except (OSError, UnicodeError, ValueError, TypeError, json.JSONDecodeError):
        print("Observation signing rejected; source data and key not printed", file=sys.stderr)
        return 1
    print(json.dumps({"mode": "operator_reviewed_signed_export", "count": len(observations)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
