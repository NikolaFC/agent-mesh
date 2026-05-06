# Agent Mesh Protocol v1

> A lightweight, file-based protocol for multi-agent collaboration.
> Any AI coding agent that can read/write files can participate.

## Overview

Agent Mesh solves one problem: **AI agents can't see each other's work.**

When you use OpenClaw + Codex + Claude Code on the same project, each agent has its own isolated context. There's no standard way to share progress, decisions, or blockers. You become the human message bus.

Agent Mesh replaces that with a **shared folder + structured files** that any agent can read and write.

## Design Principles

1. **File-as-API** — No runtime server. The repo IS the API.
2. **Zero Dependencies** — Any agent that reads/writes files can participate.
3. **Git-Native** — Version history, diff, merge, and collaboration come free.
4. **Convention over Configuration** — Fixed paths, simple schemas, predictable behavior.
5. **Append-Friendly** — History is preserved, not overwritten.

## Directory Structure

```
.mesh/
├── pulse/                    # Real-time agent heartbeats
│   ├── {agent-name}.json     # One file per agent
│   └── ...
│
├── tasks/                    # Work item tracking
│   ├── active/               # In-progress tasks
│   │   ├── {task-id}.json
│   │   └── ...
│   └── archived/             # Completed tasks (optional)
│       └── ...
│
└── shared/                   # Persistent shared knowledge
    ├── context.md            # Project context any agent should know
    ├── decisions.md          # Architecture Decision Records (append-only)
    └── blockers.md           # Current blockers requiring human input
```

## Layer 1: Pulse (Agent Heartbeat)

Each agent maintains a pulse file at `.mesh/pulse/{agent-name}.json`.

**Rules:**
- Each agent ONLY writes its own pulse file (no cross-writing)
- Update on every significant state change
- Pulse files are small (< 1KB) by design

**Schema:** See `schema/pulse-v1.json`

**Example:**
```json
{
  "schema": "agent-mesh/pulse/v1",
  "agent": "hermes",
  "agentType": "codex",
  "lastUpdate": "2026-05-05T11:30:00Z",
  "status": "working",
  "currentTask": {
    "id": "pr-77540",
    "title": "cache session/node/cron list lookups",
    "progress": 0.9
  },
  "recentActions": [
    {
      "type": "commit",
      "ref": "493fe186",
      "summary": "cherry-pick cache commits onto latest main",
      "at": "2026-05-05T10:00:00Z"
    }
  ],
  "blockers": [],
  "nextActions": ["wait for maintainer review"]
}
```

**Status values:**
- `idle` — Not currently working on anything
- `working` — Actively executing a task
- `blocked` — Waiting on external input or dependency
- `reviewing` — Reviewing code or results
- `done` — Completed current task, awaiting new assignment

## Layer 2: Tasks (Work Items)

Each task gets a JSON file in `.mesh/tasks/active/{task-id}.json`.

**Rules:**
- Task ID should be URL-safe (e.g., `pr-77540`, `feat-auth-v2`, `bugfix-login`)
- The `assignedTo` agent owns write access
- Other agents can read and add comments via `history`
- Completed tasks move to `.mesh/tasks/archived/`

**Schema:** See `schema/task-v1.json`

**Example:**
```json
{
  "schema": "agent-mesh/task/v1",
  "id": "pr-77540",
  "type": "upstream-pr",
  "title": "perf(gateway): cache session, node, and cron list lookups",
  "status": "open",
  "verdict": "ADOPT",
  "priority": "high",
  "assignedTo": "hermes",
  "createdAt": "2026-05-04T20:00:00Z",
  "updatedAt": "2026-05-05T11:00:00Z",
  "progress": 0.9,
  "links": {
    "github": "https://github.com/openclaw/openclaw/pull/77540",
    "stateFile": "docs/status/openclaw-upstream-short-handoff-20260504.md"
  },
  "history": [
    {
      "agent": "hermes",
      "action": "created",
      "summary": "Initial PR creation",
      "at": "2026-05-04T20:00:00Z"
    },
    {
      "agent": "hermes",
      "action": "repaired",
      "summary": "Resolved merge conflict on latest main",
      "at": "2026-05-05T09:00:00Z"
    },
    {
      "agent": "openclaw",
      "action": "validated",
      "summary": "Production runtime patch verified",
      "at": "2026-05-05T11:00:00Z"
    }
  ]
}
```

**Task types:** `upstream-pr`, `feature`, `bugfix`, `investigation`, `refactor`, `docs`, `ops`

**Verdict values:** `ADOPT`, `REPAIR`, `CLOSE`, `pending`

**Action values:** `created`, `started`, `committed`, `repaired`, `validated`, `deployed`, `merged`, `closed`, `commented`, `blocked`, `unblocked`

## Layer 3: Shared Knowledge

Persistent files in `.mesh/shared/` that any agent should read before starting work.

### context.md
Project overview, architecture, key constraints. Updated by any agent when context changes.

### decisions.md (Append-Only)
Architecture Decision Records. New entries append to the top. Never modify existing entries.

**Format:**
```markdown
## [2026-05-05] Decision: Cache strategy for gateway RPCs

**Decided by:** openclaw
**Context:** sessions.list and node.list had p99 > 8s under load
**Decision:** Add TTL + in-flight dedupe caches with invalidation on mutation
**Consequences:** #77540 adds 3 cache modules, cron.list cache follows same pattern
```

### blockers.md
Current blockers requiring human decision. Updated as blockers are added/resolved.

## CLI Interface

```bash
# Pulse operations
mesh pulse update --agent <name> --status <status> [--task <id>] [--summary <text>]
mesh pulse touch --agent <name> [--summary <text>]  # Freshness only; keep task/status
mesh pulse read [--agent <name>] [--all]
mesh pulse check [--strict] [--json] [--stale-minutes <n>]

# Task operations
mesh task create --id <id> --title <title> --type <type> [--assign <agent>]
mesh task update --id <id> [--status <s>] [--verdict <v>] [--progress <0-1>]
mesh task history --id <id> --action <action> --summary <text> [--agent <name>]
mesh task list [--status <s>] [--agent <a>] [--type <t>]
mesh task archive --id <id>

# Shared knowledge
mesh shared read <file>
mesh shared append <file> --content <text>
mesh shared update <file> --content <text>  # Replace content

# Utilities
mesh init              # Initialize .mesh/ in current repo
mesh status            # Overview of all agents + active tasks
mesh sync              # Refresh pulse data from external sources (e.g., GitHub PRs)
mesh validate [--json] # Check all files against schemas
mesh doctor [--fix-safe] [--json] # Safe mechanical hygiene repairs
```

## Integration Patterns

Before wiring a new runtime, read the first-install runbook: [`docs/runbooks/agent-first-install.md`](docs/runbooks/agent-first-install.md). Agent Mesh core does not automatically modify an agent's prompt, heartbeat, cron, scheduler, or alert delivery; those are host-side responsibilities.

### Pattern 1: Agent Prompt Embedding
Add to any agent's system prompt:
```
Before starting work, read .mesh/pulse/*.json and .mesh/tasks/active/*.json.
After completing significant work, update your pulse file and task history.
```

### Pattern 2: Git Hook
A post-commit hook can auto-update pulse files:
```bash
#!/bin/bash
mesh pulse update --agent $(whoami) --status working --summary "committed $(git rev-parse --short HEAD)"
```

### Pattern 3: CI/CD Integration
GitHub Actions can update task status on PR events:
```yaml
- name: Update task on CI pass
  run: mesh task update --id pr-${{ github.event.pull_request.number }} --status ci-passed
```

### Pattern 4: Cron Sync
Periodic sync from external sources:
```bash
mesh sync --source github --repo owner/repo  # Update PR statuses
```

## Conflict Resolution

- **Pulse files:** No conflicts (each agent writes its own)
- **Task files:** Single-writer per task (assignedTo agent). Others append to history only.
- **Shared files:** Append-only for decisions.md. context.md and blockers.md use last-write-wins with git history as backup.

## Versioning

This protocol follows SemVer:
- **v1.x**: Current specification
- Breaking changes bump major version
- New fields/features bump minor version
- Clarifications bump patch version

## License

MIT — Use freely, contribute back if it helps.
