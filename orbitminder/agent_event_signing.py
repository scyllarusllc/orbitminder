"""Verify an optional operator-approved signed observation envelope.

HMAC only authenticates a holder of the configured shared key. It does not
prove AgentSteers itself authored the records, and is not a live connector.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re


def canonical_observations(owner_id: str, observations: list) -> bytes:
    """Stable UTF-8 bytes signed by the trusted producer, bound to one owner."""
    return json.dumps(
        {"owner_id": owner_id, "schema_version": 1, "observations": observations},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def verify_envelope(payload: dict, owner_id: str, secret: str | None) -> list:
    """Fail closed for bad signatures whenever the operator enables signing.

    Unsigned legacy imports are permitted only when signing is not configured;
    they must still have independently reviewed provenance.
    """
    if not isinstance(payload, dict):
        raise ValueError("invalid import envelope")
    if type(payload.get("schema_version")) is not int or payload["schema_version"] != 1:
        raise ValueError("unsupported schema version")
    observations = payload.get("observations")
    if not isinstance(observations, list):
        raise ValueError("observations must be an array")

    if secret:
        if len(secret.encode("utf-8")) < 32:
            raise ValueError("signing secret too short")
        if set(payload) != {"schema_version", "observations", "owner_id", "signature"}:
            raise ValueError("signed envelope fields required")
        if payload["owner_id"] != owner_id:
            raise ValueError("signed owner does not match trusted session")
        signature = payload["signature"]
        if not isinstance(signature, str) or not re.fullmatch(r"[0-9a-f]{64}", signature):
            raise ValueError("invalid signature format")
        expected = hmac.new(
            secret.encode("utf-8"), canonical_observations(owner_id, observations),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise ValueError("invalid observation signature")
    else:
        if set(payload) != {"schema_version", "observations"}:
            raise ValueError("unsigned reviewed envelope required")
    return observations
