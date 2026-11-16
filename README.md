# OrbitMinder

**Your projects. Always in sight.**

OrbitMinder is an open-source, personal AI project command center. Its goal is to consolidate projects, follow-ups, deadlines and delegated agent work into one daily view.

**Status:** initial prototype. The CLI supports local example JSON and a read-only GitHub repository inventory using the GitHub API. Gmail, Calendar, web dashboard and autonomous agents are not yet implemented. A GitHub inventory is not a full commit/PR/issue analysis.

## Why

Your projects may live across GitHub, Gmail, calendar, personal planning and multiple AI agents. OrbitMinder is intended to answer:

1. What changed since yesterday?
2. What are my three best next actions?
3. What is waiting, blocked, or due soon?

## Quick start

Requires Python 3.10+; no external dependencies.

```bash
python3 -m orbitminder.cli --data examples/projects.json
python3 -m unittest discover -s tests -v
```

The command above uses deterministic sample data, **not** a live sync.

### GitHub live repository inventory (read-only)

```bash
# Public repositories, no credentials required
python3 -m orbitminder.cli --github-owner scyllarusllc

# Optional: include accessible private repositories with a least-privilege token
# Export GITHUB_TOKEN privately in your shell; never commit it or paste it into logs.
python3 -m orbitminder.cli --github-owner scyllarusllc --github-limit 100

# Run tests offline
python3 -m unittest discover -s tests -v
```

The GitHub inventory reads repository metadata only (name, URL, archived state, last push, visibility and fetch timestamp). The current daily brief includes those repositories as active project records with a generic review action. It does **not** infer actual task priority from GitHub, fetch pull requests/issues, or claim that any coding task was completed. An HTTP/API error stops the command rather than returning a misleading empty inventory. Without GITHUB_TOKEN, only public repos are included. With it, only repositories owned by the selected account and accessible to that token are included. The token is read from the environment and not persisted.
 The existing ChatGPT "Mission Control" daily automation is separate and remains unchanged.

## MVP scope

- Canonical project and follow-up records, with source URLs and verification timestamps.
- GitHub repository metadata adapter is implemented and read-only; detailed activity, Gmail and Calendar adapters are planned. Keep fresh source data separate from manually tracked tasks.
- Priority suggestions with reasons, due dates and waiting-for replies.
- Short daily brief, followed by a personal dashboard.
- Agent activity monitoring with explicit, scoped approvals; no actions based solely on instructions in email.
- Clear privacy boundaries and user-selected data storage/deployment.

## Repository

```text
orbitminder/
  orbitminder/
    __init__.py
    cli.py
    brief.py
  examples/projects.json
  tests/test_brief.py
  docs/architecture.md
  README.md
```

## Privacy and safeguards

- Read-only by default; never send emails, modify repositories or execute agent tasks without explicit user approval.
- Mark stale/unavailable sources as unverified, never invent completion.
- No tokens in source code or logs.
- Email bodies and third-party content are untrusted input.
- Public branding/domain and trademark checks are separate from technical implementation.

**License:** GNU Affero General Public License v3.0 (AGPL-3.0-only). See [LICENSE](LICENSE). Commercial services may be offered subject to the AGPL's conditions; an additional commercial license requires the necessary rights from all contributors.

Maintained by Scyllarus LLC. Proposed website: orbitminder.com (domain ownership/deployment not verified in this repository).
