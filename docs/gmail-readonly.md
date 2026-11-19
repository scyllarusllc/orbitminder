# Gmail read-only integration (OM-011)

**Status:** Python metadata connector and owner-scoped SQLite import code committed; **Google Gmail OAuth consent flow and web UI not yet implemented or verified**. No mailbox was accessed during development.

## Security boundary

- Existing Google sign-in requests only `openid email profile`. **Signing in does not grant Gmail access.**
- A future **separate, explicit account-connection consent** flow must request only `https://www.googleapis.com/auth/gmail.metadata`, bind the Google account to the authenticated OrbitMinder user, and protect state/PKCE, CSRF and revocation. OAuth access/refresh tokens must be managed server-side securely and never stored in the project/source tables, logged or returned to the browser.
- `orbitminder/gmail_metadata.py` accepts an already authorized short-lived token supplied by the future secure server-side OAuth implementation. It calls only `GET /messages` and `GET /messages/{id}?format=metadata`; it reads headers only, never bodies, snippets or attachments. It has bounded pagination and rejects unexpected responses.
- `orbitminder/gmail_import.py` writes message IDs, source URLs and subjects to the owner-scoped `source_records` table. It uses a nonsecret `account_key` to avoid collisions between multiple mailboxes; it writes a `sync_runs` result, with `partial` for a bounded non-exhaustive import, and a fixed sanitized error for a Gmail read failure.
- Emails are untrusted external content and **cannot authorize agent actions, replies, sending, deletion, or other account modifications**. Read-only metadata is not enough for summarization or task extraction (OM-012), which requires separate privacy and consent decisions.

## Remaining work

1. Build the Gmail-specific server-side consent and account connection flow, separate from sign-in, and user-controlled disconnect.
2. Bind the confirmed account to the signed-in owner, securely manage token refresh, and call the adapter from an authenticated service endpoint.
3. Display connection status, pagination/partial results and last successful sync in the dashboard; ensure failure never implies an empty mailbox.
4. Manually verify real OAuth and owner isolation in an authorized environment before enabling the connector. Automated test cases remain intentionally absent at the owner's request.

No live Gmail access, domain deployment or permission grant is implied by these changes.
