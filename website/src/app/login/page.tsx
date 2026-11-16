import Link from "next/link";
import { redirect } from "next/navigation";
import { auth, googleLoginConfigured, signIn } from "@/auth";

export const metadata = { title: "Sign in | OrbitMinder" };

export default async function Login() {
  const session = await auth();
  if (session?.user) redirect("/dashboard");

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#080c19] p-6 text-slate-100">
      <section className="w-full max-w-md rounded-3xl border border-white/15 bg-white/[0.04] p-8">
        <Link href="/" className="text-lg font-semibold">✦ OrbitMinder</Link>
        <h1 className="mt-10 text-3xl font-semibold">Welcome back</h1>
        <p className="mt-3 text-slate-300">
          Sign in to access your personal project command center.
        </p>
        {googleLoginConfigured ? (
          <form className="mt-8" action={async () => {
            "use server";
            await signIn("google", { redirectTo: "/dashboard" });
          }}>
            <button type="submit" className="w-full rounded-xl bg-cyan-300 px-4 py-3 font-semibold text-slate-950 hover:bg-cyan-200">
              Continue with Google
            </button>
          </form>
        ) : (
          <div role="status" className="mt-8 rounded-xl border border-amber-200/30 bg-amber-200/10 p-4 text-sm text-amber-100">
            Google sign-in is not configured on this deployment. The site remains in preview mode.
          </div>
        )}
        <p className="mt-6 text-xs text-slate-400">
          Sign-in requests only basic Google identity details. Gmail and Calendar permissions are not requested.
        </p>
      </section>
    </main>
  );
}
