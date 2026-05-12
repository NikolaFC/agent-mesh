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
6. **Shared-Root Ready** — Multiple local terminals may write the same `.mesh/` root safely through CLI-level locking and atomic file replacement.
7. **Explicit Remote Sync** — Cross-device state sharing uses explicit `mesh state ...` Git commands, not hidden background network writes.

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

**Action values (canonical on disk):** `created`, `started`, `committed`, `repaired`, `validated`, `deployed`, `merged`, `closed`, `commented`, `blocked`, `unblocked`, `tested`, `reviewed`, `confirmed`, `updated`, `superseded`

The CLI accepts common semantic aliases at write/repair boundaries and stores the canonical value. For example, `completed`, `finished`, and `success` normalize to `validated`; `commit` normalizes to `committed`. `mesh doctor --fix-safe` also normalizes legacy task history aliases, including archived tasks.

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

### Memory vs Skill boundary
Agent Mesh shared knowledge follows the same boundary contract as the host agent system. It is a shared state layer, not a memory engine and not a skill system by itself.

| Mesh surface | Classification | Owns | Do not store here |
| --- | --- | --- | --- |
| `.mesh/pulse/*.json` | operational memory/status | who is active, current task, recent action, stale/blocking signal | reusable procedures, long explanations, canonical user preferences |
| `.mesh/tasks/{active,archived}/*.json` | operational memory/status | work item truth, status, verdict, evidence history | SOP bodies, prompt libraries, unrelated project facts |
| `.mesh/shared/context.md` | operational memory/status + thin index | project facts every agent should know, active constraints, links to thick references | command dumps, full runbooks, historical narratives, dynamic runtime snapshots |
| `.mesh/shared/status/*` | operational memory/status | mutable runtime truth, current routing state, live environment snapshots too thick/dynamic for context | long historical narratives, reusable SOP bodies |
| `.mesh/shared/decisions.md` | operational memory/status | append-only decisions and consequences | how-to steps unless they are part of the decision record |
| `.mesh/shared/blockers.md` | operational memory/status | current blockers, needed decisions, current evidence | troubleshooting playbooks or resolved-history dumps |
| `.mesh/shared/sop/*` | procedure/reference | repeatable workflow instructions, checklists, runbooks, reusable prompt snippets | one-off status, current blockers, raw task history |
| `.mesh/shared/evolution/*` | durable-learning inbox / evolution signal | identity, preference, SOP, memory, or skill-candidate deltas for selective absorption | canonical memory, executable skills, guaranteed-startup context |
| `.mesh/shared/historical/*` | historical evidence/reference | resolved/superseded blocker notes, archived state snapshots, evidence that should no longer bloat live context | current blockers, active status, reusable SOP bodies |
| `.mesh/*/index.jsonl` | reference/index | search acceleration and summaries | source-of-truth memory or skill content |

Routing rules:

1. Put facts, current truth, preferences, decisions, blockers, and what happened in operational memory/status surfaces.
2. Put repeatable how-to material in `.mesh/shared/sop/` or external docs/guides. If it has a trigger, goal, reusable steps, guardrails, and repeatable execution value, it may graduate to a skill candidate or host `skills/*/SKILL.md`.
3. Keep evolution logs as learning inbox/signal only. Agents may selectively absorb them into memory, docs, workflows, or skills, but must not treat an evolution entry as canonical memory or an executable skill by itself.
4. Do not turn every repeated fact into a skill. Repetition without a reusable procedure should stay as a signal/count or pressure on an existing skill.
5. Prefer thin mesh memory plus links to thick references. Avoid large rewrites of historical files; migrate mixed legacy content one file at a time.

`mesh validate` and `mesh doctor` may emit non-fatal boundary warnings when memory/status files accumulate obvious SOP material or SOP files look mostly like one-off state. Warnings are advisory and never auto-move content.

## Experimental Optional Layer: Mesh MCP

Agent Mesh core remains file-only. The optional `mesh mcp` surface is experimental and provides MCP/client tooling over the same local state. The first supported sharing pair is deliberately limited to OpenClaw ↔ Hermes (`openclaw` / `hermes`).

Experimental storage lives under `.mesh/mcp/`:

```text
.mesh/mcp/sessions/      # transcript descriptors
.mesh/mcp/requests/      # cross-agent read approval requests
.mesh/mcp/grants/        # allow-once / scoped allow-session grants
.mesh/mcp/servers.json   # downstream MCP server registry
.mesh/mcp/audit.jsonl    # access and proxy audit events
```

Cross-agent full transcript reads are allowed only after an explicit grant. Same-agent transcript reads do not need a cross-agent grant. `allow-once` grants are consumed after one read; `allow-session` grants are scoped to the requester, target session, and current session when provided. This experimental transcript/context surface rejects unsupported agents rather than becoming a general raw-session bus.

This layer is intentionally not part of the stable core protocol yet. See `docs/mesh-mcp-experimental-construction.md` for the current construction contract and division of labor with OpenClaw/Hermes MCP.

## Write Guarantees

The CLI serializes mutating operations with a local `.mesh/.lock` on POSIX platforms and writes files through same-directory temporary files followed by atomic replacement. This prevents partial JSON/Markdown writes and reduces lost-update risk when multiple terminals share one local mesh root.

For cross-device sharing, Agent Mesh intentionally does not run a server and does not auto-sync in the background. Use a dedicated private Git state repo and the `mesh state` commands:

```bash
mesh state configure --remote <git-url> [--branch main]
mesh state clone --remote <git-url> --target ~/agent-mesh-state
mesh state tailscale host-init --repo-path ~/agent-mesh-state.git --state-root ~/agent-mesh-state [--seed-from <project-root>]
mesh state tailscale join --host <tailnet-host> --repo-path </absolute/state.git> --target ~/agent-mesh-state
mesh state tailscale configure --host <tailnet-host> --repo-path </absolute/state.git>
mesh state tailscale clone --host <tailnet-host> --repo-path </absolute/state.git> --target ~/agent-mesh-state
mesh state sync   # commit local state, pull/rebase remote state, rebuild indexes, push
```

Recommended pattern: run `mesh state sync` before work and after meaningful pulse/task milestones. If Git reports a rebase conflict, resolve it explicitly; the CLI will not guess business truth.

## Migration Capsules

`mesh migrate` moves persona/rule/skill material across devices without copying the whole workspace. The host exports a capsule with a manifest, checksums, skipped-path list, and explicit approval metadata. Clients must inspect and dry-run before applying; `apply` writes only when `--write` is passed.

Default `openclaw-persona` scope:

- core startup/persona files: `AGENTS.md`, `SOUL.md`, `IDENTITY.md`, `USER.md`, `MEMORY.md`, `STARTUP_ONEPAGE.md`, `HEARTBEAT.md`, `TOOLS.md`
- optional stable `memory/` files via `--include-memory`, excluding raw/session/dream archives by default
- optional `skills/` and `agents/` trees via `--include-skills`
- default exclusions: `.env`, credentials, device pairing state, runtime state, logs, raw session/dream archives, key/cert files, `.git`, `.openclaw`, `node_modules`, backups, and caches

Migration capsules are for trusted host-to-client onboarding. They are not a secret manager, not a device pairing system, and not a substitute for reviewing scripts inside migrated skills.

## Remote QMD Retrieval

`mesh qmd remote-search` lets client devices query the canonical host's local QMD index over SSH/Tailscale. This avoids copying vector stores to every device and avoids running a long-lived public search server.

The command is intentionally read-only: it changes directory to the host workspace and invokes `scripts/qmd_search_fallback.py` with the supplied query, collection filters, result count, and JSON mode. Host, user, workspace, cache, and remote PATH prefix can be supplied with flags or `QMD_REMOTE_*` environment variables. The default remote PATH prefix includes `$HOME/.bun/bin` so non-interactive SSH can find Bun-installed `qmd` binaries.

## CLI Interface

```bash
# Root visibility
mesh root [--json]

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

# Cross-terminal / cross-device state sync
mesh state configure --remote <git-url> [--branch main]
mesh state clone --remote <git-url> --target <dir> [--branch main]
mesh state tailscale host-init [--repo-path <path>] [--state-root <dir>] [--seed-from <project-root>] [--host <host>] [--user <user>]
mesh state tailscale join --host <host> --repo-path <path> [--target <dir>] [--user <user>]
mesh state tailscale url --host <host> --repo-path <path> [--user <user>]
mesh state tailscale configure --host <host> --repo-path <path> [--user <user>]
mesh state tailscale clone --host <host> --repo-path <path> --target <dir> [--user <user>]
mesh state status [--json]
mesh state pull [--autocommit]
mesh state push [--message <text>]
mesh state sync [--message <text>]

# Host-approved migration capsules
mesh migrate plan --preset openclaw-persona [--root <dir>] [--include-memory] [--include-skills] [--json]
mesh migrate export --preset openclaw-persona --approved-by <host> --output <bundle.tar.gz> [--root <dir>] [--include-memory] [--include-skills]
mesh migrate inspect <bundle.tar.gz> [--json]
mesh migrate apply <bundle.tar.gz> --target-root <dir> [--write] [--no-backup]

# Remote QMD retrieval
mesh qmd remote-search <query> --host <host> --workspace <host-workspace> [--user <user>] [--remote-path <paths>] [--json] [-n <num>] [-c <collection>]

# Utilities
mesh init              # Initialize .mesh/ in current repo
mesh status            # Overview of all agents + active tasks
mesh sync              # Refresh pulse data from external sources (e.g., GitHub PRs)
mesh validate [--json] # Check schemas + advisory boundary warnings
mesh doctor [--fix-safe] [--json] # Safe mechanical hygiene repairs + advisory boundary warnings
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

Current Agent Mesh package version: `0.2.0`.

Use `mesh --version` to inspect the installed CLI version. See [`CHANGELOG.md`](CHANGELOG.md) for release notes.

This protocol follows SemVer:
- **v1.x**: Current specification
- Breaking changes bump major version
- New fields/features bump minor version
- Clarifications bump patch version

## License

MIT — Use freely, contribute back if it helps.
