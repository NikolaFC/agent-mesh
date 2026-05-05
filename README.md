# Agent Mesh

**A lightweight protocol for multi-agent collaboration.**

> When you use OpenClaw + Codex + Claude Code on the same project, each agent is an island. Agent Mesh is the bridge.

[中文文档](README.zh-CN.md)

## The Problem

You have multiple AI agents working on your codebase:
- **OpenClaw** orchestrating and managing memory
- **Codex** doing deep code implementation
- **Claude Code** reviewing and refactoring
- **Cursor** in your editor

Each one has its own context window. They can't see each other's progress. You spend more time copying context between agents than actually getting work done.

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

# 2. Add to any agent's prompt:
#    "Before starting, read .mesh/pulse/*.json and .mesh/tasks/active/*.json.
#     After completing work, update your pulse and task history."

# 3. That's it. Agents now share state.
```

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

### 📚 Shared Knowledge — Persistent context
Project-wide context, decisions, and blockers in `.mesh/shared/`.

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

## CLI Reference

| Command | Description |
|---------|-------------|
| `mesh init` | Initialize `.mesh/` directory with schemas |
| `mesh status` | Overview of all agents + active tasks |
| `mesh export [-o file]` | Export status as markdown report |
| `mesh pulse read [--all]` | Read agent pulse(s) |
| `mesh pulse update` | Update your agent's pulse |
| `mesh pulse check` | Find stale agents (no update in 30min) |
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
| `mesh validate` | Validate all .mesh files against schemas |
| `mesh sync [--repo]` | Sync PR status from GitHub |

## Agent Integration

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

This project was born from a real need: [OpenClaw](https://github.com/openclaw/openclaw) uses multiple agents (OpenClaw main, Hermes/Codex for PRs, Claude Code for review). Before Agent Mesh, progress sync was manual. Now:

```
Hermes: "I just force-pushed #77540"  →  updates .mesh/pulse/hermes.json
OpenClaw: reads pulse  →  knows Hermes is waiting for CI
Claude Code: reads pulse  →  knows not to touch #77540 area
Human: mesh status  →  sees everything at a glance
```

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
```

46 tests covering: init, pulse CRUD, task lifecycle, assign, search, shared files, validate, export, pulse clean, MESH_ROOT env, schema validation.

## Contributing

1. Fork it
2. Create your feature branch
3. Add yourself to `.mesh/pulse/` (eat your own dog food)
4. Run tests: `python3 tests/test_cli.py`
5. Submit a PR

## License

MIT
