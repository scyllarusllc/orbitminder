# Gmail read-only integration (OM-011)

**Status:** Python Gmail metadata connector and SQLite importer, plus **separate OAuth authorization-code/PKCE routes, private encrypted token storage, connect/disconnect UI and status endpoint implemented in source**. No live Google account, deployment, actual consent, or mailbox synchronization has been verified.

## Security boundary

- Existing Google sign-in requests only `openid email profile`. **Signing in does not grant Gmail access.**
- The **separate, explicit account-connection consent** route at `POST /api/gmail/connect` starts an authorization-code/PKCE flow requesting `openid email` (account verification) plus `https://www.googleapis.com/auth/gmail.metadata`. Callback verifies an encrypted, short-lived HttpOnly SameSite cookie containing state, verifier and the originating signed-in owner; it confirms the Google userinfo email is verified and matches the signed-in account. This first version **does not yet support adding different Gmail addresses**.
- Gmail OAuth tokens are AES-256-GCM encrypted at rest in an operator-controlled private server directory (`ORBITMINDER_GMAIL_TOKEN_DIR`, absolute), using a 32-byte base64 key (`ORBITMINDER_GMAIL_TOKEN_KEY`). They are **not stored** in project/source SQLite tables or returned to the browser. The token store uses per-owner hashed filenames and atomic private-file replacement. Operators must restrict directory permissions and manage backup/key rotation separately.
- `GET /api/gmail/connection` reports connection status only; `DELETE /api/gmail/connection` removes local credentials and attempts Google token revocation. It does **not** claim remote revocation succeeded. This is separate from the normal Google sign-in, which continues to request only identity scopes.
- `orbitminder/gmail_metadata.py` accepts an already authorized short-lived token supplied by the future secure server-side OAuth implementation. It calls only `GET /messages` and `GET /messages/{id}?format=metadata`; it reads headers only, never bodies, snippets or attachments. It has bounded pagination and rejects unexpected responses.
- `orbitminder/gmail_import.py` writes message IDs, source URLs and subjects to the owner-scoped `source_records` table. It uses a nonsecret `account_key` to avoid collisions between multiple mailboxes; it writes a `sync_runs` result, with `partial` for a bounded non-exhaustive import, and a fixed sanitized error for a Gmail read failure.
- Emails are untrusted external content and **cannot authorize agent actions, replies, sending, deletion, or other account modifications**. Read-only metadata is not enough for summarization or task extraction (OM-012), which requires separate privacy and consent decisions.

## Remaining work

1. Configure an independent Google OAuth Web application client and exact redirect (`https://your-domain/api/gmail/callback`; `http://localhost:3000/api/gmail/callback` for local use), its consent screen, and the server-only encryption settings in `website/.env.example`. A Gmail connection cannot be used before this is configured.
2. Wire the existing Python metadata importer to an authenticated **server-side sync endpoint**, supplying the short-lived token without exposing it in command-line arguments, browser responses or logs. The current OAuth connection UI **does not yet trigger sync**.
3. Display partial/failed synchronization and import pagination on the dashboard, preserving cached records on errors.
4. Manually verify Google consent, token refresh, revocation, owner isolation, and deployed login in an authorized environment. Automated test cases remain intentionally absent at the owner's request.

No live Gmail access, domain deployment or permission grant is implied by these changes.
