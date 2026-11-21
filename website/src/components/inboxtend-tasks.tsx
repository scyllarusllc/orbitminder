"use client";

import { useEffect, useState } from "react";

type Task = {
  external_id: string;
  title: string;
  project_label: string | null;
  status: string;
  priority: string;
  due_at: string | null;
  due_date: string | null;
  source_url: string | null;
  agent_status: string | null;
  assigned_agent: string | null;
  source_updated_at: string;
  revision: number;
};
type Snapshot = {
  mode: "cached_inboxtend_tasks";
  items: Task[];
  sync_state: string;
  last_checked_at: string | null;
  checked_count: number | null;
  last_error: string | null;
  count: number;
};
function safeHttpsLink(value: string | null): boolean {
  if (!value) return false;
  try { return new URL(value).protocol === "https:"; } catch { return false; }
}

export default function InboxtendTasks() {
  const [state, setState] = useState<"loading" | "ready" | "unavailable">("loading");
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);

  async function load() {
    setState("loading");
    setSnapshot(null);
    try {
      const response = await fetch("/api/inboxtend-tasks", { cache: "no-store" });
      const result: unknown = await response.json();
      if (!response.ok || !result || typeof result !== "object" ||
          !("mode" in result) || result.mode !== "cached_inboxtend_tasks" ||
          !("items" in result) || !Array.isArray(result.items)) throw new Error();
      setSnapshot(result as Snapshot);
      setState("ready");
    } catch { setState("unavailable"); }
  }

  useEffect(() => { void load(); }, []);

  return <section className="mt-10 rounded-2xl border border-white/15 bg-white/[0.04] p-6">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 className="text-xl font-semibold">Inboxtend tasks</h2>
        <p className="mt-1 text-sm text-slate-400">Stored task snapshot · read-only · not live</p>
      </div>
      <button type="button" disabled={state === "loading"} onClick={() => void load()}
        className="rounded-xl border border-white/30 px-4 py-2 text-sm disabled:opacity-50">
        {state === "loading" ? "Loading…" : "Reload saved tasks"}
      </button>
    </div>
    {state === "loading" && <p className="mt-5 text-sm text-slate-300">Reading saved task snapshot…</p>}
    {state === "unavailable" && <p role="status" className="mt-5 text-sm text-amber-200">
      Task storage is not configured or available. This is not evidence of zero tasks.
    </p>}
    {state === "ready" && snapshot && <div className="mt-5">
      <p className="text-sm text-slate-300">
        {snapshot.count} cached tasks · last sync: {snapshot.sync_state} · last checked: {snapshot.last_checked_at ?? "never"}
        {snapshot.checked_count !== null ? " · records checked: " + snapshot.checked_count : ""}
      </p>
      {snapshot.sync_state !== "succeeded" && <p className="mt-2 text-sm text-amber-200">
        Cached data may be incomplete or stale. {snapshot.last_error ? "Latest sync: " + snapshot.last_error : ""}
      </p>}
      {snapshot.items.length === 0 && <p className="mt-4 text-sm text-slate-300">
        No cached tasks for this account. No live source check was performed.
      </p>}
      <ul className="mt-4 space-y-3">
        {snapshot.items.map(task => <li key={task.external_id} className="rounded-xl border border-white/10 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <strong className="break-words">{task.title}</strong>
            <span className="rounded-full border border-white/20 px-2.5 py-1 text-xs text-slate-200">{task.status}</span>
          </div>
          <p className="mt-2 text-xs text-slate-300">
            {task.project_label ?? "Uncategorized"} · {task.priority} priority
            {task.due_at || task.due_date ? " · Due " + (task.due_at ?? task.due_date) : ""}
          </p>
          {(task.assigned_agent || task.agent_status) && <p className="mt-2 text-xs text-violet-200">
            Agent: {task.assigned_agent ?? "Unassigned"} · status: {task.agent_status ?? "unknown"}
          </p>}
          <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400">
            <span>Source updated {task.source_updated_at} · rev {task.revision}</span>
            {safeHttpsLink(task.source_url) && <a href={task.source_url!} target="_blank"
              rel="noopener noreferrer" className="text-cyan-300 underline">Open in Inboxtend</a>}
          </div>
        </li>)}
      </ul>
      <p className="mt-4 text-xs text-slate-400">
        Reload reads the local cache only. It does not sync email or dispatch an Agent.
      </p>
    </div>}
  </section>;
}
