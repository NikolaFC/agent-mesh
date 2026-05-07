#!/usr/bin/env python3
"""Repository hygiene checks for Agent Mesh.

Non-fatal philosophy: keep checks simple, deterministic, and dependency-free.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_SCRIPTS = {"bootstrap", "verify", "smoke", "hygiene", "sync:drift"}
SECRET_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)authorization:\s*bearer\s+[A-Za-z0-9._~+/=-]{16,}"),
    re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"]{12,}['\"]"),
]
TEXT_SUFFIXES = {
    ".md", ".py", ".json", ".yml", ".yaml", ".toml", ".txt", ".sh", "",
}


def git_files() -> list[Path]:
    out = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True)
    return [ROOT / line for line in out.splitlines() if line.strip()]


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    package_path = ROOT / "package.json"
    if not package_path.exists():
        fail("package.json is missing")
    package = json.loads(package_path.read_text(encoding="utf-8"))
    scripts = set((package.get("scripts") or {}).keys())
    missing = sorted(REQUIRED_SCRIPTS - scripts)
    if missing:
        fail(f"package.json missing scripts: {', '.join(missing)}")

    bad_artifacts = []
    secret_hits = []
    for path in git_files():
        rel = path.relative_to(ROOT).as_posix()
        if "__pycache__/" in rel or rel.startswith(".pytest_cache/") or rel.endswith(".pyc"):
            bad_artifacts.append(rel)
            continue
        if path.suffix not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                secret_hits.append(rel)
                break

    if bad_artifacts:
        fail("tracked generated artifacts found: " + ", ".join(sorted(bad_artifacts)))
    if secret_hits:
        fail("possible secret material found in: " + ", ".join(sorted(set(secret_hits))))

    print("hygiene_scan: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
