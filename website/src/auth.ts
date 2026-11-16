import NextAuth from "next-auth";
import Google from "next-auth/providers/google";

// All OAuth exchanges happen on the server. Only identity is included in
// the session, never Google access/refresh tokens.
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
});

export const googleLoginConfigured = configured;
