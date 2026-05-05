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


def test(name):
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
    with test("init creates .mesh structure") as t:
        mesh = Path(t.tmpdir) / ".mesh"
        check(mesh.is_dir(), ".mesh/ created")
        check((mesh / "pulse").is_dir(), "pulse/ created")
        check((mesh / "tasks" / "active").is_dir(), "tasks/active/ created")
        check((mesh / "tasks" / "archived").is_dir(), "tasks/archived/ created")
        check((mesh / "shared" / "context.md").exists(), "shared/context.md created")
        check((mesh / "shared" / "decisions.md").exists(), "shared/decisions.md created")
        check((mesh / "shared" / "blockers.md").exists(), "shared/blockers.md created")


def test_pulse():
    with test("pulse update + read") as t:
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
    with test("task create → update → history → archive") as t:
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


def test_task_assign():
    with test("task assign") as t:
        run(["task", "create", "--id", "reassign-1", "--title", "Reassign me", "--type", "feature", "--assign", "alice"], cwd=t.tmpdir)
        rc, _, _ = run(["task", "assign", "--id", "reassign-1", "--agent", "bob"], cwd=t.tmpdir)
        check(rc == 0, "task assign succeeds")

        # Verify
        task_file = Path(t.tmpdir) / ".mesh" / "tasks" / "active" / "reassign-1.json"
        data = json.loads(task_file.read_text())
        check(data["assignedTo"] == "bob", "assignee updated to bob")


def test_task_search():
    with test("task search") as t:
        run(["task", "create", "--id", "search-1", "--title", "Fix the cache layer", "--type", "bugfix", "--assign", "alice"], cwd=t.tmpdir)
        run(["task", "create", "--id", "search-2", "--title", "Add auth module", "--type", "feature", "--assign", "bob"], cwd=t.tmpdir)

        rc, out, _ = run(["task", "search", "cache"], cwd=t.tmpdir)
        check(rc == 0, "search succeeds")
        check("search-1" in out, "finds cache task")
        check("search-2" not in out, "excludes auth task")


def test_shared():
    with test("shared read/append/update") as t:
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
    with test("validate passes on fresh init") as t:
        rc, out, _ = run(["validate"], cwd=t.tmpdir)
        check(rc == 0, "validate succeeds")
        check("passed" in out.lower(), "reports passed")


def test_export():
    with test("export markdown report") as t:
        run(["pulse", "update", "--agent", "bot1", "--status", "idle"], cwd=t.tmpdir)
        run(["task", "create", "--id", "exp-1", "--title", "Export test", "--type", "feature"], cwd=t.tmpdir)

        rc, out, _ = run(["export"], cwd=t.tmpdir)
        check(rc == 0, "export succeeds")
        check("Agent Mesh Status Report" in out, "has report header")
        check("bot1" in out, "includes agent")
        check("exp-1" in out, "includes task")


def test_export_to_file():
    with test("export to file") as t:
        outfile = Path(t.tmpdir) / "report.md"
        rc, _, _ = run(["export", "--output", str(outfile)], cwd=t.tmpdir)
        check(rc == 0, "export to file succeeds")
        check(outfile.exists(), "output file created")


def test_pulse_clean():
    with test("pulse clean") as t:
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
    with test("pulse clean skips working agents") as t:
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


def test_status():
    with test("status overview") as t:
        run(["pulse", "update", "--agent", "alpha", "--status", "working"], cwd=t.tmpdir)
        run(["task", "create", "--id", "st-1", "--title", "Status test", "--type", "feature"], cwd=t.tmpdir)

        rc, out, _ = run(["status"], cwd=t.tmpdir)
        check(rc == 0, "status succeeds")
        check("alpha" in out, "shows agent")
        check("st-1" in out, "shows task")


def test_mesh_root_env():
    with test("MESH_ROOT env var") as t:
        # Run from a different directory, using MESH_ROOT
        other = tempfile.mkdtemp()
        try:
            os.environ["MESH_ROOT"] = t.tmpdir
            rc, out, _ = run(["status"], cwd=other)
            check(rc == 0, "MESH_ROOT works from different cwd")
        finally:
            del os.environ["MESH_ROOT"]
            shutil.rmtree(other, ignore_errors=True)


def test_schema_validation():
    with test("schema validation catches bad data") as t:
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
        test_pulse,
        test_task_lifecycle,
        test_task_assign,
        test_task_search,
        test_shared,
        test_validate,
        test_export,
        test_export_to_file,
        test_pulse_clean,
        test_pulse_clean_skips_working,
        test_status,
        test_mesh_root_env,
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
