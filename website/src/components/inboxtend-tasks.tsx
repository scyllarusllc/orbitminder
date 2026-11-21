"use client";

import { useEffect, useMemo, useState } from "react";

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
  review_state: string;
  executor: string | null;
  agent_job_id: string | null;
  due_timezone: string | null;
  observed_at: string;
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

const rank: Record<string, number> = { high: 0, medium: 1, low: 2 };
const taskStatuses = ["all", "new", "in_progress", "waiting", "done"] as const;
type TaskStatusFilter = typeof taskStatuses[number];
type AgentFilter = "all" | "assigned" | "unassigned";

export default function InboxtendTasks() {
  const [state, setState] = useState<"loading" | "ready" | "unavailable">("loading");
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [statusFilter, setStatusFilter] = useState<TaskStatusFilter>("all");
  const [agentFilter, setAgentFilter] = useState<AgentFilter>("all");
  const [sortBy, setSortBy] = useState<"priority" | "due" | "updated">("priority");
  const [query, setQuery] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const filtered = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase();
    const rows = (snapshot?.items ?? []).filter(task =>
      (statusFilter === "all" || task.status === statusFilter) &&
      (agentFilter === "all" || (agentFilter === "assigned"
        ? Boolean(task.assigned_agent) : !task.assigned_agent)) &&
      (!needle || task.title.toLocaleLowerCase().includes(needle) ||
        (task.project_label ?? "").toLocaleLowerCase().includes(needle))
    );
    const byDue = (task: Task) => {
      const value = task.due_at ?? task.due_date;
      if (!value) return Number.POSITIVE_INFINITY;
      const time = Date.parse(value);
      return Number.isNaN(time) ? Number.POSITIVE_INFINITY : time;
    };
    return [...rows].sort((a, b) => {
      if (sortBy === "priority") {
        const p = (rank[a.priority] ?? 3) - (rank[b.priority] ?? 3);
        if (p !== 0) return p;
      }
      if (sortBy === "due" || sortBy === "priority") {
        const d = byDue(a) - byDue(b);
        if (!Number.isNaN(d) && d !== 0) return d;
      }
      const newer = Date.parse(b.source_updated_at) - Date.parse(a.source_updated_at);
      if (!Number.isNaN(newer) && newer !== 0) return newer;
      return a.external_id.localeCompare(b.external_id);
    });
  }, [snapshot, statusFilter, agentFilter, sortBy, query]);

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
      <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4" aria-label="Cached task totals">
        {[
          { label: "New", count: snapshot.items.filter(task => task.status === "new").length },
          { label: "In progress", count: snapshot.items.filter(task => task.status === "in_progress").length },
          { label: "Waiting", count: snapshot.items.filter(task => task.status === "waiting").length },
          { label: "Done", count: snapshot.items.filter(task => task.status === "done").length },
        ].map(item => <div key={item.label} className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
          <p className="text-xs text-slate-400">{item.label}</p>
          <p className="mt-1 text-xl font-semibold tabular-nums">{item.count}</p>
        </div>)}
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4" aria-label="Task filters">
        <label className="text-xs text-slate-300">Search tasks
          <input aria-label="Search tasks" value={query} onChange={e => setQuery(e.target.value)}
            placeholder="Title or project" className="mt-1 block w-full rounded-lg border border-white/20 bg-[#11182b] px-3 py-2 text-sm text-white" />
        </label>
        <label className="text-xs text-slate-300">Task status
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value as TaskStatusFilter)}
            className="mt-1 block w-full rounded-lg border border-white/20 bg-[#11182b] px-3 py-2 text-sm text-white">
            {taskStatuses.map(v => <option key={v} value={v}>{v === "all" ? "All statuses" : v.replaceAll("_", " ")}</option>)}
          </select>
        </label>
        <label className="text-xs text-slate-300">Agent assignment
          <select value={agentFilter} onChange={e => setAgentFilter(e.target.value as AgentFilter)}
            className="mt-1 block w-full rounded-lg border border-white/20 bg-[#11182b] px-3 py-2 text-sm text-white">
            <option value="all">All tasks</option><option value="assigned">Assigned</option><option value="unassigned">Unassigned</option>
          </select>
        </label>
        <label className="text-xs text-slate-300">Sort by
          <select value={sortBy} onChange={e => setSortBy(e.target.value as "priority" | "due" | "updated")}
            className="mt-1 block w-full rounded-lg border border-white/20 bg-[#11182b] px-3 py-2 text-sm text-white">
            <option value="priority">Priority, then due date</option><option value="due">Earliest due date</option>
            <option value="updated">Recently updated</option>
          </select>
        </label>
      </div>
      <p className="mt-3 text-xs text-slate-400" role="status">
        Showing {filtered.length} of {snapshot.items.length} cached tasks (up to the first 100 loaded).
        Filters and sorting affect only this local list.
      </p>
      {snapshot.items.length > 0 && filtered.length === 0 && <p className="mt-4 text-sm text-slate-300">
        No cached tasks match these filters.
      </p>}
      {snapshot.items.length === 0 && <p className="mt-4 text-sm text-slate-300">
        No cached tasks for this account. No live source check was performed.
      </p>}
      <ul className="mt-4 space-y-3">
        {filtered.map(task => <li key={task.external_id} className="rounded-xl border border-white/10 p-4">
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
          <button type="button"
            aria-expanded={expandedId === task.external_id}
            aria-controls={`task-detail-${task.external_id}`}
            onClick={() => setExpandedId(current => current === task.external_id ? null : task.external_id)}
            className="mt-3 rounded-lg border border-white/20 px-3 py-1.5 text-xs hover:border-white/40">
            {expandedId === task.external_id ? "Hide details" : "View details"}
          </button>
          {expandedId === task.external_id && <div id={`task-detail-${task.external_id}`}
            className="mt-3 grid gap-2 rounded-xl border border-white/10 bg-black/20 p-3 text-xs text-slate-300 sm:grid-cols-2">
            <p>Task ID: <span className="break-all text-white">{task.external_id}</span></p>
            <p>Review: <span className="text-white">{task.review_state || "Unknown"}</span></p>
            <p>Executor: <span className="text-white">{task.executor || "None"}</span></p>
            <p>Agent job: <span className="break-all text-white">{task.agent_job_id || "None"}</span></p>
            <p>Due timezone: <span className="text-white">{task.due_timezone || "Not set"}</span></p>
            <p>Snapshot observed: <span className="text-white">{task.observed_at}</span></p>
            <p className="sm:col-span-2 text-slate-400">Metadata only. This view cannot approve, reassign, or execute work.</p>
          </div>}
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
