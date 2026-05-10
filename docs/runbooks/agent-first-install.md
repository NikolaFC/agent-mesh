# Agent First-Install Runbook

This runbook is for the **agent-side work** required after installing Agent Mesh. The CLI and `.mesh/` files are only the shared state layer; every participating agent must also wire Agent Mesh into its own startup prompt, heartbeat, task lifecycle, and optional watchdog.

Read this once when onboarding a new agent runtime such as OpenClaw, Hermes, Codex, Claude Code, Cursor, or a custom worker.

## 0. What belongs outside Agent Mesh core?

Agent Mesh core provides:

- `mesh` CLI
- `.mesh/pulse/*.json`
- `.mesh/tasks/{active,archived}/*.json`
- `.mesh/shared/{context,decisions,blockers}.md`
- schemas and indexes

The following are **host / agent responsibilities** and must be configured in the agent runtime that uses Mesh:

- adding Mesh instructions to the agent's system prompt / startup files
- setting `MESH_ROOT` when the agent may run outside the repo root
- updating the agent's own pulse during work
- adding task history at milestones
- running heartbeat / watchdog checks
- deciding how alerts are delivered to humans
- registering any scheduled watchdog with the host's cron/model/governance policy

## 1. Install and locate Mesh

From the project that should contain shared state:

```bash
mesh init
mesh root
mesh status
mesh validate
```

If the agent's working directory may not be the project root, set:

```bash
export MESH_ROOT=/path/to/project/root
```

For WSL ↔ Mac / cross-device sharing, prefer a dedicated private state root instead of a normal code repo:

```bash
# First machine
mkdir -p ~/agent-mesh-state
cd ~/agent-mesh-state
mesh init
mesh state configure --remote git@github.com:<you>/<private-mesh-state>.git
mesh state push --message "initial mesh state"

# Second machine
mesh state clone --remote git@github.com:<you>/<private-mesh-state>.git --target ~/agent-mesh-state
export MESH_ROOT=~/agent-mesh-state
mesh state sync
```

For the private Tailscale SSH variant, pick one canonical tailnet host and let every other machine join it:

```bash
# On the canonical Tailscale SSH host, one time:
mesh state tailscale host-init \
  --repo-path ~/agent-mesh-state.git \
  --state-root ~/agent-mesh-state \
  --seed-from /path/to/current/project \
  --host desktop-564viur-1.tail715c1b.ts.net \
  --user nikolafc

# On each client agent machine:
mesh state tailscale join \
  --host desktop-564viur-1.tail715c1b.ts.net \
  --user nikolafc \
  --repo-path /home/nikolafc/agent-mesh-state.git \
  --target ~/agent-mesh-state
export MESH_ROOT=~/agent-mesh-state
```

Use `join` instead of `configure` for clients when possible; it makes the host/client direction explicit and refuses to overwrite non-empty local state.

Acceptance:

```bash
mesh root --json
mesh status
mesh pulse check --strict --json
mesh validate --json
```

`mesh status` should show the shared state; `validate` should be clean on a fresh install.

## 2. Choose a stable agent name

Use one lowercase, stable name per runtime:

- `openclaw`
- `hermes`
- `codex`
- `claude-code`
- `cursor`
- `reviewer`
- `sub-worker`

Rules:

- each agent writes only `.mesh/pulse/<agent>.json`
- task owners may update task fields
- non-owners should usually append task history instead of overwriting fields
- use `mesh pulse touch --agent <name>` for heartbeat-only freshness updates that should not change task/status

## 3. Add this prompt block to the agent startup

Copy this into the agent's system prompt, startup file, or equivalent long-lived instruction layer:

```text
## Agent Mesh collaboration protocol

This project uses Agent Mesh for cross-agent state sharing.

Environment:
- If not already in the project root, set MESH_ROOT=<project-root>.

Before starting work:
1. Run `mesh root` to confirm which shared root this runtime is using.
2. If this root uses cross-device Git sync, run `mesh state sync`.
3. Run `mesh status`.
4. Run `mesh task list` and look for related active tasks.
5. Read `.mesh/shared/context.md`; if decisions/blockers matter, read those too.

During work:
- Keep your pulse fresh when starting work, reaching a milestone, becoming blocked, or finishing.
- Use your stable agent name: <agent-name>.
- Example: `mesh pulse update --agent <agent-name> --status working --task <task-id> --summary "what changed"`.

When committing or finishing a meaningful step:
1. Append task history: `mesh task history --id <task-id> --action committed --agent <agent-name> --summary "what changed"`.
2. Update task fields only if you own the task or were asked to do so.
3. Update pulse again.

When blocked:
1. `mesh pulse update --agent <agent-name> --status blocked --task <task-id> --summary "why blocked"`.
2. Add a blocker to `.mesh/shared/blockers.md` if another agent or human needs to act.

Before final response / handoff:
1. Run `mesh validate` if you wrote Mesh state.
2. Make sure your pulse is not stale.
3. If this root uses cross-device Git sync, run `mesh state sync --message "<agent> mesh update"`.
4. If task state changed, make the final task status/history match the actual outcome.
```

## 4. Lifecycle command patterns

Start work:

```bash
mesh root
mesh state sync   # only when this root has a Git state remote configured
mesh status
mesh task list
mesh pulse update --agent <agent> --status working --task <task-id> --summary "started <scope>"
```

Milestone:

```bash
mesh task history --id <task-id> --agent <agent> --action commented --summary "milestone summary"
mesh pulse update --agent <agent> --status working --task <task-id> --summary "milestone summary"
```

Commit:

```bash
mesh task history --id <task-id> --agent <agent> --action committed --summary "committed $(git rev-parse --short HEAD)"
mesh pulse update --agent <agent> --status working --task <task-id> --summary "committed $(git rev-parse --short HEAD)"
```

Heartbeat-only freshness update:

```bash
mesh pulse touch --agent <agent> --summary "heartbeat"
```

Blocked:

```bash
mesh pulse update --agent <agent> --status blocked --task <task-id> --summary "blocked: <reason>"
mesh shared append blockers --content "## [$(date -Iseconds)] <title>\n<reason / needed action>"
```

Done:

```bash
mesh task history --id <task-id> --agent <agent> --action validated --summary "validation passed"
mesh task update --id <task-id> --status closed --progress 1
mesh pulse update --agent <agent> --status done --task <task-id> --summary "done"
mesh state sync --message "<agent> completed <task-id>"  # when using a Git state remote
```

## 5. Add a heartbeat / watchdog

A human-facing Mesh installation should not rely only on agents remembering to update pulse. Add one of these:

### Minimal heartbeat inside the agent

On each routine heartbeat / check-in:

```bash
mesh pulse touch --agent <agent> --summary "heartbeat"
mesh pulse check --strict --json
mesh validate --json
```

If there are stale agents, blockers, or validation errors, report them. If clean, stay silent.

### External watchdog

Run periodically from a scheduler such as cron, systemd timer, GitHub Actions, or the host agent scheduler:

```bash
mesh doctor --fix-safe --json
mesh pulse check --strict --json
mesh validate --json
```

**Important**: call `mesh` directly in the cron/watchdog payload. Do not wrap it in agent-specific modules (e.g. `python -m some_agent.terminal`) that may not be installed — `mesh` has zero external dependencies and works standalone.

Recommended interval: 5-15 minutes for active multi-agent work; 30-60 minutes for low-activity repos.

Recommended alert policy:

- no alert when everything is clean
- alert on stale pulse
- alert on schema validation failure
- alert once when `doctor --fix-safe` repaired state
- suppress duplicate identical alerts for a cooldown window

## 6. Safe-fix boundary

`mesh doctor --fix-safe` is allowed to do only safe, mechanical cleanup:

- rebuild indexes
- backfill missing schema fields in legacy task files
- normalize safe legacy aliases such as priority `P0 -> critical`
- move terminal tasks (`closed`, `done`, `merged`, `deployed`, `archived`) from active to archived
- update auto-managed runtime snapshot blocks

It must **not** decide business truth:

- do not change PR verdicts such as `ADOPT` / `REPAIR` / `CLOSE` based on guesses
- do not mark work done just because a pulse is idle
- do not rewrite append-only decisions history
- do not remove blockers without evidence

## 7. Host-specific scheduling notes

### OpenClaw-style agent scheduler

If using an agent scheduler / cron job:

- explicitly set the model in the cron payload
- keep the payload thin: run the watchdog script or the three commands above
- let delivery happen through scheduler delivery config, not ad-hoc messaging inside the job
- register the job in any local cron/model guard allowlist if your host has one
- deliver alerts to the Mesh maintenance channel/thread, not the general chat

### Shell cron / systemd timer

Example shell cron body:

```bash
cd /path/to/project/root
mesh doctor --fix-safe --json >/tmp/mesh-doctor.json
mesh pulse check --strict --json >/tmp/mesh-pulse.json
mesh validate --json >/tmp/mesh-validate.json
```

Wrap it with your own notifier. Do not spam on clean runs.

### Git hook

Optional, useful for coding agents:

```bash
export MESH_AGENT=<agent>
cp hooks/post-commit .git/hooks/post-commit
chmod +x .git/hooks/post-commit
```

## 8. First-install acceptance checklist

Before declaring an agent onboarded:

- [ ] `mesh` is on `PATH`
- [ ] `MESH_ROOT` is set or the agent always runs from the repo root
- [ ] the agent startup prompt includes the Mesh collaboration protocol
- [ ] `mesh pulse update --agent <agent> --status idle --summary "onboarded"` works
- [ ] `mesh status` shows the new agent
- [ ] `mesh validate` passes
- [ ] heartbeat/watchdog is configured
- [ ] stale/validation alerts have a human-visible destination
- [ ] duplicate clean runs are silent

## 9. Troubleshooting

Pulse is stale but agent is working:

- the agent likely did not load this runbook / prompt block
- add a heartbeat hook with `mesh pulse touch`
- check that `MESH_ROOT` points to the same repo as other agents

`mesh validate` fails after real-world usage:

- run `mesh doctor --fix-safe --json`
- if still failing, update schema only when the new field/status is a real protocol concept, not a typo

Agents disagree with Mesh truth:

- Mesh is a shared state layer, not an oracle
- compare with external truth (GitHub, production runtime, CI, logs)
- update `.mesh/shared/context.md` or task history with the verified truth
- avoid overwriting old history; append corrections

Runtime path/version is stale:

- add or update an auto-managed runtime snapshot block in `.mesh/shared/context.md`
- do not trust old handoff text over a live command such as `openclaw --version`, `git rev-parse HEAD`, or service status

Cron heartbeat shows `ok` but pulse is stale:

- the agent scheduler may treat any output (including errors) as success
- check the actual cron session logs, not just `last_status`
- common cause: the cron invokes a wrapper module (e.g. `python -m hermes_tools.terminal`) that is not installed in the agent's venv
- fix: call `mesh` CLI directly in the cron payload — it has zero external dependencies
- example broken command: `python -m hermes_tools.terminal "... && bash scripts/pulse.sh update ..."`
- example fixed command: `cd /path/to/project/root && MESH_ROOT=. mesh pulse update --agent <agent> --status working --summary "heartbeat"`
- after fixing, manually run the new command once to verify, then wait for the next cron cycle

Watchdog alerts on `done` agents:

- agents with status `done` or `completed` legitimately stop updating pulse
- use `mesh pulse check --ignore-done` to skip them in stale checks
- the built-in watchdog script already uses `--ignore-done`; if you write your own, pass this flag too
