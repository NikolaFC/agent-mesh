# Agent Mesh

**A lightweight protocol for multi-agent collaboration.**

Current version: **0.3.0**. See [`CHANGELOG.md`](CHANGELOG.md).

> When you use OpenClaw + Codex + Claude Code on the same project, each agent is an island. Agent Mesh is the bridge.

[中文文档](README.zh-CN.md)

## The Problem

You have multiple AI agents working on your codebase:
- **OpenClaw** orchestrating and managing memory
- **Hermes** implementing features, fixing bugs, and handling PRs
- **Claude Code** reviewing and refactoring
- **Cursor** in your editor

Each one has its own context window. They can't see each other's progress. You spend more time copying context between agents than actually getting work done.

### How it started

This project was born from a real pain point: our setup uses two independent agent systems — **OpenClaw** and **Hermes** — running in parallel on the same machine (WSL). Each has its own gateway, its own session management, and its own memory, but they share the same workspace and coordinate on the same PRs.

Hermes handles upstream PR implementation while OpenClaw manages orchestration and memory. Before Agent Mesh, every time Hermes finished a chunk of work, it would write a 22KB handoff document. OpenClaw had to parse that document, cross-reference with `gh pr view`, and manually piece together the current state. When the user asked "How is it going?", OpenClaw had to do this dance every single time.

Agent Mesh replaces all of that with `mesh status`.

## The Solution

Agent Mesh is a **file-based shared state layer**. Any agent that can read/write files can participate. No servers, no APIs, no dependencies.

```
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ OpenClaw │  │  Codex   │  │  Claude  │  │  Cursor  │
└────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
     │             │             │             │
     └─────────────┴─────────────┴─────────────┘
                         │
                  ┌──────┴──────┐
                  │  .mesh/     │  ← Shared state in your repo
                  └─────────────┘
```

## Quick Start

```bash
# 1. Initialize in your project
mesh init

# 2. Read the first-install runbook for agent-side wiring:
#    docs/runbooks/agent-first-install.md

# 3. Add to any agent's prompt:
#    "Before starting, read .mesh/pulse/*.json and .mesh/tasks/active/*.json.
#     After completing work, update your pulse and task history."

# 4. That's it. Agents now share state.
```

**Important:** Agent Mesh core only provides the shared state layer. Each agent must still wire Mesh into its own startup prompt, heartbeat/watchdog, task lifecycle, and alert delivery. See the required first-install runbook: [`docs/runbooks/agent-first-install.md`](docs/runbooks/agent-first-install.md).

## Cross-terminal / cross-device Mesh

Agent Mesh can be shared across WSL, macOS terminals, OpenClaw, Hermes, Claude Code, Codex, and other file-capable agents.

For multiple terminals on the same machine or mounted workspace, point every runtime at the same root:

```bash
export MESH_ROOT=/path/to/shared/mesh-root
mesh root
mesh status
```

For WSL ↔ Mac or other cross-device setups, use a **private Git state repo** as an explicit backend. This keeps the file API as the source of truth while avoiding a server/daemon:

```bash
# First machine, e.g. WSL
mkdir -p ~/agent-mesh-state
cd ~/agent-mesh-state
mesh init
mesh state configure --remote git@github.com:<you>/<private-mesh-state>.git
mesh state push --message "initial mesh state"

# Second machine, e.g. Mac
mesh state clone --remote git@github.com:<you>/<private-mesh-state>.git --target ~/agent-mesh-state
export MESH_ROOT=~/agent-mesh-state
mesh state sync
```

For a fully private tailnet path, pick **one canonical Tailscale SSH host** (usually the always-on machine running the main agents), then let every other device join it:

```bash
# On the canonical host, e.g. WSL:
mesh state tailscale host-init \
  --repo-path ~/agent-mesh-state.git \
  --state-root ~/agent-mesh-state \
  --seed-from /path/to/current/project \
  --host desktop-564viur-1.tail715c1b.ts.net \
  --user nikolafc

# On a client device, e.g. Mac:
mesh state tailscale join \
  --host desktop-564viur-1.tail715c1b.ts.net \
  --user nikolafc \
  --repo-path /home/nikolafc/agent-mesh-state.git \
  --target ~/agent-mesh-state
export MESH_ROOT=~/agent-mesh-state
```

`host-init` creates/uses the local bare repo and working state root; `join` refuses to overwrite a non-empty target so accidental Mac-local host state is not lost.

Recommended agent loop:

```bash
mesh state sync                       # before work: pull/rebase remote state
mesh pulse update --agent mac-agent --status working --summary "started"
# ...work...
mesh state sync --message "mac-agent pulse/task update"  # after milestones
```

Safety notes:
- Use a dedicated private state repo; do not point `mesh state configure` at a normal project repo unless you pass `--allow-project-repo` deliberately.
- State sync is explicit, not hidden auto-sync. If Git reports a rebase conflict, resolve it like any normal Git conflict.
- Mesh mutations use a local `.mesh/.lock` and atomic file replacement on POSIX platforms so multi-terminal writes on the same machine are safer.

## Host-approved persona / skill migration

Agent Mesh can package a host-approved migration capsule for OpenClaw-style persona and rule files. This is intentionally not a blind workspace sync.

```bash
# On the canonical host: review the plan
mesh migrate plan --preset openclaw-persona --root /path/to/openclaw-workspace --include-skills

# Export a host-approved capsule
mesh migrate export \
  --preset openclaw-persona \
  --root /path/to/openclaw-workspace \
  --include-skills \
  --approved-by wsl-host \
  --output /tmp/openclaw-persona.tar.gz

# On the client: inspect, dry-run, then write
mesh migrate inspect /tmp/openclaw-persona.tar.gz
mesh migrate apply /tmp/openclaw-persona.tar.gz --target-root ~/openclaw-workspace
mesh migrate apply /tmp/openclaw-persona.tar.gz --target-root ~/openclaw-workspace --write
```

The `openclaw-persona` preset includes core startup/persona files such as `AGENTS.md`, `SOUL.md`, `IDENTITY.md`, `USER.md`, `MEMORY.md`, and optional `skills/` + `agents/` content. It excludes secrets, credentials, device pairing state, `.env`, logs, runtime state, and common key/cert files by default. `apply` is dry-run unless `--write` is passed and backs up overwritten files under `.mesh/migrate/backups/`.

## What Gets Shared

### 📡 Pulse — Real-time heartbeats
Each agent has a pulse file (`.mesh/pulse/{agent}.json`) showing what they're doing right now.

```bash
mesh pulse read --all          # See all agents
mesh pulse update --agent codex --status working --task pr-77540
```

### 📋 Tasks — Work items
Track PRs, features, bugs with full history. One agent owns each task, others can observe.

```bash
mesh task list                          # All active tasks
mesh task create --id pr-77540 --title "cache lookups" --type upstream-pr --assign hermes
mesh task update --id pr-77540 --verdict ADOPT
mesh task history --id pr-77540 --action validated --summary "Production smoke passed"
```

Task history actions are stored with a fixed canonical vocabulary. The CLI accepts common semantic aliases and normalizes them before writing, e.g. `completed`/`finished`/`success` → `validated`, and `commit` → `committed`. `mesh doctor --fix-safe` repairs the same aliases in legacy active and archived task files.

### 📚 Shared Knowledge — Persistent context
Project-wide operational memory/status lives in `.mesh/shared/`: thin context, decisions, and current blockers.

Keep dynamic runtime/routing truth in `.mesh/shared/status/`, repeatable how-to material in `.mesh/shared/sop/` or docs/guides, and resolved/superseded evidence in `.mesh/shared/historical/`. Do not bury these in `context.md`, `decisions.md`, or `blockers.md`. Agent Mesh can point to host skills, but it is not a skill system by itself.

```bash
mesh shared read context.md
mesh shared append decisions.md --content "## [2026-05-05] Cache TTL = 1s chosen for RPCs"
```

## Installation

```bash
# From source
git clone https://github.com/NikolaFC/agent-mesh.git
cd agent-mesh
chmod +x cli/mesh
ln -s $(pwd)/cli/mesh /usr/local/bin/mesh
mesh --version

# Or copy the CLI script directly
cp cli/mesh /usr/local/bin/mesh
```

### Dependencies

- Python 3.8+ (standard library only)
- [GitHub CLI](https://cli.github.com) (`gh`) — only needed for `mesh sync`

### Environment

If your working directory is not the project root:
```bash
export MESH_ROOT=/path/to/project/root
```

### Verification

Optional npm scripts are provided as a thin wrapper around the Python-only toolchain:

```bash
npm run bootstrap
npm run verify
npm run smoke
npm run hygiene
npm run sync:drift
```

CI runs the same core checks: `python3 scripts/verify_suite.py`, `python3 scripts/hygiene_scan.py`, and `python3 scripts/sync_drift_check.py`.

## CLI Reference

| Command | Description |
|---------|-------------|
| `mesh --version` | Print Agent Mesh version |
| `mesh init` | Initialize `.mesh/` directory with schemas |
| `mesh status` | Overview of all agents + active tasks |
| `mesh root [--json]` | Show detected mesh root, source, and symlink resolution |
| `mesh export [-o file]` | Export status as markdown report |
| `mesh pulse read [--all]` | Read agent pulse(s) |
| `mesh pulse update` | Update your agent's pulse |
| `mesh pulse touch` | Refresh pulse freshness without changing task/status |
| `mesh pulse check [--strict --json]` | Find stale agents (no update in 30min) |
| `mesh pulse clean` | Remove stale done/idle pulses |
| `mesh task create` | Create a new task |
| `mesh task update` | Update task status/verdict/progress |
| `mesh task assign` | Reassign a task to another agent |
| `mesh task search` | Search tasks by keyword |
| `mesh task history` | Append to task event log |
| `mesh task list` | List tasks with filters |
| `mesh task archive` | Move task to archive |
| `mesh shared read` | Read shared knowledge file |
| `mesh shared append` | Append to shared file (append-only) |
| `mesh shared update` | Replace shared file content |
| `mesh validate [--json]` | Validate all .mesh files against schemas |
| `mesh doctor [--fix-safe]` | Inspect or safely repair state hygiene |
| `mesh sync [--repo]` | Sync PR status from GitHub |
| `mesh state configure` | Configure a private Git backend for cross-device mesh state |
| `mesh state clone` | Clone a shared mesh state root and print `MESH_ROOT` setup |
| `mesh state tailscale host-init|join|url|configure|clone` | Use a Tailscale SSH host as the private Git state backend |
| `mesh state pull` | Pull/rebase remote mesh state |
| `mesh state push` | Commit and push local mesh state |
| `mesh state sync` | Commit local state, pull/rebase, rebuild indexes, and push |
| `mesh migrate plan|export|inspect|apply` | Create and apply host-approved persona/skill migration capsules |
| `mesh evolution log` | Log an identity/preference/SOP change |
| `mesh evolution read` | Read agent evolution logs |
| `mesh evolution sync` | Check other agents' recent changes |
| `mesh evolution compact` | Compact log, archive old entries |
| `mesh evolution index` | Generate searchable JSONL index |
| `mesh config` | Show mesh configuration |
| `mesh index` | Rebuild all indexes (tasks, pulses, evolution) |

## Agent Integration

Before integrating any runtime, read the first-install runbook: [`docs/runbooks/agent-first-install.md`](docs/runbooks/agent-first-install.md). It separates Agent Mesh internals from host/agent-side operations such as prompt injection, pulse updates, watchdogs, and scheduler delivery.

### OpenClaw
```bash
# In cron or heartbeat:
mesh pulse read --all > /tmp/mesh-status.md
# Inject into context or notify human
```

### Codex / Claude Code
Add to your agent prompt:
```
Before editing code:
1. Run `mesh status` to see what other agents are doing
2. Run `mesh task list` to check for related tasks
3. After completing work: `mesh task history --id <id> --action committed --summary "..."`
```

### GitHub Actions
```yaml
- name: Update mesh on PR merge
  run: |
    mesh task update --id pr-${{ github.event.number }} --status merged
    mesh task archive --id pr-${{ github.event.number }}
```

## Why Files?

| Approach | Pros | Cons |
|----------|------|------|
| **Files (chosen)** | Zero deps, git-native, works everywhere | Convention-based |
| SQLite | Query-friendly | Locking issues, not universal |
| HTTP API | Standard | Needs server, not all agents have network |

Files win because:
- Every coding agent reads/writes files
- Git gives version history for free
- `git log .mesh/` = complete collaboration timeline
- Zero operational cost

## Schema

Full JSON Schema definitions in `schema/`:
- [`pulse-v1.json`](schema/pulse-v1.json) — Agent heartbeat schema
- [`task-v1.json`](schema/task-v1.json) — Task tracking schema

Protocol specification: [`PROTOCOL.md`](PROTOCOL.md)

## Real-World Example

This project was born from a real need: our workspace runs two independent agent systems — [OpenClaw](https://github.com/openclaw/openclaw) as the main orchestrator, and **Hermes** as a standalone agent handling PR implementation. Each runs its own gateway on the same WSL machine, sharing the same workspace and memory.

Before Agent Mesh, Hermes would write 22KB handoff documents and OpenClaw had to parse them every time someone asked for a status update. Now:

```
Hermes: "I just force-pushed #77540"  →  updates .mesh/pulse/hermes.json
OpenClaw: reads pulse  →  knows Hermes is waiting for CI
Claude Code: reads pulse  →  knows not to touch #77540 area
Human: mesh status  →  sees everything at a glance
```

### About Hermes

Hermes is an independent agent framework running its own gateway, session management, and skill system. It shares the workspace with OpenClaw and coordinates via Agent Mesh — each writes its own pulse file, and both read the shared `.mesh/` directory. This peer-to-peer model means either agent can work independently, and Agent Mesh provides the shared awareness layer.

See the full [OpenClaw + Hermes workflow example](examples/openclaw-hermes/README.md).

## Git Hooks

Auto-update pulse on every commit:

```bash
# One-time setup
cp hooks/post-commit .git/hooks/post-commit
chmod +x .git/hooks/post-commit

# Or use symlink for auto-updates
git config core.hooksPath hooks
```

Set your agent name:
```bash
export MESH_AGENT=hermes  # or codex, claude-code, etc.
```

## GitHub Actions

Auto-sync mesh tasks on PR events. Copy the template:

```bash
cp .github/workflows/mesh-sync.yml <your-repo>/.github/workflows/
```

See [`.github/workflows/mesh-sync.yml`](.github/workflows/mesh-sync.yml) for the full template.

## Tests

```bash
python3 tests/test_cli.py
pytest -q tests/test_cli.py
```

Tests cover: init, pulse CRUD/touch, task lifecycle, assign, search, shared files, validate/json, export, pulse clean/check, MESH_ROOT env, schema validation, and doctor safe-fix behavior.

## Configuration

Mesh behavior is configurable via `.mesh/config.json`. Run `mesh config` to see current settings.

```json
{
  "evolution": {
    "autoRotate": true,
    "rotateThreshold": 200,
    "rotateKeep": 30,
    "index": { "enabled": true, "experimental": true, "autoIndex": true, "format": "jsonl", "path": ".mesh/shared/evolution/index.jsonl" }
  },
  "tasks": {
    "index": { "enabled": true, "experimental": true, "autoIndex": true, "format": "jsonl", "path": ".mesh/tasks/index.jsonl" }
  },
  "pulses": {
    "index": { "enabled": true, "experimental": true, "autoIndex": true, "format": "jsonl", "path": ".mesh/pulse/index.jsonl" }
  }
}
```

All three index types:
- **tasks** — every task (id, title, status, verdict, assignee, progress, last action)
- **pulses** — every agent pulse (agent, status, current task, last update)
- **evolution** — every identity/SOP change (agent, category, file, summary)

Indexes are auto-rebuilt on every write. Disable per-type via `"autoIndex": false`. All marked `experimental`.

| Option | Default | Description |
|--------|---------|-------------|
| `*.index.enabled` | `true` | Enable JSONL index generation |
| `*.index.experimental` | `true` | Mark as experimental (format may change) |
| `*.index.autoIndex` | `true` | Auto-rebuild index on every mutation |
| `evolution.autoRotate` | `true` | Auto-compact when log exceeds threshold |
| `evolution.rotateThreshold` | `200` | Line count trigger for auto-rotation |
| `evolution.rotateKeep` | `30` | Entries to keep after auto-rotation |

## Evolution: Shared Identity & Mutual Learning

Beyond task coordination, Agent Mesh supports **evolution logging** — a lightweight learning inbox/signal channel for agents to share what changed in their own rules or operating model.

When an agent modifies its core files (AGENTS.md, USER.md, SOUL.md, SOPs), it logs the change to `.mesh/shared/evolution/{agent}.md`. Other agents can read these logs and selectively absorb useful learnings.

Evolution logs are **not canonical memory and not executable skills**. Treat them as signals to review; promote only validated facts to memory/status, thick reusable context to references, and repeatable procedures with trigger/goal/steps/guardrails to skill candidates or host skills.

```bash
# Log a change you made
mesh evolution log --agent hermes --file AGENTS.md --category sop --summary "Added mesh workflow skill"

# Read another agent's evolution
mesh evolution read --agent hermes

# Check what's new from all other agents
mesh evolution sync --my-agent openclaw --since-hours 48
```

This is **not** read on every mesh interaction — it's a passive log that agents actively choose to consume when they want to learn from each other.

## Contributing

1. Fork it
2. Create your feature branch
3. Add yourself to `.mesh/pulse/` (eat your own dog food)
4. Run tests: `python3 tests/test_cli.py`
5. Submit a PR

## License

MIT
