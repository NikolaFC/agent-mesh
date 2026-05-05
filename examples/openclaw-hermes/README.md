# Example: OpenClaw + Hermes PR Workflow with Agent Mesh

This shows how our real PR workflow would look with Agent Mesh.

## Before Agent Mesh (the old way)

```
Hermes: [writes 22KB handoff doc]
Satoshi: "多多，Hermes 进展怎样？"
OpenClaw: [reads 22KB doc, memory_search, gh pr view] "总结..."
Satoshi: "那个 PR CI 过了吗？"
OpenClaw: [gh pr view again] "让我查一下..."
```

## After Agent Mesh (the new way)

### Step 1: Hermes starts working
```bash
mesh pulse update --agent hermes --status working --task pr-77540 \
  --summary "rebuilding branch on latest official main"
```

### Step 2: Hermes commits
```bash
mesh task history --id pr-77540 --action committed \
  --summary "cherry-picked 4 cache commits, resolved changelog conflict" \
  --agent hermes --ref "493fe186"
mesh pulse update --agent hermes --status working --task pr-77540 \
  --summary "pushed to fork, waiting for CI"
```

### Step 3: CI passes
```bash
mesh task update --id pr-77540 --status ci-pass
mesh task history --id pr-77540 --action validated \
  --summary "92 success / 20 skipped / 0 failed" --agent hermes
```

### Step 4: OpenClaw checks in (automated or on-demand)
```bash
mesh status
# Output:
# 📡 Agents:
#   hermes: working → pr-77540 (ci-pass, waiting for review)
#
# 📋 Active Tasks:
#   pr-77540  [ci-pass]  ADOPT  → hermes  "cache session/node/cron list lookups"
#   pr-77013  [open]     pending → hermes  "codex goal completion bridge"
```

### Step 5: Satoshi asks "进展怎样？"
OpenClaw just runs `mesh status` — instant answer, no 22KB doc parsing needed.

## The Mesh State at This Point

### .mesh/pulse/hermes.json
```json
{
  "schema": "agent-mesh/pulse/v1",
  "agent": "hermes",
  "agentType": "codex",
  "lastUpdate": "2026-05-05T10:30:00Z",
  "status": "working",
  "currentTask": {
    "id": "pr-77540",
    "title": "cache session/node/cron list lookups",
    "progress": 0.9
  },
  "recentActions": [
    {"type": "commit", "ref": "493fe186", "summary": "rebased on latest main", "at": "2026-05-05T09:00:00Z"},
    {"type": "ci-pass", "ref": "pr-77540", "summary": "92/0/1 checks passed", "at": "2026-05-05T10:00:00Z"}
  ],
  "blockers": [],
  "nextActions": ["wait for maintainer review"]
}
```

### .mesh/pulse/openclaw.json
```json
{
  "schema": "agent-mesh/pulse/v1",
  "agent": "openclaw",
  "agentType": "openclaw",
  "lastUpdate": "2026-05-05T11:00:00Z",
  "status": "idle",
  "recentActions": [
    {"type": "review", "summary": "Reviewed all PR statuses via mesh status", "at": "2026-05-05T11:00:00Z"}
  ],
  "nextActions": ["report to Satoshi", "monitor CI for pr-77013"]
}
```

### .mesh/tasks/active/pr-77540.json
```json
{
  "schema": "agent-mesh/task/v1",
  "id": "pr-77540",
  "type": "upstream-pr",
  "title": "perf(gateway): cache session, node, and cron list lookups",
  "status": "ci-pass",
  "verdict": "ADOPT",
  "priority": "high",
  "assignedTo": "hermes",
  "createdAt": "2026-05-04T20:00:00Z",
  "updatedAt": "2026-05-05T10:30:00Z",
  "progress": 0.9,
  "links": {
    "github": "https://github.com/openclaw/openclaw/pull/77540"
  },
  "history": [
    {"agent": "hermes", "action": "created", "summary": "PR created", "at": "2026-05-04T20:00:00Z"},
    {"agent": "hermes", "action": "repaired", "summary": "Merge conflict resolved", "at": "2026-05-05T09:00:00Z"},
    {"agent": "hermes", "action": "validated", "summary": "CI: 92/0/1 passed", "at": "2026-05-05T10:00:00Z"},
    {"agent": "openclaw", "action": "validated", "summary": "Production runtime smoke passed", "at": "2026-05-05T11:00:00Z"}
  ]
}
```

## What Changed

| Before | After |
|--------|-------|
| 22KB handoff doc to parse | `mesh status` → instant overview |
| Manual "what's the PR status?" | Auto-updated pulse files |
| Context lost between sessions | `.mesh/shared/` persists |
| Human is the message bus | Agents share state directly |
| No visibility into agent activity | `mesh pulse read --all` → real-time |
