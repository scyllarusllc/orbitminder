"""Import Gmail metadata into the existing owner-scoped SQLite source index.

The caller must provide an authenticated owner identity and a short-lived,
separately consented Gmail metadata token. Never read bodies or store tokens.
This library is not an HTTP endpoint and cannot authorize consent by itself.
"""
from __future__ import annotations

from .gmail_metadata import GmailMetadataError, collect_metadata
from .storage import ProjectStore, _now


def import_gmail_metadata(store: ProjectStore, owner_id: str, account_key: str,
                          access_token: str, *, max_messages: int = 50):
    if not isinstance(owner_id, str) or not owner_id.strip():
        raise ValueError("Authenticated owner required")
    if not isinstance(account_key, str) or not account_key.strip() or len(account_key) > 200:
        raise ValueError("Nonsecret account identifier required")
    try:
        page = collect_metadata(access_token, max_messages=max_messages)
        messages = page["messages"]
        # Partial imports are deliberately not reported as fully synchronized.
        state = "succeeded" if page["complete"] else "partial"
        observed_at = _now()
        for message in messages:
            store.upsert_source(
                owner_id, provider="gmail", account_key=account_key,
                external_id=message["id"], source_url=message["source_url"],
                title=message["subject"], observed_at=observed_at,
                verification_state="verified",
            )
        store.record_sync(owner_id, provider="gmail", account_key=account_key,
                          state=state, checked_count=len(messages))
        return {
            "status": state, "checked_count": len(messages),
            "has_more": not page["complete"],
            "next_page_token": page["next_page_token"],
        }
    except GmailMetadataError:
        # Store only a fixed non-sensitive error code.
        store.record_sync(owner_id, provider="gmail", account_key=account_key,
                          state="failed", last_error="gmail_metadata_unavailable")
        raise
