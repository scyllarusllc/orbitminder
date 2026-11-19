"use client";

import { useState } from "react";

type Activity = {
  commits_last_n_days: number;
  window_days: number;
  open_pull_requests: number;
  open_issues: number;
};
type Brief = {
  date: string;
  project_count: number;
  top_three: [number, string, string][];
  waiting: string[];
  blocked: string[];
  due: string[];
  unverified: string[];
  activity: [string, Activity, string][];
};

export default function ProjectActivity() {
  const [state, setState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [brief, setBrief] = useState<Brief | null>(null);
  const [error, setError] = useState("");

  async function load() {
    setState("loading");
    setBrief(null);
    setError("");
    try {
      const response = await fetch("/api/projects", { cache: "no-store" });
      const data: unknown = await response.json();
      if (!response.ok) {
        const message = data && typeof data === "object" && "error" in data &&
          typeof data.error === "string" ? data.error : "Unable to fetch projects";
        throw new Error(message);
      }
      if (!data || typeof data !== "object" ||
          !("project_count" in data) || typeof data.project_count !== "number" ||
          !("top_three" in data) || !Array.isArray(data.top_three) ||
          !("activity" in data) || !Array.isArray(data.activity) ||
          !("unverified" in data) || !Array.isArray(data.unverified)) {
        throw new Error("GitHub returned an unexpected summary");
      }
      setBrief(data as Brief);
      setState("ready");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to fetch projects");
      setState("error");
    }
  }

  return <section className="mt-10 rounded-2xl border border-white/15 bg-white/[0.04] p-6">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 className="text-xl font-semibold">GitHub daily brief</h2>
        <p className="mt-1 text-sm text-slate-400">Read-only, on-demand synchronization</p>
      </div>
      <button type="button" disabled={state === "loading"} onClick={load}
        className="rounded-xl bg-cyan-300 px-4 py-2 font-semibold text-slate-950 disabled:opacity-50">
        {state === "loading" ? "Checking…" : "Check GitHub"}
      </button>
    </div>
    {state === "idle" && <p className="mt-5 text-slate-300">Choose Check GitHub to request a fresh summary.</p>}
    {state === "error" && <p role="alert" className="mt-5 text-amber-200">{error}. No previous snapshot is being presented as current.</p>}
    {state === "ready" && brief && <div className="mt-6 space-y-6">
      <p className="text-sm text-slate-300">{brief.project_count} repositories · brief date {brief.date} · {brief.activity.length} activity-checked</p>
      <div>
        <h3 className="font-semibold">Suggested next actions</h3>
        {brief.top_three.length === 0 ? <p className="mt-2 text-slate-300">No recorded actions.</p> :
          <ol className="mt-2 list-inside list-decimal space-y-2 text-slate-200">
            {brief.top_three.map(([, name, action]) => <li key={name}><strong>{name}</strong>: {action}</li>)}
          </ol>}
      </div>
      <div>
        <h3 className="font-semibold">Verified GitHub activity samples</h3>
        {brief.activity.length === 0 ? <p className="mt-2 text-slate-300">No repository activity was checked.</p> :
          <ul className="mt-3 space-y-3">
            {brief.activity.map(([name, counts, url]) => <li key={name} className="rounded-xl border border-white/10 p-4">
              <strong>{url.startsWith("https://github.com/") ?
                <a className="underline decoration-white/30 hover:decoration-white" href={url} target="_blank" rel="noopener noreferrer">{name}</a> :
                name}</strong>
              <p className="mt-1 text-sm text-slate-300">
                {counts.commits_last_n_days} commits in {counts.window_days} days · {counts.open_pull_requests} open PRs · {counts.open_issues} open issues
              </p>
            </li>)}
          </ul>}
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {([
          ["Waiting", brief.waiting],
          ["Blocked", brief.blocked],
          ["Follow-ups due", brief.due],
          ["Not live-verified", brief.unverified],
        ] as const).map(([title, items]) => <div key={title} className="rounded-xl border border-white/10 p-4">
          <h3 className="font-semibold">{title} ({items.length})</h3>
          <p className="mt-2 text-sm text-slate-300">{items.length ? items.join(", ") : "None recorded"}</p>
        </div>)}
      </div>
      <p className="text-xs text-slate-400">Suggestions are rule-based, not AI decisions. Activity is sampled for up to five repositories from the first twenty. Counts may be lower bounds; unchecked repositories are not verified and zero does not mean no activity.</p>
    </div>}
  </section>;
}
