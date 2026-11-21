"use client";

import { useEffect, useMemo, useState } from "react";

type Task = {
  external_id: string;
  title: string;
  project_label: string | null;
  status: string;
  priority: string;
  presence_state: "unverified" | "present" | "not_returned";
  last_seen_snapshot: string | null;
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
type AgentActivity = {
  task_id: string;
  job_id: string;
  provider: string;
  mode: "mock" | "real";
  state: string;
  observed_at: string | null;
  updated_at: string;
};
type AgentEvent = {
  id: string;
  task_id: string;
  job_id: string;
  state: string;
  mode: "mock" | "real";
  observed_at: string;
  recorded_at: string;
  verification_method: "legacy_unknown" | "operator_reviewed" | "shared_key_hmac";
};
type Snapshot = {
  mode: "cached_inboxtend_tasks";
  items: Task[];
  agent_activities: AgentActivity[];
  agent_events: AgentEvent[];
  sync_state: string;
  last_checked_at: string | null;
  checked_count: number | null;
  last_error: string | null;
  freshness: { state: "never_synced" | "sync_failed_or_incomplete" | "invalid_timestamp" | "aged_over_24h" | "recent_cache"; age_hours: number | null };
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
  const [projectFilter, setProjectFilter] = useState("all");
  const [eventMode, setEventMode] = useState<"all" | "real" | "mock">("all");
  const [reviewOnly, setReviewOnly] = useState(false);
  const [includeNotReturned, setIncludeNotReturned] = useState(false);

  const activeTasks = useMemo(
    () => (snapshot?.items ?? []).filter(task => task.presence_state !== "not_returned"),
    [snapshot]
  );

  const projects = useMemo(() => {
    const summaries = new Map<string, { total: number; open: number; high: number }>();
    for (const task of activeTasks) {
      const name = task.project_label?.trim() || "Uncategorized";
      const counts = summaries.get(name) ?? { total: 0, open: 0, high: 0 };
      counts.total++;
      if (task.status !== "done") counts.open++;
      if (task.priority === "high" && task.status !== "done") counts.high++;
      summaries.set(name, counts);
    }
    return [...summaries].sort(([a], [b]) => a.localeCompare(b));
  }, [activeTasks]);

  const activityOverview = useMemo(() => {
    const tasks = activeTasks;
    const activities = snapshot?.agent_activities ?? [];
    const ids = new Set(tasks.map(task => task.external_id));
    const relevant = activities.filter(activity => ids.has(activity.task_id));
    const byTask = new Map(tasks.map(task => [task.external_id, task]));
    const recent = [...relevant].sort((a, b) => {
      const left = Date.parse(a.observed_at ?? a.updated_at);
      const right = Date.parse(b.observed_at ?? b.updated_at);
      return (Number.isFinite(right) ? right : 0) - (Number.isFinite(left) ? left : 0);
    }).slice(0, 12);
    const projects = new Map<string, { matched: number; real: number; mock: number }>();
    for (const activity of relevant) {
      const task = byTask.get(activity.task_id);
      if (!task) continue;
      const name = task.project_label?.trim() || "Uncategorized";
      const current = projects.get(name) ?? { matched: 0, real: 0, mock: 0 };
      current.matched++;
      if (activity.mode === "real") current.real++;
      if (activity.mode === "mock") current.mock++;
      projects.set(name, current);
    }
    return {
      recent,
      groups: [...projects].sort(([a], [b]) => a.localeCompare(b)),
      matched: relevant.length,
      withJobId: tasks.filter(task => task.executor === "agentsteers" && Boolean(task.agent_job_id)).length,
    };
  }, [snapshot, activeTasks]);

  const visibleEvents = useMemo(() => {
    const tasks = new Map((snapshot?.items ?? []).map(task => [task.external_id, task]));
    return (snapshot?.agent_events ?? []).filter(event => {
      const task = tasks.get(event.task_id);
      return Boolean(task) &&
        (projectFilter === "all" || (task?.project_label?.trim() || "Uncategorized") === projectFilter) &&
        (eventMode === "all" || event.mode === eventMode);
    }).slice(0, 15);
  }, [snapshot, projectFilter, eventMode]);

  const agentDiscrepancies = useMemo(() => {
    const activities = snapshot?.agent_activities ?? [];
    return activeTasks.flatMap(task => {
      if (task.executor !== "agentsteers" || !task.agent_job_id) return [];
      const matched = activities.find(activity =>
        activity.task_id === task.external_id && activity.job_id === task.agent_job_id);
      if (!matched) return [{ task, kind: "missing" as const, stored: null }];
      if (task.agent_status && task.agent_status.trim().toLowerCase() !== matched.state.trim().toLowerCase()) {
        return [{ task, kind: "different" as const, stored: matched }];
      }
      return [];
    });
  }, [snapshot, activeTasks]);

  const reviewIds = useMemo(() => new Set(agentDiscrepancies.map(item => item.task.external_id)), [agentDiscrepancies]);

  const filtered = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase();
    const rows = (snapshot?.items ?? []).filter(task =>
      (includeNotReturned || task.presence_state !== "not_returned") &&
      (!reviewOnly || reviewIds.has(task.external_id)) &&
      (statusFilter === "all" || task.status === statusFilter) &&
      (projectFilter === "all" || (task.project_label?.trim() || "Uncategorized") === projectFilter) &&
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
  }, [snapshot, statusFilter, agentFilter, sortBy, query, projectFilter, reviewOnly, reviewIds, includeNotReturned]);

  async function load() {
    setState("loading");
    setSnapshot(null);
    try {
      const response = await fetch("/api/inboxtend-tasks", { cache: "no-store" });
      const result: unknown = await response.json();
      if (!response.ok || !result || typeof result !== "object" ||
          !("mode" in result) || result.mode !== "cached_inboxtend_tasks" ||
          !("items" in result) || !Array.isArray(result.items) ||
          !("agent_events" in result) || !Array.isArray(result.agent_events) ||
          !("agent_activities" in result) || !Array.isArray(result.agent_activities)) throw new Error();
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
      <p role="status" className={`mt-2 text-sm ${snapshot.freshness?.state === "recent_cache" ? "text-slate-300" : "text-amber-200"}`}>
        Cache freshness: {snapshot.freshness?.state === "recent_cache" ? "last successful sync within 24 hours (not live)" :
          snapshot.freshness?.state === "aged_over_24h" ? "last successful sync more than 24 hours ago" :
          snapshot.freshness?.state === "never_synced" ? "never synchronized" :
          snapshot.freshness?.state === "sync_failed_or_incomplete" ? "latest sync was not successful" :
          "sync timestamp unavailable or invalid"}
        {typeof snapshot.freshness?.age_hours === "number" ? ` · ${snapshot.freshness.age_hours} hours ago` : ""}
      </p>
      {snapshot.sync_state !== "succeeded" && <p className="mt-2 text-sm text-amber-200">
        Cached data may be incomplete or stale. {snapshot.last_error ? "Latest sync: " + snapshot.last_error : ""}
      </p>}
      <section className="mt-4 rounded-xl border border-amber-200/20 p-4" aria-labelledby="agent-discrepancies-heading">
        <h3 id="agent-discrepancies-heading" className="text-sm font-semibold text-amber-100">
          Agent status reconciliation · {agentDiscrepancies.length} items need review
        </h3>
        <p className="mt-1 text-xs text-slate-300">
          Comparing cached task claims to separately stored job snapshots. Differences can reflect delays,
          different status vocabularies, or incomplete history; they do not prove an execution failure.
        </p>
        <label className="mt-3 flex items-center gap-2 text-xs text-slate-200">
          <input type="checkbox" checked={reviewOnly} onChange={event => setReviewOnly(event.target.checked)}
            className="accent-cyan-400" />
          Show only review items in the task list
        </label>
        {agentDiscrepancies.length === 0 ? <p className="mt-2 text-xs text-slate-400">
          No missing or differing matched AgentSteers snapshots among loaded tasks. This does not verify execution.
        </p> : <ul className="mt-3 space-y-2 text-xs">
          {agentDiscrepancies.slice(0, 10).map(({ task, kind, stored }) => <li
            key={task.external_id} className="rounded-lg border border-white/10 p-3">
            <strong className="block break-words text-white">{task.title}</strong>
            <span className="block text-amber-100">
              {kind === "missing" ? "No independently stored matching job" :
                `Task reports "${task.agent_status}"; stored job reports "${stored?.state}"`}
            </span>
            {stored && <span className="block text-slate-400">
              Stored observation: {stored.observed_at ?? "not recorded"}
            </span>}
          </li>)}
        </ul>}
        {agentDiscrepancies.length > 10 && <p className="mt-2 text-xs text-slate-400">
          Showing first 10 of {agentDiscrepancies.length} review items.
        </p>}
      </section>
      <p className="mt-3 text-xs text-slate-300">
        Presence in latest complete snapshot: {snapshot.items.filter(task => task.presence_state === "present").length} present ·
        {" "}{snapshot.items.filter(task => task.presence_state === "not_returned").length} not returned ·
        {" "}{snapshot.items.filter(task => task.presence_state === "unverified").length} legacy unverified.
        Not returned does not prove the source task was deleted.
      </p>
      <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4" aria-label="Cached task totals">
        {[
          { label: "New", count: activeTasks.filter(task => task.status === "new").length },
          { label: "In progress", count: snapshot.items.filter(task => task.status === "in_progress").length },
          { label: "Waiting", count: snapshot.items.filter(task => task.status === "waiting").length },
          { label: "Done", count: snapshot.items.filter(task => task.status === "done").length },
        ].map(item => <div key={item.label} className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
          <p className="text-xs text-slate-400">{item.label}</p>
          <p className="mt-1 text-xl font-semibold tabular-nums">{item.count}</p>
        </div>)}
      </div>
      <section className="mt-5 rounded-xl border border-white/10 p-4" aria-labelledby="agent-overview-title">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 id="agent-overview-title" className="text-sm font-semibold">AgentSteers stored activity overview</h3>
          <span className="text-xs text-slate-400">{activityOverview.matched} matched records · {activityOverview.withJobId} tasks reference a job</span>
        </div>
        <p className="mt-2 text-xs text-slate-400">Historical records matched by owner and job ID, not a live execution feed. A task job reference without a match is unverified.</p>
        {activityOverview.groups.length > 0 && <ul className="mt-3 grid gap-2 sm:grid-cols-2">
          {activityOverview.groups.map(([name, counts]) => <li key={name} className="rounded-lg border border-white/10 bg-white/[0.03] p-3 text-xs">
            <strong className="block break-words text-white">{name}</strong>
            <span className="mt-1 block text-slate-300">{counts.matched} matched · {counts.real} real · {counts.mock} mock</span>
          </li>)}
        </ul>}
        <div className="mt-4 flex flex-wrap items-center justify-between gap-2">
          <h4 className="text-xs font-semibold text-slate-200">Persisted event timeline</h4>
          <label className="text-xs text-slate-300">Execution mode
            <select value={eventMode} onChange={event => setEventMode(event.target.value as "all" | "real" | "mock")}
              className="ml-2 rounded-lg border border-white/20 bg-[#11182b] px-2 py-1 text-xs text-white">
              <option value="all">All modes</option><option value="real">Real</option><option value="mock">Mock</option>
            </select>
          </label>
        </div>
        <p className="mt-2 text-xs text-slate-400">
          Showing {visibleEvents.length} stored events (up to 15), using the selected project and execution mode.
        </p>
        {visibleEvents.length === 0 ? <p className="mt-2 text-xs text-slate-400">
          No persisted AgentSteers events match these filters. Status snapshots below are not a full timeline.
        </p> : <ol className="mt-2 space-y-2 border-l border-white/20 pl-4">
          {visibleEvents.map(event => {
            const task = snapshot.items.find(item => item.external_id === event.task_id);
            return <li key={event.id} className="relative rounded-lg border border-white/10 p-3 text-xs">
              <strong className="block text-white">{event.state} · {event.mode}</strong>
              <span className="block text-amber-200">Source check: {event.verification_method === "shared_key_hmac" ? "Shared-key signature (not AgentSteers-authenticated)" : event.verification_method === "operator_reviewed" ? "Operator-reviewed file" : "Unknown legacy origin"}</span>
              <span className="block text-slate-300">{task?.title ?? "Cached task"} · {task?.project_label || "Uncategorized"}</span>
              <span className="block text-slate-400">Observed {event.observed_at} · recorded {event.recorded_at}</span>
            </li>;
          })}
        </ol>}
        <h4 className="mt-4 text-xs font-semibold text-slate-200">Recently observed records</h4>
        {activityOverview.recent.length === 0 ? <p className="mt-2 text-xs text-slate-400">No matching stored AgentSteers records.</p> :
          <ol className="mt-2 space-y-2">
            {activityOverview.recent.map(activity => {
              const related = snapshot.items.find(task => task.external_id === activity.task_id);
              return <li key={activity.task_id + ":" + activity.job_id}
                className="flex flex-wrap justify-between gap-2 rounded-lg border border-white/10 p-3 text-xs">
                <div>
                  <strong className="block break-words text-slate-100">{related?.title ?? "Cached task"}</strong>
                  <span className="text-slate-300">{related?.project_label || "Uncategorized"} · {activity.state} · {activity.mode}</span>
                  <span className="block break-all text-slate-500">Job {activity.job_id}</span>
                </div>
                <span className="text-slate-400">Observed {activity.observed_at ?? "unknown"}</span>
              </li>;
            })}
          </ol>}
        <p className="mt-3 text-xs text-slate-500">One stored state per matched job, not a complete event history. No actions are available here.</p>
      </section>
      <div className="mt-5 rounded-xl border border-white/10 p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-sm font-semibold">Projects in this snapshot</h3>
          <span className="text-xs text-slate-400">{projects.length} project groups · cached only</span>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <button type="button" aria-pressed={projectFilter === "all"}
            onClick={() => setProjectFilter("all")}
            className={`rounded-lg border px-3 py-2 text-xs ${projectFilter === "all" ? "border-cyan-400 bg-cyan-400/10 text-cyan-200" : "border-white/20 text-slate-300"}`}>
            All projects · {activeTasks.length}
          </button>
          {projects.map(([name, counts]) => <button key={name} type="button"
            aria-pressed={projectFilter === name} onClick={() => setProjectFilter(name)}
            className={`rounded-lg border px-3 py-2 text-left text-xs ${projectFilter === name ? "border-cyan-400 bg-cyan-400/10 text-cyan-200" : "border-white/20 text-slate-300"}`}>
            <span className="font-medium">{name}</span>
            <span className="ml-2 opacity-80">{counts.open} open / {counts.total} total{counts.high > 0 ? ` · ${counts.high} high` : ""}</span>
          </button>)}
        </div>
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
      <label className="mt-3 flex items-center gap-2 text-xs text-slate-300">
        <input type="checkbox" checked={includeNotReturned}
          onChange={event => setIncludeNotReturned(event.target.checked)}
          className="accent-cyan-400" />
        Include tasks not returned by the latest complete sync
      </label>
      <p className="mt-3 text-xs text-slate-400" role="status">
        Showing {filtered.length} of {snapshot.items.length} cached tasks (up to the first 100 loaded).
        Filters and sorting affect only this local list, not all tasks in the source.
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
          {task.presence_state !== "present" && <p className="mt-2 text-xs text-amber-200">
            {task.presence_state === "not_returned" ? "Not returned by latest complete source snapshot" :
              "Presence not verified by a complete source snapshot"}
          </p>}
          <p className="mt-2 text-xs text-slate-300">
            {task.project_label ?? "Uncategorized"} · {task.priority} priority
            {task.due_at || task.due_date ? " · Due " + (task.due_at ?? task.due_date) : ""}
          </p>
          {(task.assigned_agent || task.agent_status) && <p className="mt-2 text-xs text-violet-200">
            Agent: {task.assigned_agent ?? "Unassigned"} · status: {task.agent_status ?? "unknown"}
          </p>}
          {(() => {
            const issue = agentDiscrepancies.find(item => item.task.external_id === task.external_id);
            return issue ? <p role="status" className="mt-2 text-xs text-amber-200">
              Needs review: {issue.kind === "missing" ? "No matching stored AgentSteers job" :
                `Task says "${task.agent_status}", stored job says "${issue.stored?.state}"`}
            </p> : null;
          })()}
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
            <p className="sm:col-span-2 text-amber-200">Task-reported Agent state: {task.agent_status ?? "not provided"} — source metadata, not independent execution proof.</p>
            <p>Due timezone: <span className="text-white">{task.due_timezone || "Not set"}</span></p>
            <p>Snapshot observed: <span className="text-white">{task.observed_at}</span></p>
            <p>Last seen in source snapshot: <span className="text-white">{task.last_seen_snapshot ?? "Not verified"}</span></p>
            <div className="sm:col-span-2 rounded-lg border border-white/10 p-3">
              <h4 className="font-semibold text-white">Persisted job events</h4>
              {(() => {
                const events = snapshot.agent_events.filter(event =>
                  event.task_id === task.external_id && event.job_id === task.agent_job_id);
                return events.length ? <ol className="mt-2 space-y-1">
                  {events.map(event => <li key={event.id}>
                    {event.observed_at} · {event.state} · {event.mode} · {event.verification_method.replaceAll("_", " ")}
                  </li>)}
                </ol> : <p className="mt-2 text-slate-400">No persisted job events.</p>;
              })()}
              <p className="mt-3 text-slate-400">Persisted events may be incomplete. A signed import proves only shared-key possession, not official AgentSteers origin.</p>
              <h4 className="mt-3 font-semibold text-white">Stored AgentSteers current activity</h4>
              {(() => {
                const matches = snapshot.agent_activities.filter(activity =>
                  activity.task_id === task.external_id && activity.job_id === task.agent_job_id);
                return matches.length ? <ul className="mt-2 space-y-2">
                  {matches.map(activity => <li key={activity.provider + ":" + activity.job_id}>
                    {activity.provider} · {activity.mode} · {activity.state}
                    <span className="block text-slate-400">Observed {activity.observed_at ?? "not recorded"} · updated {activity.updated_at}</span>
                  </li>)}
                </ul> : <p className="mt-2 text-slate-400">No matching stored activity. A job ID alone does not confirm execution.</p>;
              })()}
            </div>
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
