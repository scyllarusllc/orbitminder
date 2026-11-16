"""Deterministic project summary; source adapters provide verification data."""
from datetime import date


def build_brief(projects, today=None):
    today = today or date.today()
    priorities, waiting, blocked, due, unverified, activity = [], [], [], [], [], []
    for project in projects:
        name = project["name"]
        status = project.get("status", "unknown")
        action = project.get("next_action", "")
        source_status = project.get("source_status", "unverified")
        if source_status != "verified":
            unverified.append(name)
        deadline = date.fromisoformat(project["follow_up_date"]) if project.get("follow_up_date") else None
        if deadline and deadline <= today:
            due.append(name)
        if status == "waiting":
            waiting.append(name)
        if status == "blocked":
            blocked.append(name)
        if "activity" in project:
            activity.append((name, project["activity"], project.get("source_url", "")))
        if action and status != "done":
            score = (100 if deadline and deadline <= today else 0) + int(project.get("priority", 0))
            priorities.append((score, name, action))
    priorities.sort(key=lambda item: (-item[0], item[1]))
    return {"date": today.isoformat(), "top_three": priorities[:3],
            "waiting": waiting, "blocked": blocked, "due": due,
            "unverified": unverified, "activity": activity,
            "project_count": len(projects)}


def format_brief(report):
    lines = [f"# OrbitMinder Daily Brief — {report['date']}",
             f"Projects: {report['project_count']}", "", "## Today's three priorities"]
    for index, (_, name, action) in enumerate(report["top_three"], 1):
        lines.append(f"{index}. {name}: {action}")
    if not report["top_three"]:
        lines.append("No active actions recorded.")
    for key, title in [("waiting", "Waiting"), ("blocked", "Blocked"), ("due", "Follow-ups due"),
                       ("unverified", "Not live-verified")]:
        lines.extend(["", f"## {title}", ", ".join(report[key]) if report[key] else "None recorded."])
    if report.get("activity"):
        lines.extend(["", "## GitHub activity (read-only)"])
        for name, stats, url in report["activity"]:
            lines.append(
                f"- {name}: {stats['commits_last_n_days']} commits in "
                f"{stats['window_days']} days; {stats['open_pull_requests']} open PRs; "
                f"{stats['open_issues']} open issues ({url})")
        lines.append("Counts may be lower bounds when GitHub returns a full page of 100.")
        lines.append("Other repositories have not been activity-checked.")
    return "\n".join(lines) + "\n"
