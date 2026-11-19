import { NextRequest } from "next/server";
import { gmailConfig, jsonError, permittedIdentity, readTokens, removeTokens } from "@/lib/gmail";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const headers = { "Cache-Control": "private, no-store" };

export async function GET() {
  const identity = await permittedIdentity();
  if (!identity.ok) return jsonError(identity.error, identity.status);
  try {
    gmailConfig();
    const account = await readTokens(identity.subject);
    return Response.json({
      configured: true,
      connected: Boolean(account),
      account_email: account?.email ?? null,
      scope: "gmail.metadata",
      mode: "read_only_metadata",
    }, { headers });
  } catch {
    return Response.json({ configured: false, connected: false },
      { status: 503, headers });
  }
}

export async function DELETE(request: NextRequest) {
  const identity = await permittedIdentity();
  if (!identity.ok) return jsonError(identity.error, identity.status);
  const config = gmailConfig();
  if (request.headers.get("origin") !== new URL(config.redirect).origin) {
    return jsonError("Invalid request origin", 403);
  }
  try {
    const tokens = await readTokens(identity.subject);
    // Best-effort Google revocation; local encrypted credential removal still wins.
    if (tokens?.refresh_token) {
      try {
        await fetch("https://oauth2.googleapis.com/revoke", {
          method: "POST", cache: "no-store",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: new URLSearchParams({ token: tokens.refresh_token }),
          signal: AbortSignal.timeout(8000),
        });
      } catch { /* Network revocation is best effort, not verified. */ }
    }
    await removeTokens(identity.subject);
    return Response.json({ connected: false, local_credentials_removed: true,
      google_revocation_confirmed: false }, { headers });
  } catch {
    return jsonError("Could not remove Gmail credentials", 503);
  }
}
