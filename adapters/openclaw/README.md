# OpenClaw Adapter for Agent Mesh

## How to Use

Add this to your OpenClaw agent's system prompt (AGENTS.md or SOUL.md):

```markdown
## Agent Mesh Integration

Set `MESH_ROOT` so `mesh` CLI finds `.mesh/` from any directory:
```bash
export MESH_ROOT=/home/nikolafc/.openclaw/workspace
```

Before starting any task, check for .mesh/ in the workspace:
1. Read `.mesh/pulse/*.json` to see what other agents are doing
2. Read `.mesh/tasks/active/*.json` for current work items
3. After completing significant work, update your pulse:
   ```
   exec: mesh pulse update --agent openclaw --status working --task <id> --summary "what I did"
   ```
4. When a task is done:
   ```
   exec: mesh task update --id <id> --status closed
   exec: mesh task archive --id <id>
   ```

### Heartbeat Integration
In HEARTBEAT.md, add:
```
Run `mesh pulse check` — if any agent is stale (>30min), investigate.
Run `mesh status` — report any blockers to Satoshi.
```

### Cron Integration
Create a cron job to sync mesh state:
```
exec: mesh status > docs/status/mesh-overview.md
```
```

## Files

- `prompt-snippet.md` — Copy-paste prompt addition for OpenClaw agents
- `heartbeat-snippet.md` — Addition for HEARTBEAT.md
