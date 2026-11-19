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
  const subject = session?.user?.id;
  const email = session?.user?.email?.trim().toLowerCase();
  if (!subject || !email) {
    return Response.json({ error: "Authentication required" }, { status: 401, headers });
  }
  const allowed = (process.env.ORBITMINDER_ALLOWED_EMAILS ?? "").split(",")
    .map(value => value.trim().toLowerCase()).filter(Boolean);
  if (!allowed.includes(email)) {
    return Response.json({ error: "Not authorized for saved project data" }, { status: 403, headers });
  }
  const db = process.env.ORBITMINDER_DB_PATH;
  // Local DB path is operator-controlled; never accept a client-supplied path or owner.
  if (!db || !path.isAbsolute(db)) {
    return Response.json({ error: "Saved project storage is not configured" }, { status: 503, headers });
  }
  try {
    const { stdout } = await exec(process.env.ORBITMINDER_PYTHON || "python3",
      ["-m", "orbitminder.saved_overview", "--db", db, "--owner", subject],
      { cwd: path.resolve(process.cwd(), ".."), timeout: 15000, maxBuffer: 1_000_000, windowsHide: true });
    const parsed: unknown = JSON.parse(stdout);
    if (!parsed || typeof parsed !== "object" || !("mode" in parsed) ||
        parsed.mode !== "saved_snapshot") throw new Error("Invalid overview");
    return Response.json(parsed, { headers });
  } catch {
    return Response.json({ error: "Saved project overview unavailable" }, { status: 503, headers });
  }
}
