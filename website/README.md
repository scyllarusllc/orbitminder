# OrbitMinder website

Next.js 16 App Router + React 19 + TypeScript + Tailwind CSS 4. The public website, Google sign-in
and a private Dashboard shell share one Next.js project. The Python core is unchanged.

## Local development

Requires Node.js 22+.

```bash
cd website
npm install
cp .env.example .env.local
# Configure AUTH_SECRET, AUTH_GOOGLE_ID and AUTH_GOOGLE_SECRET to enable sign-in.
npm run dev
npm test
npm run lint
npm run typecheck
npm run build
```

Visit http://localhost:3000 for the public homepage, /login for Google sign-in,
and /dashboard for the private dashboard shell. The dashboard requires an authenticated
verified Google account. It includes a manual, read-only GitHub brief request; this requires
ORBITMINDER_GITHUB_OWNER and ORBITMINDER_ALLOWED_EMAILS. By default, no user is authorized
for shared project data until an allowlist is configured. A server-side GITHUB_TOKEN is
optional for private repos. The API runs the existing Python CLI from the repo root and returns
JSON; Python 3.10+ must be installed in the same server deployment. No credential is sent to
the browser. This is a single-owner integration, not yet multi-tenant per-user GitHub OAuth.

OAuth setup and security notes: [docs/google-login.md](docs/google-login.md).

## Deployment status

No production domain or Google OAuth client has been verified.
Do not claim deployed login until configured and tested against Google.
GitHub Action `website.yml` runs tests, lint, TypeScript and production build on website changes.
`npm test` currently contains lightweight source/configuration regression checks,
**not** a full simulated-provider OAuth test or end-to-end browser test. These are required before launch.

## Integration constraints

The on-demand GitHub sync checks up to five nonarchived repositories from the first 20.
The Python CLI limits request duration in the Node wrapper; GitHub activity requests may still
encounter rate limits. When the service is unavailable or the account lacks authorization,
the Dashboard displays an error instead of fabricated results. Production deployments must
run Python alongside the Node.js server and keep the GitHub token private.

## Next integration

Expose the existing Python GitHub sync and brief engine via a read-only API with service-level
authorization, explicit data freshness and per-account access controls; do not serve GitHub tokens
to the browser. Gmail, Calendar and AgentSteers are later milestones.

License: AGPL-3.0-only (see repository root LICENSE).
