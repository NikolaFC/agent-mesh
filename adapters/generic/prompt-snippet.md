# Agent Mesh — Generic Prompt Snippet

Copy this into any AI coding agent's system prompt to enable Agent Mesh.

---

## Agent Mesh (Cross-Agent State Sharing)

This project uses Agent Mesh for multi-agent collaboration. The `.mesh/` directory contains shared state.

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

### Your agent name:
Use a consistent name: `codex`, `claude-code`, `cursor`, `hermes`, `openclaw`, etc.
