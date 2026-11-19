import { randomBytes, createHash } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";
import { encryptTransient, gmailConfig, jsonError, metadataScope, permittedIdentity } from "@/lib/gmail";

export const runtime = "nodejs";
export async function POST(request: NextRequest) {
  const identity = await permittedIdentity();
  if (!identity.ok) return jsonError(identity.error, identity.status);
  let config: ReturnType<typeof gmailConfig>;
  try { config = gmailConfig(); } catch { return jsonError("Gmail connection not configured", 503); }
  const origin = request.headers.get("origin");
  const expected = new URL(config.redirect).origin;
  if (origin !== expected) return jsonError("Invalid request origin", 403);

  const state = randomBytes(32).toString("base64url");
  const verifier = randomBytes(32).toString("base64url");
  const challenge = createHash("sha256").update(verifier).digest("base64url");
  const url = new URL("https://accounts.google.com/o/oauth2/v2/auth");
  url.search = new URLSearchParams({
    client_id: config.clientId, redirect_uri: config.redirect, response_type: "code",
    scope: "openid email " + metadataScope, access_type: "offline",
    prompt: "consent", state, code_challenge: challenge, code_challenge_method: "S256",
  }).toString();
  const response = NextResponse.json({ authorization_url: url.toString() },
    { headers: { "Cache-Control": "private, no-store" } });
  response.cookies.set("orbit_gmail_oauth", encryptTransient({
    state, verifier, owner: identity.subject, email: identity.email, created_at: Date.now(),
  }), { httpOnly: true, sameSite: "lax", secure: expected.startsWith("https:"),
    path: "/api/gmail", maxAge: 600 });
  return response;
}
