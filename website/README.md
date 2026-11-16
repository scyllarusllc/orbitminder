# OrbitMinder website

Initial Next.js App Router frontend using React, TypeScript, and Tailwind CSS 4.

## Local development

Requires Node.js 22+.

```bash
cd website
npm install
npm run dev
# open http://localhost:3000
npm run typecheck
npm run lint
npm run build
```

This is the **public marketing website scaffold**, not an authenticated dashboard. The hero illustration contains no real user data. Google OAuth, sessions, and the authenticated dashboard will be implemented separately, with mock-provider tests before any claim of real sign-in. Do not put OAuth secrets into frontend code. Python CLI stays in the repository root.

For production, deploy behind HTTPS and verify domain ownership before setting the Google OAuth callback.
