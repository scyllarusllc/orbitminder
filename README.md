# OrbitMinder

**Your projects. Always in sight.**

OrbitMinder is an open-source, personal AI project command center. Its goal is to consolidate projects, follow-ups, deadlines and delegated agent work into one daily view.

**Status:** initial prototype. The current CLI produces a daily brief from a local example JSON file. GitHub/Gmail live connectors, web dashboard and autonomous agents are not yet implemented.

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

The brief is deterministic sample output, **not** a live sync. The existing ChatGPT "Mission Control" daily automation is separate and remains unchanged.

## MVP scope

- Canonical project and follow-up records, with source URLs and verification timestamps.
- Read-only GitHub and Gmail adapters, eventually calendar; clear distinction between fresh source data and manually tracked tasks.
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

Maintained by Scyllarus LLC. Proposed website: orbitminder.com (domain ownership/deployment not verified in this repository).
