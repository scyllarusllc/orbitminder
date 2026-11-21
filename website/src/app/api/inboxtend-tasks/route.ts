import { auth } from "@/auth";
import { execFile } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const exec = promisify(execFile);
const headers = { "Cache-Control": "private, no-store" };

export async function GET() {
  const session = await auth();
  const owner = session?.user?.id;
  const email = session?.user?.email?.trim().toLowerCase();
  if (!owner || !email) {
    return Response.json({ error: "Authentication required" }, { status: 401, headers });
  }
  const allowlist = (process.env.ORBITMINDER_ALLOWED_EMAILS ?? "").split(",")
    .map(value => value.trim().toLowerCase()).filter(Boolean);
  if (!allowlist.includes(email)) {
    return Response.json({ error: "Not authorized" }, { status: 403, headers });
  }
  const db = process.env.ORBITMINDER_DB_PATH;
  const account = process.env.INBOXTEND_ACCOUNT_KEY;
  if (!db || !path.isAbsolute(db) || !account?.trim()) {
    return Response.json({ error: "Task snapshot is not configured" }, { status: 503, headers });
  }
  try {
    const { stdout } = await exec(process.env.ORBITMINDER_PYTHON || "python3",
      ["-m", "orbitminder.cached_tasks", "--db", db, "--owner", owner, "--account", account, "--limit", "100"],
      { cwd: path.resolve(process.cwd(), ".."), timeout: 15000, maxBuffer: 1_000_000, windowsHide: true });
    const parsed: unknown = JSON.parse(stdout);
    if (!parsed || typeof parsed !== "object" || !("mode" in parsed) ||
        parsed.mode !== "cached_inboxtend_tasks" || !("items" in parsed) ||
        !Array.isArray(parsed.items)) throw new Error("Invalid cached task response");
    return Response.json(parsed, { headers });
  } catch {
    return Response.json({ error: "Cached task snapshot unavailable" }, { status: 503, headers });
  }
}
