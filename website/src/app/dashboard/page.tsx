import ProjectActivity from "@/components/project-activity";
import SavedProjects from "@/components/saved-projects";
import Link from "next/link";
import { redirect } from "next/navigation";
import { auth, signOut } from "@/auth";

export const metadata = { title: "Dashboard | OrbitMinder" };

const planned = [
  { title: "My projects", detail: "Saved SQLite project overview is available when the server database is configured." },
  { title: "Activity", detail: "Check GitHub below for a separate on-demand activity snapshot." },
  { title: "Daily brief", detail: "Rule-based GitHub suggestions are available from the on-demand brief." },
];

export default async function Dashboard() {
  const session = await auth();
  if (!session?.user || !session.user.id) redirect("/login");

  const name = session.user.name ?? "there";

  return (
    <main className="min-h-screen bg-[#080c19] text-slate-100">
      <header className="mx-auto flex max-w-6xl items-center justify-between gap-4 border-b border-white/10 px-6 py-5">
        <Link href="/" className="font-semibold">✦ OrbitMinder</Link>
        <form action={async () => {
          "use server";
          await signOut({ redirectTo: "/" });
        }}>
          <button className="rounded-lg border border-white/20 px-4 py-2 text-sm hover:border-white/50">Sign out</button>
        </form>
      </header>
      <div className="mx-auto max-w-6xl px-6 py-12">
        <p className="text-sm uppercase tracking-widest text-cyan-300">Mission Control</p>
        <h1 className="mt-3 text-4xl font-semibold">Welcome, {name}</h1>
        <p className="mt-4 text-slate-300">Your private workspace separates stored project snapshots from on-demand GitHub checks. Saved storage requires server configuration.</p>
        <div className="mt-10 grid gap-5 md:grid-cols-3">
          {planned.map(card => (
            <section key={card.title} className="rounded-2xl border border-white/15 bg-white/[0.04] p-6">
              <h2 className="text-lg font-semibold">{card.title}</h2>
              <p className="mt-3 text-sm leading-relaxed text-slate-300">{card.detail}</p>
              <span className="mt-5 inline-block text-xs text-cyan-300">Source-dependent</span>
            </section>
          ))}
        </div>
        <SavedProjects />
        <ProjectActivity />
        <p className="mt-8 text-xs text-slate-400">No sample values are presented as live user data.</p>
      </div>
    </main>
  );
}
