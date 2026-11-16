"use client";

import { useState } from "react";

type Brief = {
  date: string;
  project_count: number;
  top_three: [number, string, string][];
  waiting: string[];
  blocked: string[];
  due: string[];
  unverified: string[];
};

export default function ProjectActivity() {
  const [state, setState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [brief, setBrief] = useState<Brief | null>(null);
  const [error, setError] = useState("");

  async function load() {
    setState("loading");
    setError("");
    try {
      const response = await fetch("/api/projects", { cache: "no-store" });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.error === "string" ? data.error : "Unable to fetch projects");
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
    {state === "error" && <p role="alert" className="mt-5 text-amber-200">{error}</p>}
    {state === "ready" && brief && <div className="mt-6 space-y-4">
      <p className="text-sm text-slate-300">{brief.project_count} repositories · brief date {brief.date}</p>
      <h3 className="font-semibold">Suggested next actions</h3>
      {brief.top_three.length === 0 ? <p className="text-slate-300">No recorded actions.</p> :
        <ol className="list-inside list-decimal space-y-2 text-slate-200">
          {brief.top_three.map(([, name, action]) => <li key={name}><strong>{name}</strong>: {action}</li>)}
        </ol>}
      <p className="text-xs text-slate-400">Suggestions are rule-based, not AI decisions. Activity is checked for up to five repositories; others may be unchecked.</p>
    </div>}
  </section>;
}
