"""Gmail metadata-only, read-only adapter for OrbitMinder (OM-011).

A separately authorized OAuth flow must supply a short-lived access token with
https://www.googleapis.com/auth/gmail.metadata. No token is saved here.
No email bodies, snippets, attachments or modification endpoints are requested.
"""
from __future__ import annotations

import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

GMAIL_METADATA_SCOPE = "https://www.googleapis.com/auth/gmail.metadata"
_API = "https://gmail.googleapis.com/gmail/v1/users/me"
_ID = re.compile(r"^[A-Za-z0-9_-]{1,160}$")


class GmailMetadataError(RuntimeError):
    pass


def _get(path, access_token, *, params=None, opener=urlopen):
    if not isinstance(access_token, str) or not access_token.strip():
        raise GmailMetadataError("A separately authorized Gmail access token is required")
    url = _API + path + ("?" + urlencode(params) if params else "")
    req = Request(url, headers={
        "Authorization": "Bearer " + access_token,
        "Accept": "application/json",
        "User-Agent": "OrbitMinder/0.1",
    })
    try:
        with opener(req, timeout=15) as response:
            raw = response.read(1_000_001)
        if len(raw) > 1_000_000:
            raise GmailMetadataError("Gmail response exceeded size limit")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise GmailMetadataError("Unexpected Gmail response")
        return data
    except (HTTPError, URLError, TimeoutError, OSError, ValueError):
        raise GmailMetadataError("Gmail metadata request failed") from None


def list_message_ids(access_token, *, page_token=None, page_size=50, opener=urlopen):
    """One Gmail API page; the caller owns pagination and limits."""
    if type(page_size) is not int or not 1 <= page_size <= 100:
        raise ValueError("page_size must be between 1 and 100")
    if page_token is not None and (not isinstance(page_token, str) or len(page_token) > 2048):
        raise ValueError("Invalid page token")
    params = {"maxResults": page_size}
    if page_token:
        params["pageToken"] = page_token
    payload = _get("/messages", access_token, params=params, opener=opener)
    rows = payload.get("messages") or []
    if not isinstance(rows, list):
        raise GmailMetadataError("Invalid Gmail message listing")
    ids = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not _ID.fullmatch(row["id"]):
            raise GmailMetadataError("Invalid Gmail message identifier")
        ids.append(row["id"])
    cursor = payload.get("nextPageToken")
    if cursor is not None and not isinstance(cursor, str):
        raise GmailMetadataError("Invalid Gmail pagination cursor")
    return {"message_ids": ids, "next_page_token": cursor}


def get_message_metadata(access_token, message_id, *, opener=urlopen):
    """Get header metadata only, never format=full or attachment bytes."""
    if not isinstance(message_id, str) or not _ID.fullmatch(message_id):
        raise ValueError("Invalid Gmail message identifier")
    payload = _get("/messages/" + message_id, access_token, params={
        "format": "metadata",
        "metadataHeaders": ["From", "To", "Subject", "Date"],
    }, opener=opener)
    if payload.get("id") != message_id:
        raise GmailMetadataError("Unexpected Gmail message identifier")
    headers = (payload.get("payload") or {}).get("headers") or []
    if not isinstance(headers, list):
        raise GmailMetadataError("Invalid metadata headers")
    values = {}
    for header in headers:
        if isinstance(header, dict) and isinstance(header.get("name"), str):
            key = header["name"].lower()
            if key in ("from", "to", "subject", "date"):
                values[key] = str(header.get("value", ""))[:500]
    return {
        "id": message_id,
        "thread_id": payload.get("threadId") if isinstance(payload.get("threadId"), str) else None,
        "from": values.get("from", ""), "to": values.get("to", ""),
        "subject": values.get("subject", ""), "date_header": values.get("date", ""),
        "source_url": "https://mail.google.com/mail/u/0/#all/" + message_id,
    }


def collect_metadata(access_token, *, max_messages=50, page_size=50, opener=urlopen):
    """Bounded pagination for an explicitly consented mailbox.

    Does not imply completeness when the next_page_token is present.
    """
    if type(max_messages) is not int or not 1 <= max_messages <= 500:
        raise ValueError("max_messages must be 1 through 500")
    cursor, records = None, []
    while len(records) < max_messages:
        listing = list_message_ids(access_token, page_token=cursor,
                                   page_size=min(page_size, max_messages - len(records)),
                                   opener=opener)
        for message_id in listing["message_ids"]:
            records.append(get_message_metadata(access_token, message_id, opener=opener))
            if len(records) >= max_messages:
                break
        next_cursor = listing["next_page_token"]
        if not next_cursor or not listing["message_ids"] or next_cursor == cursor:
            cursor = None
            break
        cursor = next_cursor
    return {"messages": records, "next_page_token": cursor, "complete": cursor is None}
