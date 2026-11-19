import { createCipheriv, createDecipheriv, createHash, randomBytes } from "node:crypto";
import { mkdir, readFile, rename, unlink, writeFile } from "node:fs/promises";
import path from "node:path";
import { auth } from "@/auth";

export const metadataScope = "https://www.googleapis.com/auth/gmail.metadata";
export type GmailTokens = { refresh_token: string; access_token?: string; expires_at?: number; email: string };
const noStore = { "Cache-Control": "private, no-store" };

export async function permittedIdentity() {
  const session = await auth();
  const subject = session?.user?.id;
  const email = session?.user?.email?.trim().toLowerCase();
  if (!subject || !email) return { ok: false as const, status: 401, error: "Authentication required" };
  const allowed = (process.env.ORBITMINDER_ALLOWED_EMAILS ?? "").split(",")
    .map(value => value.trim().toLowerCase()).filter(Boolean);
  if (!allowed.includes(email)) return { ok: false as const, status: 403, error: "Not authorized" };
  return { ok: true as const, subject, email };
}

export function jsonError(message: string, status: number) {
  return Response.json({ error: message }, { status, headers: noStore });
}

export function gmailConfig() {
  const clientId = process.env.ORBITMINDER_GMAIL_CLIENT_ID;
  const clientSecret = process.env.ORBITMINDER_GMAIL_CLIENT_SECRET;
  const redirect = process.env.ORBITMINDER_GMAIL_REDIRECT_URI;
  const directory = process.env.ORBITMINDER_GMAIL_TOKEN_DIR;
  const keyText = process.env.ORBITMINDER_GMAIL_TOKEN_KEY;
  if (!clientId || !clientSecret || !redirect || !directory || !path.isAbsolute(directory) ||
      !keyText || !/^https:\/\//.test(redirect) && !/^http:\/\/localhost:/.test(redirect)) {
    throw new Error("Gmail OAuth not configured");
  }
  const url = new URL(redirect);
  if (url.pathname !== "/api/gmail/callback" || url.search || url.hash ||
      (url.protocol !== "https:" && !(url.protocol === "http:" && url.hostname === "localhost"))) {
    throw new Error("Untrusted Gmail redirect");
  }
  const key = Buffer.from(keyText, "base64");
  if (key.length !== 32) throw new Error("Invalid Gmail token encryption key");
  return { clientId, clientSecret, redirect, directory, key };
}

function tokenFile(directory: string, owner: string) {
  return path.join(directory, createHash("sha256").update(owner).digest("hex") + ".enc");
}
function seal(value: unknown, key: Buffer) {
  const iv = randomBytes(12);
  const cipher = createCipheriv("aes-256-gcm", key, iv);
  const bytes = Buffer.concat([cipher.update(JSON.stringify(value), "utf8"), cipher.final()]);
  return Buffer.concat([iv, cipher.getAuthTag(), bytes]).toString("base64url");
}
function unseal(value: string, key: Buffer) {
  const bytes = Buffer.from(value, "base64url");
  if (bytes.length < 29) throw new Error("Invalid encrypted record");
  const decipher = createDecipheriv("aes-256-gcm", key, bytes.subarray(0, 12));
  decipher.setAuthTag(bytes.subarray(12, 28));
  return JSON.parse(Buffer.concat([decipher.update(bytes.subarray(28)), decipher.final()]).toString("utf8")) as unknown;
}
export function encryptTransient(value: unknown) {
  return seal(value, gmailConfig().key);
}
export function decryptTransient(value: string): unknown {
  return unseal(value, gmailConfig().key);
}
export async function readTokens(owner: string): Promise<GmailTokens | null> {
  const config = gmailConfig();
  try {
    const record = await readFile(tokenFile(config.directory, owner), "utf8");
    const result = unseal(record, config.key) as GmailTokens;
    if (!result || typeof result.refresh_token !== "string" || typeof result.email !== "string") {
      throw new Error("Invalid stored token");
    }
    return result;
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return null;
    throw error;
  }
}
export async function saveTokens(owner: string, value: GmailTokens) {
  const config = gmailConfig();
  await mkdir(config.directory, { recursive: true, mode: 0o700 });
  const file = tokenFile(config.directory, owner);
  const temp = file + "." + randomBytes(6).toString("hex") + ".tmp";
  await writeFile(temp, seal(value, config.key), { mode: 0o600, flag: "wx" });
  try { await rename(temp, file); } catch (error) { await unlink(temp).catch(() => {}); throw error; }
}
export async function removeTokens(owner: string) {
  const config = gmailConfig();
  await unlink(tokenFile(config.directory, owner)).catch(error => {
    if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
  });
}
export async function refreshAccessToken(owner: string, tokens: GmailTokens) {
  if (tokens.access_token && tokens.expires_at && tokens.expires_at > Date.now() + 60_000) {
    return tokens.access_token;
  }
  const config = gmailConfig();
  const response = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST", cache: "no-store", headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ client_id: config.clientId, client_secret: config.clientSecret,
      refresh_token: tokens.refresh_token, grant_type: "refresh_token" }),
    signal: AbortSignal.timeout(10000),
  });
  if (!response.ok) throw new Error("Token refresh failed");
  const data = await response.json() as { access_token?: string; expires_in?: number; scope?: string };
  if (!data.access_token || !data.scope?.split(" ").includes(metadataScope)) throw new Error("Gmail scope missing");
  await saveTokens(owner, { ...tokens, access_token: data.access_token,
    expires_at: Date.now() + Math.max(0, data.expires_in ?? 3500) * 1000 });
  return data.access_token;
}
