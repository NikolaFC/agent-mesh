#!/usr/bin/env python3
"""Check lightweight documentation/config sync drift."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require_contains(path: str, needle: str) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    if needle not in text:
        raise AssertionError(f"{path} missing required marker: {needle}")


def main() -> int:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if package.get("version") != version:
        raise AssertionError(f"package.json version {package.get('version')} != VERSION {version}")

    scripts = package.get("scripts") or {}
    for name in ("bootstrap", "verify", "smoke", "hygiene", "sync:drift"):
        if name not in scripts:
            raise AssertionError(f"package.json missing script {name}")

    for marker in (".mesh/shared/status/", ".mesh/shared/sop/", ".mesh/shared/historical/", "not a skill system by itself"):
        require_contains("README.md", marker)
    for marker in (".mesh/shared/status/", ".mesh/shared/sop/", ".mesh/shared/historical/", "不是 canonical memory，也不是 executable skill"):
        require_contains("README.zh-CN.md", marker)
    for marker in ("Memory vs Skill boundary", ".mesh/shared/status/*", ".mesh/shared/historical/*"):
        require_contains("PROTOCOL.md", marker)

    ci = ROOT / ".github" / "workflows" / "ci.yml"
    if not ci.exists():
        raise AssertionError("missing .github/workflows/ci.yml")
    for marker in ("python3 scripts/verify_suite.py", "python3 scripts/hygiene_scan.py", "python3 scripts/sync_drift_check.py"):
        require_contains(".github/workflows/ci.yml", marker)

    print("sync_drift_check: ok")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
