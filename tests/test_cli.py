#!/usr/bin/env python3
"""Agent Mesh CLI test suite.

Run: python3 tests/test_cli.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

MESH = str(Path(__file__).resolve().parent.parent / "cli" / "mesh")
PASS = 0
FAIL = 0


def run(args, cwd=None, expect_rc=0):
    """Run mesh CLI and return (rc, stdout, stderr)."""
    r = subprocess.run(
        [sys.executable, MESH] + args,
        capture_output=True, text=True, timeout=15,
        cwd=cwd,
        env={**os.environ, "NO_COLOR": "1"},
    )
    if expect_rc is not None and r.returncode != expect_rc:
        print(f"  ❌ Expected rc={expect_rc}, got {r.returncode}")
        print(f"     stdout: {r.stdout[:200]}")
        print(f"     stderr: {r.stderr[:200]}")
    return r.returncode, r.stdout, r.stderr


def case(name):
    """Test context manager."""
    class Ctx:
        def __enter__(self):
            self.tmpdir = tempfile.mkdtemp()
            # Init mesh
            run(["init"], cwd=self.tmpdir)
            return self
        def __exit__(self, *args):
            shutil.rmtree(self.tmpdir, ignore_errors=True)
    print(f"🧪 {name}")
    return Ctx()


def check(cond, msg):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {msg}")
    else:
        FAIL += 1
        print(f"  ❌ {msg}")


# ── Tests ──────────────────────────────────────────────────────

def test_init():
    with case("init creates .mesh structure") as t:
        mesh = Path(t.tmpdir) / ".mesh"
        check(mesh.is_dir(), ".mesh/ created")
        check((mesh / "pulse").is_dir(), "pulse/ created")
        check((mesh / "tasks" / "active").is_dir(), "tasks/active/ created")
        check((mesh / "tasks" / "archived").is_dir(), "tasks/archived/ created")
        check((mesh / "shared" / "context.md").exists(), "shared/context.md created")
        check((mesh / "shared" / "decisions.md").exists(), "shared/decisions.md created")
        check((mesh / "shared" / "blockers.md").exists(), "shared/blockers.md created")
        check((mesh / "shared" / "status").is_dir(), "shared/status/ created")
        check((mesh / "shared" / "historical").is_dir(), "shared/historical/ created")


def test_version():
    with case("version flag") as t:
        rc, out, _ = run(["--version"], cwd=t.tmpdir)
        check(rc == 0, "version succeeds")
        check("Agent Mesh 0.3.0" in out, "version output correct")


def test_root_command():
    with case("root command") as t:
        rc, out, _ = run(["root", "--json"], cwd=t.tmpdir)
        check(rc == 0, "root json succeeds")
        data = json.loads(out)
        check(data["root"] == str(Path(t.tmpdir).resolve()), "root path correct")
        check(data["mesh"].endswith(".mesh"), "mesh path shown")


def test_pulse():
    with case("pulse update + read") as t:
        rc, out, _ = run(["pulse", "update", "--agent", "testbot", "--status", "working", "--summary", "testing"], cwd=t.tmpdir)
        check(rc == 0, "pulse update succeeds")
        check((Path(t.tmpdir) / ".mesh" / "pulse" / "testbot.json").exists(), "pulse file created")

        rc, out, _ = run(["pulse", "read", "--agent", "testbot"], cwd=t.tmpdir)
        check(rc == 0, "pulse read succeeds")
        data = json.loads(out)
        check(data["agent"] == "testbot", "agent name correct")
        check(data["status"] == "working", "status correct")
        check(len(data["recentActions"]) == 1, "one recent action")


def test_task_lifecycle():
    with case("task create → update → history → archive") as t:
        rc, _, _ = run(["task", "create", "--id", "test-1", "--title", "Test task", "--type", "feature", "--assign", "alice"], cwd=t.tmpdir)
        check(rc == 0, "task create")

        rc, _, _ = run(["task", "update", "--id", "test-1", "--status", "in-progress", "--progress", "0.5"], cwd=t.tmpdir)
        check(rc == 0, "task update")

        rc, _, _ = run(["task", "history", "--id", "test-1", "--action", "committed", "--summary", "first commit", "--agent", "alice"], cwd=t.tmpdir)
        check(rc == 0, "task history")

        rc, out, _ = run(["task", "list"], cwd=t.tmpdir)
        check("test-1" in out, "task appears in list")

        rc, _, _ = run(["task", "archive", "--id", "test-1"], cwd=t.tmpdir)
        check(rc == 0, "task archive")

        # Should not appear in active list
        rc, out, _ = run(["task", "list"], cwd=t.tmpdir)
        check("test-1" not in out, "archived task not in active list")


def test_task_history_action_aliases_are_canonicalized():
    with case("task history action aliases are canonicalized") as t:
        run(["task", "create", "--id", "alias-1", "--title", "Alias task", "--type", "feature", "--assign", "alice"], cwd=t.tmpdir)
        rc, _, _ = run(["task", "history", "--id", "alias-1", "--action", "completed", "--summary", "done", "--agent", "alice"], cwd=t.tmpdir)
        check(rc == 0, "completed alias accepted")

        task_file = Path(t.tmpdir) / ".mesh" / "tasks" / "active" / "alias-1.json"
        data = json.loads(task_file.read_text())
        check(data["history"][-1]["action"] == "validated", "completed stored as validated")

        rc, out, _ = run(["validate", "--json"], cwd=t.tmpdir)
        check(rc == 0 and json.loads(out)["ok"] is True, "canonicalized task validates")


def test_task_assign():
    with case("task assign") as t:
        run(["task", "create", "--id", "reassign-1", "--title", "Reassign me", "--type", "feature", "--assign", "alice"], cwd=t.tmpdir)
        rc, _, _ = run(["task", "assign", "--id", "reassign-1", "--agent", "bob"], cwd=t.tmpdir)
        check(rc == 0, "task assign succeeds")

        # Verify
        task_file = Path(t.tmpdir) / ".mesh" / "tasks" / "active" / "reassign-1.json"
        data = json.loads(task_file.read_text())
        check(data["assignedTo"] == "bob", "assignee updated to bob")


def test_task_search():
    with case("task search") as t:
        run(["task", "create", "--id", "search-1", "--title", "Fix the cache layer", "--type", "bugfix", "--assign", "alice"], cwd=t.tmpdir)
        run(["task", "create", "--id", "search-2", "--title", "Add auth module", "--type", "feature", "--assign", "bob"], cwd=t.tmpdir)

        rc, out, _ = run(["task", "search", "cache"], cwd=t.tmpdir)
        check(rc == 0, "search succeeds")
        check("search-1" in out, "finds cache task")
        check("search-2" not in out, "excludes auth task")


def test_shared():
    with case("shared read/append/update") as t:
        rc, out, _ = run(["shared", "read", "context.md"], cwd=t.tmpdir)
        check(rc == 0, "shared read")
        check("Shared Context" in out, "context.md has expected content")

        run(["shared", "append", "decisions.md", "--content", "## Decision 1\nUse files."], cwd=t.tmpdir)
        rc, out, _ = run(["shared", "read", "decisions.md"], cwd=t.tmpdir)
        check("Decision 1" in out, "append works")

        run(["shared", "update", "context.md", "--content", "# New Context\nReplaced."], cwd=t.tmpdir)
        rc, out, _ = run(["shared", "read", "context.md"], cwd=t.tmpdir)
        check("Replaced" in out, "update replaces content")
        check("Shared Context" not in out, "old content gone")


def test_validate():
    with case("validate passes on fresh init") as t:
        rc, out, _ = run(["validate"], cwd=t.tmpdir)
        check(rc == 0, "validate succeeds")
        check("passed" in out.lower(), "reports passed")

        rc, out, _ = run(["validate", "--json"], cwd=t.tmpdir)
        check(rc == 0, "validate json succeeds")
        check(json.loads(out)["ok"] is True, "validate json reports ok")


def test_boundary_warnings():
    with case("memory/skill boundary warnings") as t:
        shared = Path(t.tmpdir) / ".mesh" / "shared"
        (shared / "context.md").write_text(
            "# Shared Context\n\n"
            "## Emergency SOP\n"
            "```bash\n"
            "cd repo\n"
            "git status\n"
            "mesh status\n"
            "python3 scripts/fix.py\n"
            "```\n"
            "1. Run the command.\n"
            "2. Restart the service.\n"
        )
        sop_dir = shared / "sop"
        sop_dir.mkdir()
        (sop_dir / "incident.md").write_text(
            "# Incident note\n\n"
            "Status: RESOLVED\n"
            "Issue: CI failed once\n"
            "Current: no active problem\n"
            "Decision: leave as-is\n"
            "Resolution: rerun passed\n"
            "Evidence: PR #123 CI passed\n"
        )

        rc, out, _ = run(["validate", "--json"], cwd=t.tmpdir)
        parsed = json.loads(out)
        check(rc == 0 and parsed["ok"] is True, "boundary warnings are non-fatal")
        paths = {w["path"] for w in parsed["warnings"]}
        check(".mesh/shared/context.md" in paths, "warns when context accumulates SOP material")
        check(".mesh/shared/sop/incident.md" in paths, "warns when SOP looks like one-off status")

        rc, out, _ = run(["doctor", "--json"], cwd=t.tmpdir)
        doctor = json.loads(out)
        check(any(w.get("kind") == "boundary" for w in doctor["warnings"]), "doctor includes boundary warnings")


def test_export():
    with case("export markdown report") as t:
        run(["pulse", "update", "--agent", "bot1", "--status", "idle"], cwd=t.tmpdir)
        run(["task", "create", "--id", "exp-1", "--title", "Export test", "--type", "feature"], cwd=t.tmpdir)

        rc, out, _ = run(["export"], cwd=t.tmpdir)
        check(rc == 0, "export succeeds")
        check("Agent Mesh Status Report" in out, "has report header")
        check("bot1" in out, "includes agent")
        check("exp-1" in out, "includes task")


def test_export_to_file():
    with case("export to file") as t:
        outfile = Path(t.tmpdir) / "report.md"
        rc, _, _ = run(["export", "--output", str(outfile)], cwd=t.tmpdir)
        check(rc == 0, "export to file succeeds")
        check(outfile.exists(), "output file created")


def test_pulse_clean():
    with case("pulse clean") as t:
        # Create a pulse with old timestamp
        pulse_file = Path(t.tmpdir) / ".mesh" / "pulse" / "stale-bot.json"
        pulse_file.write_text(json.dumps({
            "schema": "agent-mesh/pulse/v1",
            "agent": "stale-bot",
            "agentType": "custom",
            "lastUpdate": "2020-01-01T00:00:00Z",
            "status": "done",
        }))
        rc, out, _ = run(["pulse", "clean", "--stale-minutes", "1"], cwd=t.tmpdir)
        check(rc == 0, "pulse clean succeeds")
        check(not pulse_file.exists(), "stale done pulse removed")


def test_pulse_clean_skips_working():
    with case("pulse clean skips working agents") as t:
        pulse_file = Path(t.tmpdir) / ".mesh" / "pulse" / "busy-bot.json"
        pulse_file.write_text(json.dumps({
            "schema": "agent-mesh/pulse/v1",
            "agent": "busy-bot",
            "agentType": "custom",
            "lastUpdate": "2020-01-01T00:00:00Z",
            "status": "working",
        }))
        rc, _, _ = run(["pulse", "clean", "--stale-minutes", "1"], cwd=t.tmpdir)
        check(rc == 0, "pulse clean succeeds")
        check(pulse_file.exists(), "working pulse NOT removed")


def test_pulse_touch_and_strict_check():
    with case("pulse touch + strict/json check") as t:
        run(["pulse", "update", "--agent", "touchbot", "--status", "working", "--task", "task-1", "--summary", "started"], cwd=t.tmpdir)
        rc, out, _ = run(["pulse", "touch", "--agent", "touchbot", "--summary", "heartbeat"], cwd=t.tmpdir)
        check(rc == 0, "pulse touch succeeds")

        pulse_file = Path(t.tmpdir) / ".mesh" / "pulse" / "touchbot.json"
        data = json.loads(pulse_file.read_text())
        check(data["status"] == "working", "touch preserves status")
        check(data["currentTask"]["id"] == "task-1", "touch preserves task")

        # Force staleness and verify strict/json mode exits non-zero.
        data["lastUpdate"] = "2020-01-01T00:00:00Z"
        pulse_file.write_text(json.dumps(data))
        rc, out, _ = run(["pulse", "check", "--strict", "--json", "--stale-minutes", "1"], cwd=t.tmpdir, expect_rc=1)
        check(rc == 1, "strict check returns non-zero on stale")
        parsed = json.loads(out)
        check(parsed["ok"] is False and parsed["stale"][0]["agent"] == "touchbot", "strict json reports stale agent")


def test_doctor_safe_fix_archives_terminal():
    with case("doctor --fix-safe archives terminal tasks") as t:
        run(["task", "create", "--id", "done-1", "--title", "Done", "--type", "feature", "--assign", "alice"], cwd=t.tmpdir)
        run(["task", "update", "--id", "done-1", "--status", "closed", "--progress", "1"], cwd=t.tmpdir)
        rc, out, _ = run(["doctor", "--fix-safe", "--json"], cwd=t.tmpdir)
        check(rc == 0, "doctor safe-fix succeeds")
        check(json.loads(out)["ok"] is True, "doctor reports ok")

        active = Path(t.tmpdir) / ".mesh" / "tasks" / "active" / "done-1.json"
        archived = Path(t.tmpdir) / ".mesh" / "tasks" / "archived" / "done-1.json"
        check(not active.exists(), "terminal task removed from active")
        check(archived.exists(), "terminal task moved to archive")
        runtime_status = Path(t.tmpdir) / ".mesh" / "shared" / "status" / "openclaw-runtime.md"
        context_file = Path(t.tmpdir) / ".mesh" / "shared" / "context.md"
        check(runtime_status.exists(), "runtime snapshot written to shared/status")
        check("agent-mesh-runtime-snapshot" not in context_file.read_text(), "runtime snapshot not embedded in context")


def test_doctor_safe_fix_normalizes_archived_action_aliases():
    with case("doctor --fix-safe normalizes archived action aliases") as t:
        archived = Path(t.tmpdir) / ".mesh" / "tasks" / "archived" / "legacy-done.json"
        archived.write_text(json.dumps({
            "schema": "agent-mesh/task/v1",
            "id": "legacy-done",
            "type": "ops",
            "title": "Legacy done",
            "status": "done",
            "verdict": "pending",
            "priority": "medium",
            "assignedTo": "alice",
            "createdAt": "2026-01-01T00:00:00Z",
            "updatedAt": "2026-01-01T00:00:00Z",
            "progress": 1.0,
            "history": [{
                "agent": "alice",
                "action": "completed",
                "summary": "legacy wording",
                "at": "2026-01-01T00:00:00Z",
            }],
        }))

        rc, _, _ = run(["validate", "--json"], cwd=t.tmpdir, expect_rc=1)
        check(rc == 1, "validate catches non-canonical archived alias before doctor")

        rc, out, _ = run(["doctor", "--fix-safe", "--json"], cwd=t.tmpdir)
        check(rc == 0 and json.loads(out)["ok"] is True, "doctor fixes archived alias")
        data = json.loads(archived.read_text())
        check(data["history"][0]["action"] == "validated", "archived completed alias stored as validated")

        rc, out, _ = run(["validate", "--json"], cwd=t.tmpdir)
        check(rc == 0 and json.loads(out)["ok"] is True, "validate passes after archived alias fix")


def test_status():
    with case("status overview") as t:
        run(["pulse", "update", "--agent", "alpha", "--status", "working"], cwd=t.tmpdir)
        run(["task", "create", "--id", "st-1", "--title", "Status test", "--type", "feature"], cwd=t.tmpdir)

        rc, out, _ = run(["status"], cwd=t.tmpdir)
        check(rc == 0, "status succeeds")
        check("alpha" in out, "shows agent")
        check("st-1" in out, "shows task")


def test_mesh_root_env():
    with case("MESH_ROOT env var") as t:
        # Run from a different directory, using MESH_ROOT
        other = tempfile.mkdtemp()
        try:
            os.environ["MESH_ROOT"] = t.tmpdir
            rc, out, _ = run(["status"], cwd=other)
            check(rc == 0, "MESH_ROOT works from different cwd")
        finally:
            del os.environ["MESH_ROOT"]
            shutil.rmtree(other, ignore_errors=True)


def test_state_sync_between_two_roots():
    with case("state sync via git remote between two roots") as t:
        remote_parent = tempfile.mkdtemp()
        root_b = tempfile.mkdtemp()
        try:
            remote = Path(remote_parent) / "mesh-state.git"
            subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True, text=True)

            rc, _, _ = run(["state", "configure", "--remote", str(remote)], cwd=t.tmpdir)
            check(rc == 0, "state configure succeeds")
            run(["pulse", "update", "--agent", "wsl-agent", "--status", "working", "--summary", "from WSL"], cwd=t.tmpdir)
            rc, _, _ = run(["state", "push", "--message", "initial mesh state"], cwd=t.tmpdir)
            check(rc == 0, "state push succeeds")

            shutil.rmtree(root_b)
            rc, out, _ = run(["state", "clone", "--remote", str(remote), "--target", root_b])
            check(rc == 0, "state clone succeeds")
            rc, out, _ = run(["pulse", "read", "--agent", "wsl-agent"], cwd=root_b)
            check(rc == 0 and "from WSL" in out, "second root sees first root pulse")

            run(["pulse", "update", "--agent", "mac-agent", "--status", "working", "--summary", "from Mac"], cwd=root_b)
            rc, _, _ = run(["state", "sync", "--message", "mac pulse"], cwd=root_b)
            check(rc == 0, "state sync from second root succeeds")
            rc, _, _ = run(["state", "pull"], cwd=t.tmpdir)
            check(rc == 0, "state pull into first root succeeds")
            rc, out, _ = run(["pulse", "read", "--agent", "mac-agent"], cwd=t.tmpdir)
            check(rc == 0 and "from Mac" in out, "first root sees second root pulse")
        finally:
            shutil.rmtree(remote_parent, ignore_errors=True)
            shutil.rmtree(root_b, ignore_errors=True)


def test_state_configure_refuses_project_content_by_default():
    with case("state configure refuses non-dedicated project roots") as t:
        Path(t.tmpdir, "src").mkdir()
        Path(t.tmpdir, "src", "app.py").write_text("print('hello')\n")
        remote_parent = tempfile.mkdtemp()
        try:
            remote = Path(remote_parent) / "mesh-state.git"
            subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True, text=True)
            rc, _, _ = run(["state", "configure", "--remote", str(remote)], cwd=t.tmpdir, expect_rc=1)
            check(rc == 1, "state configure refuses project root")
        finally:
            shutil.rmtree(remote_parent, ignore_errors=True)


def test_state_tailscale_url_and_configure():
    with case("state tailscale url + configure") as t:
        expected = "satoshi@macbook.tailnet.ts.net:/Users/satoshi/agent-mesh-state.git"
        rc, out, _ = run([
            "state", "tailscale", "url",
            "--host", "macbook.tailnet.ts.net",
            "--repo-path", "/Users/satoshi/agent-mesh-state.git",
            "--user", "satoshi",
        ], cwd=t.tmpdir)
        check(rc == 0 and out.strip() == expected, "tailscale url builds scp-style Git remote")

        rc, _, _ = run([
            "state", "tailscale", "configure",
            "--host", "macbook.tailnet.ts.net",
            "--repo-path", "/Users/satoshi/agent-mesh-state.git",
            "--user", "satoshi",
        ], cwd=t.tmpdir)
        check(rc == 0, "tailscale configure succeeds without network access")

        rc, out, _ = run(["state", "status", "--json"], cwd=t.tmpdir)
        data = json.loads(out)
        check(rc == 0 and data["remote"] == expected, "tailscale remote stored in state config")


def test_evolution_log():
    with case("evolution log + read") as t:
        rc, _, _ = run(["evolution", "log", "--agent", "hermes", "--file", "AGENTS.md", "--category", "sop", "--summary", "Added mesh workflow"], cwd=t.tmpdir)
        check(rc == 0, "evolution log succeeds")

        evo_file = Path(t.tmpdir) / ".mesh" / "shared" / "evolution" / "hermes.md"
        check(evo_file.exists(), "evolution file created")

        rc, out, _ = run(["evolution", "read", "--agent", "hermes"], cwd=t.tmpdir)
        check(rc == 0, "evolution read succeeds")
        check("Added mesh workflow" in out, "content matches")
        check("AGENTS.md" in out, "file name shown")


def test_evolution_multiple_entries():
    with case("evolution multiple entries") as t:
        run(["evolution", "log", "--agent", "hermes", "--file", "USER.md", "--summary", "Change 1"], cwd=t.tmpdir)
        run(["evolution", "log", "--agent", "hermes", "--file", "SOUL.md", "--summary", "Change 2"], cwd=t.tmpdir)
        run(["evolution", "log", "--agent", "openclaw", "--file", "AGENTS.md", "--summary", "Change 3"], cwd=t.tmpdir)

        rc, out, _ = run(["evolution", "read", "--all"], cwd=t.tmpdir)
        check(rc == 0, "read all succeeds")
        check("Change 1" in out, "entry 1 present")
        check("Change 2" in out, "entry 2 present")
        check("Change 3" in out, "entry 3 present")

        rc, out, _ = run(["evolution", "read", "--agent", "hermes", "--recent", "1"], cwd=t.tmpdir)
        check(rc == 0, "recent filter works")
        check("Change 2" in out, "shows most recent")


def test_evolution_sync():
    with case("evolution sync") as t:
        run(["evolution", "log", "--agent", "hermes", "--file", "AGENTS.md", "--summary", "Hermes learned something"], cwd=t.tmpdir)
        run(["evolution", "log", "--agent", "openclaw", "--file", "HEARTBEAT.md", "--summary", "OpenClaw learned something"], cwd=t.tmpdir)

        # openclaw sync should see hermes but not itself
        rc, out, _ = run(["evolution", "sync", "--my-agent", "openclaw"], cwd=t.tmpdir)
        check(rc == 0, "sync succeeds")
        check("hermes" in out, "sees hermes")

        # hermes sync should see openclaw but not itself
        rc, out, _ = run(["evolution", "sync", "--my-agent", "hermes"], cwd=t.tmpdir)
        check(rc == 0, "sync reverse succeeds")
        check("openclaw" in out, "sees openclaw")


def test_schema_validation():
    with case("schema validation catches bad data") as t:
        # Write a bad pulse file (missing required fields)
        bad = Path(t.tmpdir) / ".mesh" / "pulse" / "bad.json"
        bad.write_text('{"schema": "wrong"}')
        rc, _, err = run(["validate"], cwd=t.tmpdir, expect_rc=1)
        check(rc == 1, "validate rejects bad data")


# ── Runner ─────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("Agent Mesh CLI Test Suite")
    print("=" * 50)
    print()

    tests = [
        test_init,
        test_version,
        test_root_command,
        test_pulse,
        test_task_lifecycle,
        test_task_history_action_aliases_are_canonicalized,
        test_task_assign,
        test_task_search,
        test_shared,
        test_validate,
        test_boundary_warnings,
        test_export,
        test_export_to_file,
        test_pulse_clean,
        test_pulse_clean_skips_working,
        test_pulse_touch_and_strict_check,
        test_doctor_safe_fix_archives_terminal,
        test_doctor_safe_fix_normalizes_archived_action_aliases,
        test_status,
        test_mesh_root_env,
        test_state_sync_between_two_roots,
        test_state_configure_refuses_project_content_by_default,
        test_state_tailscale_url_and_configure,
        test_evolution_log,
        test_evolution_multiple_entries,
        test_evolution_sync,
        test_schema_validation,
    ]

    for t in tests:
        try:
            t()
        except Exception as e:
            FAIL += 1
            print(f"  💥 {e}")

    print()
    print(f"{'=' * 50}")
    print(f"Results: {PASS} passed, {FAIL} failed, {PASS + FAIL} total")
    print(f"{'=' * 50}")
    sys.exit(1 if FAIL else 0)
