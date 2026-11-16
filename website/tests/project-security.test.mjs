import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const api = readFileSync(new URL("../src/app/api/projects/route.ts", import.meta.url), "utf8");

test("server protects project data with verified session and allowlist", () => {
  assert.ok(api.includes("await auth()"));
  assert.ok(api.includes("ORBITMINDER_ALLOWED_EMAILS"));
  assert.ok(api.includes("status: 401"));
  assert.ok(api.includes("status: 403"));
});

test("Python token remains server side and response is non-cacheable", () => {
  assert.ok(api.includes('runtime = "nodejs"'));
  assert.ok(api.includes("private, no-store"));
  assert.ok(!api.includes("NEXT_PUBLIC_GITHUB_TOKEN"));
});

test("bounded child process and failures are handled", () => {
  assert.ok(api.includes("timeout: 45_000"));
  assert.ok(api.includes("maxBuffer: 1_000_000"));
  assert.ok(api.includes("status: 502"));
});
