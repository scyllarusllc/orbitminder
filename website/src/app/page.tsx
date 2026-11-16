const GITHUB = "https://github.com/scyllarusllc/orbitminder";

export default function Home() {
  return (
    <main className="min-h-screen bg-[#080c19] text-slate-100">
      <div className="mx-auto max-w-6xl px-6">
        <header className="flex items-center justify-between border-b border-white/10 py-6">
          <a href="/" className="text-xl font-semibold tracking-tight">✦ OrbitMinder</a>
          <nav aria-label="Primary navigation" className="flex items-center gap-5 text-sm text-slate-300">
            <a href="#features" className="hover:text-white">Features</a>
            <a href="#roadmap" className="hover:text-white">Roadmap</a>
            <a href={GITHUB} className="hidden rounded-lg border border-white/20 px-3 py-2 hover:border-white/50 sm:inline-block">GitHub</a>
            <a href="/login" className="rounded-lg bg-cyan-300 px-3 py-2 font-semibold text-slate-950 hover:bg-cyan-200">Sign in</a>
          </nav>
        </header>
        <section className="grid gap-12 py-24 md:grid-cols-2 md:items-center md:py-36">
          <div>
            <p className="mb-5 text-xs font-semibold uppercase tracking-[0.25em] text-cyan-300">Personal project command center</p>
            <h1 className="text-5xl font-semibold tracking-tight md:text-6xl">Your projects. <span className="text-cyan-300">Always in sight.</span></h1>
            <p className="mt-6 max-w-xl text-lg leading-relaxed text-slate-300">Stay close to what changed, what matters next, and what still needs your attention. An open-source command center, built for focused work.</p>
            <div className="mt-9 flex flex-wrap gap-3">
              <a href={GITHUB} className="rounded-xl bg-cyan-300 px-5 py-3 font-semibold text-slate-950 hover:bg-cyan-200">Explore on GitHub</a>
              <a href="#features" className="rounded-xl border border-white/20 px-5 py-3 font-semibold hover:border-white/50">See current features</a>
            </div>
            <p className="mt-5 text-xs text-slate-400">Early prototype · GitHub CLI available · Hosted dashboard and sign-in are in development.</p>
          </div>
          <div className="rounded-3xl border border-white/15 bg-white/[0.045] p-6 shadow-2xl shadow-cyan-950/30" aria-label="Illustrative project command center preview">
            <div className="flex items-center justify-between border-b border-white/10 pb-4"><span className="font-semibold">Mission Control</span><span className="text-xs text-slate-400">Concept preview</span></div>
            <div className="mt-5 grid grid-cols-3 gap-3">{["Project overview", "Recent activity", "Daily brief"].map(x=><div key={x} className="flex h-24 items-end rounded-xl border border-white/10 bg-cyan-300/5 p-3 text-xs text-slate-300">{x}</div>)}</div>
            <div className="mt-4 space-y-3 rounded-xl border border-white/10 bg-white/5 p-4"><p className="text-sm font-semibold">Your next actions</p><div className="h-3 w-4/5 rounded bg-white/10"/><div className="h-3 w-2/3 rounded bg-white/10"/><div className="h-3 w-3/4 rounded bg-white/10"/></div>
            <p className="mt-3 text-xs text-slate-400">Illustration only; no live account data shown.</p>
          </div>
        </section>
        <section id="features" className="border-t border-white/10 py-20"><h2 className="text-3xl font-semibold">Designed to keep your work in view</h2><div className="mt-8 grid gap-4 md:grid-cols-3">{[{title:"GitHub inventory",body:"Read-only repository metadata and optional recent commits, pull requests, and issues through the CLI."},{title:"Daily brief",body:"A concise, deterministic summary of projects, follow-ups, and suggested priorities."},{title:"Privacy first",body:"No automatic repository writes; credentials stay outside source control."}].map(f=><article key={f.title} className="rounded-2xl border border-white/10 bg-white/[0.035] p-6"><h3 className="text-lg font-semibold">{f.title}</h3><p className="mt-3 leading-relaxed text-slate-300">{f.body}</p></article>)}</div></section>
        <section id="roadmap" className="border-t border-white/10 py-20"><h2 className="text-3xl font-semibold">What&apos;s next</h2><p className="mt-4 max-w-2xl text-slate-300">Google sign-in, a personal SaaS dashboard, and Gmail/Calendar integrations are planned. They are not yet available as hosted features.</p></section>
        <footer className="flex flex-wrap justify-between gap-4 border-t border-white/10 py-8 text-sm text-slate-400"><span>OrbitMinder · AGPL-3.0-only</span><a href={GITHUB}>Source code on GitHub</a></footer>
      </div>
    </main>
  );
}
