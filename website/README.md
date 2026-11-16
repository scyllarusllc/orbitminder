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
verified Google account; it has no real project data yet.

OAuth setup and security notes: [docs/google-login.md](docs/google-login.md).

## Deployment status

No production domain or Google OAuth client has been verified.
Do not claim deployed login until configured and tested against Google.
GitHub Action `website.yml` runs tests, lint, TypeScript and production build on website changes.
`npm test` currently contains lightweight source/configuration regression checks,
**not** a full simulated-provider OAuth test or end-to-end browser test. These are required before launch.

## Next integration

Expose the existing Python GitHub sync and brief engine via a read-only API with service-level
authorization, explicit data freshness and per-account access controls; do not serve GitHub tokens
to the browser. Gmail, Calendar and AgentSteers are later milestones.

License: AGPL-3.0-only (see repository root LICENSE).
