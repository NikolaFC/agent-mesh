#!/usr/bin/env python3
"""Local bootstrap helper for Agent Mesh.

This project has no runtime package dependencies. Bootstrap keeps the CLI
executable and prints the optional install command without requiring sudo.
"""
from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "cli" / "mesh"


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> int:
    if not CLI.exists():
        print(f"ERROR: missing CLI at {CLI}", file=sys.stderr)
        return 1

    mode = CLI.stat().st_mode
    CLI.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    run([sys.executable, str(CLI), "--version"])

    print("\nBootstrap complete.")
    print("Optional install:")
    print(f"  ln -sf {CLI} /usr/local/bin/mesh")
    print("Or use directly:")
    print(f"  {CLI} status")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
