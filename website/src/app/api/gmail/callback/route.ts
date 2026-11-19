import { timingSafeEqual } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";
import { decryptTransient, gmailConfig, metadataScope, permittedIdentity, readTokens, saveTokens } from "@/lib/gmail";

export const runtime = "nodejs";
export async function GET(request: NextRequest) {
  const back = new URL("/dashboard", request.url);
  const result = (code: string) => {
    back.searchParams.set("gmail", code);
    const response = NextResponse.redirect(back);
    response.cookies.set("orbit_gmail_oauth", "", { path: "/api/gmail", maxAge: 0 });
    response.headers.set("Cache-Control", "no-store");
    return response;
  };
  const identity = await permittedIdentity();
  if (!identity.ok) return result("session_required");
  const value = request.cookies.get("orbit_gmail_oauth")?.value;
  const code = request.nextUrl.searchParams.get("code");
  const state = request.nextUrl.searchParams.get("state");
  if (!value || !code || !state || code.length > 4096) return result("not_connected");
  try {
    const pending = decryptTransient(value) as {
      state: string; verifier: string; owner: string; email: string; created_at: number;
    };
    if (!pending || pending.owner !== identity.subject || pending.email !== identity.email ||
        !Number.isFinite(pending.created_at) || Date.now() - pending.created_at > 600000 ||
        typeof pending.state !== "string" || typeof pending.verifier !== "string") {
      return result("not_connected");
    }
    const left = Buffer.from(state);
    const right = Buffer.from(pending.state);
    if (left.length !== right.length || !timingSafeEqual(left, right)) return result("not_connected");

    const config = gmailConfig();
    const tokenResponse = await fetch("https://oauth2.googleapis.com/token", {
      method: "POST", cache: "no-store",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        code, client_id: config.clientId, client_secret: config.clientSecret,
        redirect_uri: config.redirect, code_verifier: pending.verifier,
        grant_type: "authorization_code",
      }),
      signal: AbortSignal.timeout(10000),
    });
    if (!tokenResponse.ok) return result("not_connected");
    const tokens = await tokenResponse.json() as {
      access_token?: string; refresh_token?: string; expires_in?: number; scope?: string;
    };
    if (!tokens.access_token || !tokens.scope?.split(" ").includes(metadataScope)) return result("scope_missing");
    const userResponse = await fetch("https://openidconnect.googleapis.com/v1/userinfo", {
      headers: { Authorization: "Bearer " + tokens.access_token }, cache: "no-store",
      signal: AbortSignal.timeout(10000),
    });
    if (!userResponse.ok) return result("not_connected");
    const account = await userResponse.json() as { email?: string; email_verified?: boolean };
    // First version only connects the same Google email as the signed-in owner.
    if (!account.email_verified || account.email?.trim().toLowerCase() !== identity.email) {
      return result("account_mismatch");
    }
    const prior = await readTokens(identity.subject);
    const refresh = tokens.refresh_token || (prior?.email === identity.email ? prior.refresh_token : undefined);
    if (!refresh) return result("refresh_missing");
    await saveTokens(identity.subject, {
      email: identity.email, refresh_token: refresh, access_token: tokens.access_token,
      expires_at: Date.now() + Math.max(0, tokens.expires_in ?? 3500) * 1000,
    });
    return result("connected");
  } catch {
    return result("not_connected");
  }
}
