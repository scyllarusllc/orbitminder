import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = path => readFileSync(new URL(path, import.meta.url), "utf8");

test("private dashboard checks server-side session", () => {
  const dashboard = read("../src/app/dashboard/page.tsx");
  assert.ok(dashboard.includes("await auth()"));
  assert.ok(dashboard.includes('redirect("/login")'));
});

test("auth callback uses Auth.js and verified Google accounts", () => {
  const auth = read("../src/auth.ts");
  assert.ok(auth.includes("Google({"));
  assert.ok(auth.includes("email_verified === true"));
  assert.ok(auth.includes('strategy: "jwt"'));
});

test("no client-public OAuth secrets", () => {
  const example = read("../.env.example");
  assert.doesNotMatch(example, /^NEXT_PUBLIC_AUTH_/m);
  assert.match(example, /^AUTH_GOOGLE_SECRET=/m);
});

test("dashboard clearly distinguishes non-live data", () => {
  const dashboard = read("../src/app/dashboard/page.tsx");
  assert.ok(dashboard.includes("Data connectors have not been activated"));
});
