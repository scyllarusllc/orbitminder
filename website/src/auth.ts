import NextAuth from "next-auth";
import Google from "next-auth/providers/google";

// Authentication stays server-side. No Google tokens or secrets are sent to the browser.
// Auth.js uses OAuth state / PKCE protections and signed/encrypted session cookies.
const configured = Boolean(
  process.env.AUTH_GOOGLE_ID &&
  process.env.AUTH_GOOGLE_SECRET &&
  process.env.AUTH_SECRET
);

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: configured ? [Google({
    authorization: { params: { scope: "openid email profile" } },
  })] : [],
  session: { strategy: "jwt", maxAge: 60 * 60 * 24 * 7 },
  callbacks: {
    async signIn({ account, profile }) {
      if (account?.provider !== "google") return false;
      return profile?.email_verified === true &&
        typeof profile.sub === "string" &&
        profile.sub.length > 0;
    },
    async session({ session, token }) {
      if (session.user && typeof token.sub === "string") {
        session.user.id = token.sub;
      }
      return session;
    },
  },
  pages: { signIn: "/login" },
  trustHost: false,
});

export const googleLoginConfigured = configured;
