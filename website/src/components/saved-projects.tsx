"use client";

import { useEffect, useState } from "react";

type Source = {
  provider: string;
  source_url: string | null;
  observed_at: string | null;
  last_success_at: string | null;
  stored_verification_state: string;
};
type SavedProject = {
  id: string;
  name: string;
  status: string;
  next_action: string | null;
  follow_up_at: string | null;
  blocker: string | null;
  updated_at: string;
  sources: Source[];
};
type Sync = {
  provider: string;
  account_key: string;
  sync_state: string;
  last_checked_at: string | null;
  cached_record_count: number;
  is_fully_verified: boolean;
};
type Overview = {
  mode: "saved_snapshot";
  project_count: number;
  sources_count: number;
  projects: SavedProject[];
  syncs: Sync[];
};
function safeLink(url: string | null): boolean {
  if (!url) return false;
  try {
    return new URL(url).protocol === "https:";
  } catch {
    return false;
  }
}
export default function SavedProjects() {
  const [state, setState] = useState<"loading" | "ready" | "unavailable">("loading");
  const [overview, setOverview] = useState<Overview | null>(null);
  const [message, setMessage] = useState("");
  async function load() {
    setState("loading");
    setOverview(null);
    try {
      const response = await fetch("/api/saved-projects", { cache: "no-store" });
      const data: unknown = await response.json();
      if (!response.ok || !data || typeof data !== "object" ||
          !("mode" in data) || data.mode !== "saved_snapshot" ||
          !("projects" in data) || !Array.isArray(data.projects) ||
          !("syncs" in data) || !Array.isArray(data.syncs)) {
        throw new Error("Saved storage is not available or has not been configured.");
      }
      setOverview(data as Overview);
      setState("ready");
    } catch {
      setMessage("Saved project storage is unavailable. The live GitHub check below remains separate.");
      setState("unavailable");
    }
  }
  useEffect(() => { void load(); }, []);
  return <section className="mt-10 rounded-2xl border border-white/15 bg-white/[0.04] p-6">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 className="text-xl font-semibold">Saved projects</h2>
        <p className="mt-1 text-sm text-slate-400">Historical SQLite snapshot — never labeled live</p>
      </div>
      <button type="button" onClick={() => void load()} disabled={state === "loading"}
        className="rounded-xl border border-white/30 px-4 py-2 text-sm disabled:opacity-50">
        {state === "loading" ? "Loading…" : "Reload saved data"}
      </button>
    </div>
    {state === "loading" && <p className="mt-5 text-slate-300">Reading saved project snapshot…</p>}
    {state === "unavailable" && <p role="status" className="mt-5 text-amber-200">{message}</p>}
    {state === "ready" && overview && <div className="mt-5 space-y-5">
      <p className="text-sm text-slate-300">{overview.project_count} saved projects · {overview.sources_count} source records</p>
      {overview.projects.length === 0 && <p className="text-slate-300">No projects have been saved for this account.</p>}
      <ul className="space-y-3">{overview.projects.map(project =>
        <li key={project.id} className="rounded-xl border border-white/10 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <strong>{project.name}</strong>
            <span className="text-xs text-slate-300">{project.status} · saved {project.updated_at}</span>
          </div>
          {project.next_action && <p className="mt-2 text-sm">Next: {project.next_action}</p>}
          {project.follow_up_at && <p className="mt-1 text-sm text-slate-300">Follow-up: {project.follow_up_at}</p>}
          {project.blocker && <p className="mt-1 text-sm text-amber-200">Blocked: {project.blocker}</p>}
          <ul className="mt-2 space-y-1 text-xs text-slate-400">{project.sources.map((source, i) =>
            <li key={i}>{safeLink(source.source_url) ?
              <a href={source.source_url!} target="_blank" rel="noopener noreferrer" className="underline">{source.provider} source</a> :
              <span>{source.provider} source</span>} · stored {source.stored_verification_state} · checked {source.last_success_at ?? "never"}</li>)}</ul>
        </li>)}</ul>
      <h3 className="font-semibold">Provider sync status</h3>
      {overview.syncs.length === 0 ?
        <p className="text-sm text-slate-300">No provider sync history is available. Saved records must not be assumed current.</p> :
        <ul className="space-y-2 text-sm">{overview.syncs.map(sync =>
          <li key={sync.provider + ":" + sync.account_key} className="rounded-lg border border-white/10 p-3">
            {sync.provider}: {sync.sync_state} · last checked {sync.last_checked_at ?? "never"} · {sync.cached_record_count} cached records
            {!sync.is_fully_verified && <span className="block text-amber-200">Not fully verified by the latest run</span>}
          </li>)}</ul>}
      <p className="text-xs text-slate-400">Reload reads SQLite; it does not contact GitHub, Gmail or Calendar. Use Check GitHub below for a separate on-demand request. Sync failures are not proof of zero activity.</p>
    </div>}
  </section>;
}
