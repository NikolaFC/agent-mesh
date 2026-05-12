# Agent Mesh MCP Interface (experimental) — Construction Plan

Status: construction-ready MVP
Owner: Satoshi Lab / Agent Mesh
Scope: optional extension, not Agent Mesh core runtime; initial shared-context allowlist is OpenClaw ↔ Hermes only

## 1. Product intent

Agent Mesh currently makes cross-agent work visible through files: pulse, tasks, shared context, decisions, blockers, and status docs. The experimental Mesh MCP interface turns that shared state into a tool surface that approved agents can query without bespoke handoff prompts.

The first published experimental scope is intentionally narrow: only `openclaw` and `hermes` are accepted by the transcript/session/context-pack tools. This keeps the feature useful for the original two-runtime deployment while avoiding a premature general raw-session bus.

The feature is primarily for two workflows:

1. **Cross-agent bug repair** — Agent A can inspect Agent B's relevant session history, failed commands, and current task context before patching.
2. **Seamless handoff** — A new agent can continue an existing conversation or task without asking the user to manually prepare a cross-agent prompt.

The core value is not only "shared MCP tools". The core value is **controlled access to other agents' context**.

## 2. Non-goals

- Do not replace OpenClaw MCP.
- Do not replace Hermes / coding-runtime MCP.
- Do not make Agent Mesh core depend on a daemon, network service, or MCP SDK.
- Do not automatically inject raw transcripts into every agent prompt.
- Do not sync raw transcripts to remote Mesh state by default.
- Do not flatten every downstream MCP tool into one global namespace.

## 3. System boundary and division of labor

### OpenClaw MCP

OpenClaw MCP remains the bridge for OpenClaw-owned routed conversations:

- Discord / Telegram / Signal / channel sessions
- `messages_read`, `messages_send`
- approval requests and responses
- OpenClaw session route metadata

It is the **channel/session bridge**.

### Hermes MCP

Hermes or coding-runtime MCP remains the bridge for execution context:

- coding harness state
- repo/file/shell/patch/test context
- coding logs and run outputs
- Hermes-owned session context

It is the **execution/runtime bridge**.

### Agent Mesh MCP (experimental)

Agent Mesh MCP exposes the cross-agent coordination layer:

- agent/task/pulse catalog
- registered session catalog
- cross-agent context search
- full transcript reads behind a permission gate
- context pack generation
- access request/grant/audit records
- optional registry/proxy entry points for other MCP servers

It is the **cross-agent context fabric**.

Agent Mesh MCP may consume OpenClaw/Hermes as context providers, but it should not loop OpenClaw → Mesh MCP → OpenClaw MCP → OpenClaw in a way that creates routing or approval ambiguity.

## 4. Access gate policy

When an agent believes a task needs another agent's session history, it must request approval before reading the transcript.

User choices:

- `allow-once` — one read for the requested source session and scope.
- `allow-session` — allow reads for the current target session/task and requested source session.
- `deny` — no read; the agent must proceed with available context or ask a narrower question.

`allow-session` is intentionally scoped. It is not a global pass to read every session.

### Trigger heuristics

An agent should request cross-agent session history when any of these are true:

1. Local memory / Mesh status / status docs do not contain a clear enough record.
2. The conversation has been idle for a long time and the user's message looks like immediate continuation of work not owned by the current agent.
3. The user explicitly says to continue, take over, inspect the peer runtime, fix the peer runtime's bug, or check Hermes/OpenClaw side context.
4. Mesh task/pulse shows the relevant task owner is not the current agent.
5. A bug fix depends on failed attempts, command output, stack traces, or reasoning that is only present in another agent's transcript.
6. Status sources conflict and raw transcript is needed to determine the truth.

## 5. Local data model

All experimental files live under `.mesh/mcp/` and are excluded from the core protocol guarantee unless explicitly documented later.

```text
.mesh/mcp/
├── sessions/                 # registered transcript descriptors
│   └── <session-key>.json
├── requests/                 # access requests awaiting decision or history
│   └── <request-id>.json
├── grants/                   # allow-once / allow-session grants
│   └── <grant-id>.json
├── servers.json              # optional downstream MCP server registry
└── audit.jsonl               # who read what, why, when
```

Session descriptors point to local transcript material. In the initial experimental release, descriptors are limited to OpenClaw/Hermes. Adapters can later materialize descriptors from other runtimes after their own trust and redaction policy is designed.

## 6. CLI / MCP tool surface

Initial CLI surface:

```bash
mesh mcp session register --agent hermes --session-id bug-123 --transcript /path/to/log.txt
mesh mcp session list
mesh mcp access request --requesting-agent openclaw --target-session hermes:bug-123 --reason "handoff"
mesh mcp access decide --id <request-id> --decision allow-once --by satoshi
mesh mcp transcript read --requesting-agent openclaw --target-session hermes:bug-123 --mode full
mesh mcp context pack --requesting-agent openclaw --target-session hermes:bug-123 --token-budget 4000
mesh mcp server set browser '{"command":"browser-mcp","args":[]}'
mesh mcp server list
mesh mcp serve

# Rejected in the initial experimental scope:
# mesh mcp session register --agent coder-pro --session-id bug-123 --transcript /path/to/log.txt
```

Initial MCP tools exposed by `mesh mcp serve`:

- `mesh_agents_list`
- `mesh_sessions_list`
- `mesh_access_request`
- `mesh_transcript_read`
- `mesh_context_pack`
- `mesh_mcp_servers_list`
- `mesh_mcp_tools_list`
- `mesh_mcp_call`

Downstream MCP tools are addressed by namespace:

```json
{"server":"browser", "tool":"open_page", "input":{"url":"https://example.com"}}
```

No global tool flattening in the MVP.

## 7. Security and audit defaults

- Full transcript reads are enabled only after an explicit grant.
- Local trusted agents can request raw reads, but remote state sync must not publish raw transcripts by default.
- Every read writes an audit event with requester, target session, mode, reason/request id, and timestamp.
- Reading a transcript does not automatically inject it into the model context; agents should generate a bounded context pack.
- External MCP proxy calls are experimental and should remain namespaced.

## 8. MVP success criteria

- Agent Mesh still works without MCP dependencies.
- `mesh mcp serve` can be launched as a stdio MCP server.
- OpenClaw/Hermes sessions can be registered/listed; unsupported agents are rejected.
- Cross-agent transcript read requires `allow-once` or scoped `allow-session` approval.
- Context pack generation works from a registered transcript.
- Optional downstream MCP server registry exists and is namespaced.
- Tests cover register → request → approve → read → audit, plus MCP server tool listing.

## 9. Later phases

- Native OpenClaw session-history adapter.
- Native Hermes transcript adapter.
- Redaction/sanitization profiles.
- Rich search index over transcripts.
- Persistent shared MCP daemon for long-lived HTTP/streamable-http clients.
- Per-resource leases for browser/filesystem/shell/trading tools.
