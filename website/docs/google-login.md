# OrbitMinder Google Sign-In

This Next.js application uses Auth.js (NextAuth v5) Google Provider, not a browser-side token exchange.
The design draws on the tested Saipan Finds server-side OAuth flow: state/PKCE, verified Google identity,
HttpOnly session cookies, and a safe logout. OAuth implementation is delegated to Auth.js.

## Configuration

1. In Google Cloud / Google Auth Platform, configure an OAuth consent screen and create a **Web application** client for OrbitMinder.
2. Add the exact redirect URI `http://localhost:3000/api/auth/callback/google` for local development.
3. After controlling the public domain and HTTPS deployment, add `https://YOUR_DOMAIN/api/auth/callback/google` in Google Cloud.
4. Copy `.env.example` to `.env.local`, set a strong `AUTH_SECRET`, `AUTH_GOOGLE_ID`, `AUTH_GOOGLE_SECRET`, and optionally `AUTH_URL` to your trusted canonical origin.
5. Run `npm install`, `npm run dev`, then test login, refresh, sign-out, denied consent, missing credentials, and unauthenticated Dashboard access.

Google sign-in requests only `openid email profile`. Do not request Gmail/Calendar scopes until those connectors exist.
Session cookies are managed by Auth.js. The session is identity-only and does not store Google API access or refresh tokens.

## Security and limits

- The dashboard performs server-side session checks. Do not rely on navigation hiding for access control.
- Never commit OAuth credentials or print them in logs. Rotate exposed credentials immediately.
- The initial JWT session is suitable for the preview. For centralized revocation / enterprise account administration,
  adopt a database-backed adapter and test sign-out and revocation across instances.
- The sign-in callback denies unverified Google identities.
- Only configure `AUTH_URL` for an origin you control; validate the reverse-proxy host/origin before production deployment.
- A passing mocked or static unit test is not proof of an actual Google OAuth production login.
