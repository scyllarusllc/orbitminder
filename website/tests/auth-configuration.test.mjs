import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = path => readFileSync(new URL(path, import.meta.url), "utf8");

test("private dashboard checks server-side session", () => {
  const dashboard = read("../src/app/dashboard/page.tsx");
  assert.match(dashboard, /await auth\(\)/);
  assert.match(dashboard, /redirect\("\/login"\)/);
});

test("auth callback uses Auth.js and verified Google accounts", () => {
  const auth = read("../src/auth.ts");
  assert.match(auth, /Google\(/);
  assert.match(auth, /email_verified === true/);
  assert.match(auth, /strategy: "jwt"/);
});

test("no client-public OAuth secrets", () => {
  const example = read("../.env.example");
  assert.doesNotMatch(example, /^NEXT_PUBLIC_AUTH_/m);
  assert.match(example, /^AUTH_GOOGLE_SECRET=/m);
});

test("dashboard clearly distinguishes non-live data", () => {
  const dashboard = read("../src/app/dashboard/page.tsx");
  assert.match(dashboard, /Data connectors have not been activated/);
});
