# Changelog

All notable changes to Agent Mesh are documented here.

This project follows SemVer. See `VERSION` for the current package version.

## [Unreleased]

### Changed

- Marked cross-terminal/cross-device Mesh state sync as experimental in docs/runbooks and clarified that every target device must have the standalone `mesh` CLI installed; `openclaw mesh` is not a fallback.
- Documented explicit cross-device/host-local sync receipts so agents report which Mesh layer changed, including state worktree and bare repo commits.
- Migration capsules now skip host-local `TOOLS.md` by default so WSL/macOS absolute paths and local tool boundaries are not copied blindly across devices.
- Added a first-install repair checklist for migrated clients that have Mesh-dependent rules but no standalone `mesh` CLI or operational `.mesh/shared`, `.mesh/tasks`, and `.mesh/pulse` tree.

## [0.3.0] - 2026-05-10

### Added

- Added `mesh root [--json]` to show the detected mesh root, `.mesh` path, root source, and symlink resolution.
- Added experimental cross-terminal/cross-device Git state backend commands:
  - `mesh state configure`
  - `mesh state clone`
  - `mesh state status`
  - `mesh state pull`
  - `mesh state push`
  - `mesh state sync`
- Added experimental Tailscale SSH helpers for private tailnet-backed state repos:
  - `mesh state tailscale host-init`
  - `mesh state tailscale join`
  - `mesh state tailscale url`
  - `mesh state tailscale configure`
  - `mesh state tailscale clone`
- Added `mesh migrate plan/export/inspect/apply` for host-approved OpenClaw persona/rule/memory/skill migration capsules, including `--include-memory` for stable `memory/` files.
- Added `mesh qmd remote-search` for read-only SSH/Tailscale querying of a canonical host's QMD index, including remote PATH prefix support for non-interactive shells that miss Bun-installed `qmd`.
- Added tests that simulate WSL ↔ Mac style sharing through a local bare Git remote, verify Tailscale host/client generation/configuration, exercise migration capsule dry-run/write behavior, and validate remote QMD command construction.

### Changed

- Mutating CLI commands now use a local `.mesh/.lock` on POSIX platforms.
- JSON and Markdown writes now use same-directory temporary files followed by atomic replacement.
- Documentation now recommends a dedicated private mesh-state repo for cross-device sharing and keeps `mesh sync` reserved for GitHub PR sync.
- Documentation now separates mesh state sync from persona/memory/skill migration, with migration excluded-path guardrails.

### Safety

- `mesh state configure` refuses to use a non-dedicated project directory by default; pass `--allow-project-repo` only when intentional.
- Generated indexes and local lock/cache files are ignored by the Git state backend to reduce avoidable sync conflicts.

## [0.2.0] - 2026-05-06

### Added

- Added explicit Agent Mesh versioning via `VERSION` and `mesh --version`.
- Added `mesh pulse touch` for heartbeat-only freshness updates without changing task/status.
- Added `mesh pulse check --strict --json` for watchdog and CI automation.
- Added `mesh validate --json` for machine-readable validation.
- Added `mesh doctor --fix-safe` for safe mechanical hygiene repairs:
  - rebuild indexes
  - backfill legacy task fields
  - normalize safe aliases such as `P0 -> critical`
  - archive terminal active tasks
  - update auto-managed runtime snapshot blocks
- Added first-install agent-side runbook: `docs/runbooks/agent-first-install.md`.
- Added README / protocol / adapter links to the runbook.
- Added pytest-compatible coverage for version-adjacent automation paths: pulse touch, strict JSON checks, validate JSON, and doctor safe-fix.

### Changed

- Expanded schema enums to match real-world Mesh usage:
  - pulse action types: `config`, `handoff`
  - task type: `coordination`
  - task statuses: `ready`, `done`
  - task verdicts: `accepted`, `superseded`, `superseded-by-official-update`
  - task actions: `confirmed`, `updated`, `superseded`
- Updated docs to distinguish Agent Mesh core responsibilities from host/agent-side integration responsibilities.
- Made `tests/test_cli.py` pytest-friendly while preserving direct `python3 tests/test_cli.py` execution.

### Fixed

- Fixed stale active-task hygiene by giving `doctor --fix-safe` a safe path to archive terminal tasks.
- Fixed validation friction caused by real-world status/action names not being represented in schemas.

## [0.1.0] - 2026-05-05

### Added

- Initial Agent Mesh file-based shared state protocol.
- CLI for pulse, task, shared knowledge, export, sync, evolution logs, indexes, and validation.
- JSON schemas for pulse and task files.
- OpenClaw/Hermes collaboration example and adapter prompt snippets.
- Optional GitHub Actions and git hook integration templates.
