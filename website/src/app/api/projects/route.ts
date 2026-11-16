import { auth } from "@/auth";
import { execFile } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const exec = promisify(execFile);
const noStore = { "Cache-Control": "private, no-store" };

export async function GET() {
  const session = await auth();
  const email = session?.user?.email?.toLowerCase();
  if (!session?.user?.id || !email) {
    return Response.json({ error: "Authentication required" }, { status: 401, headers: noStore });
  }

  // A shared server-side GitHub token must NEVER expose its private repositories
  // to every arbitrary Google account. Per-user OAuth is a later milestone.
  const allowed = (process.env.ORBITMINDER_ALLOWED_EMAILS ?? "")
    .split(",").map(value => value.trim().toLowerCase()).filter(Boolean);
  if (!allowed.includes(email)) {
    return Response.json({ error: "This account is not authorized for project data" }, { status: 403, headers: noStore });
  }

  const owner = process.env.ORBITMINDER_GITHUB_OWNER;
  if (!owner || !/^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$/.test(owner)) {
    return Response.json({ error: "GitHub integration is not configured" }, { status: 503, headers: noStore });
  }

  const cwd = path.resolve(process.cwd(), "..");
  try {
    const { stdout } = await exec(
      process.env.ORBITMINDER_PYTHON || "python3",
      ["-m", "orbitminder.cli", "--github-owner", owner, "--github-limit", "20",
        "--github-activity", "--activity-max-repos", "5", "--format", "json"],
      { cwd, timeout: 45_000, maxBuffer: 1_000_000, windowsHide: true }
    );
    const result: unknown = JSON.parse(stdout);
    return Response.json(result, { headers: noStore });
  } catch {
    // Never reveal command output or credentials in public responses.
    return Response.json({ error: "GitHub data is temporarily unavailable" }, { status: 502, headers: noStore });
  }
}
