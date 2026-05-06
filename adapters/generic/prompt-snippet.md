# Agent Mesh — Generic Prompt Snippet

Copy this into any AI coding agent's system prompt to enable Agent Mesh.

For first-time onboarding, read the full runbook first:
`docs/runbooks/agent-first-install.md`

---

## Agent Mesh (Cross-Agent State Sharing)

This project uses Agent Mesh for multi-agent collaboration. The `.mesh/` directory contains shared state.

### Environment Setup

If your working directory is not the project root, set:
```bash
export MESH_ROOT=/path/to/project/root
```
The `mesh` CLI uses this to locate `.mesh/` regardless of your current directory.

### First-install requirement

Agent Mesh core is only the shared state layer. This agent must also wire Mesh into its own work loop:

1. Keep a stable agent name.
2. Refresh pulse at start, milestones, blockers, and completion.
3. Append task history when meaningful work happens.
4. Run or participate in heartbeat/watchdog checks.
5. Report stale/blocked/validation failures through the host's normal alert path.

### Before starting work:
1. Run `mesh status` to see what other agents are doing
2. Check `.mesh/tasks/active/` for related tasks
3. Read `.mesh/shared/context.md` for project-wide context

### After completing significant work:
1. Update your pulse: `mesh pulse update --agent <your-name> --status working --task <id> --summary "what you did"`
2. Log to task history: `mesh task history --id <id> --action committed --summary "brief description"`

### When blocked:
1. Update pulse: `mesh pulse update --agent <your-name> --status blocked`
2. Add blocker: `mesh pulse update --agent <your-name> --status blocked --summary "why you're blocked"`

### When you finish a task:
1. `mesh task update --id <id> --status closed`
2. `mesh pulse update --agent <your-name> --status done`

### Heartbeat-only refresh:
Use `mesh pulse touch --agent <your-name> --summary "heartbeat"` when you only need to refresh freshness without changing current task/status.

### Your agent name:
Use a consistent name: `codex`, `claude-code`, `cursor`, `hermes`, `openclaw`, etc.
