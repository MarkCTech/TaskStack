#!/usr/bin/env python3
"""
Build the in-repo React app into client/webapp_build (Flask static_folder).

Frontend source lives in client/frontend/ (committed with TaskStack).

From repo root:
  python scripts/build_frontend.py

Requires Node.js/npm; script can attempt install via winget/brew.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "client" / "frontend"
OUT = REPO_ROOT / "client" / "webapp_build"


def _which(cmd: str) -> str | None:
    return shutil.which(cmd)


def _run(cmd: list[str], cwd: Path | None = None, env: dict | None = None) -> int:
    return subprocess.run(cmd, cwd=cwd, env=env).returncode


def _run_npm(args: list[str], cwd: Path, env: dict) -> int:
    if sys.platform == "win32":
        cmdline = subprocess.list2cmdline(["npm", *args])
        return subprocess.run(cmdline, cwd=cwd, env=env, shell=True).returncode
    return subprocess.run(["npm", *args], cwd=cwd, env=env).returncode


def _ensure_npm() -> bool:
    if _which("npm") and _which("node"):
        return True
    print("Node.js (includes npm) not found in PATH.")
    print("  Download: https://nodejs.org/  (LTS recommended)")
    try:
        answer = input("Try to install via winget (Windows) or brew (macOS)? [y/N] ").strip().lower()
    except EOFError:
        answer = "n"
    if answer != "y":
        return False
    if sys.platform == "win32":
        if _which("winget"):
            print("Running: winget install OpenJS.NodeJS.LTS --accept-package-agreements")
            if _run(["winget", "install", "OpenJS.NodeJS.LTS", "--accept-package-agreements"]) == 0:
                print("Restart this terminal so PATH includes npm, then run again.")
            return False
        print("winget not found. Install Node from https://nodejs.org/")
        return False
    if sys.platform == "darwin":
        if _which("brew"):
            print("Running: brew install node")
            return _run(["brew", "install", "node"]) == 0 and bool(_which("npm"))
        print("Homebrew not found. Install Node from https://nodejs.org/")
        return False
    print("On Linux, use your package manager, e.g.:")
    print("  sudo apt install nodejs npm   # Debian/Ubuntu")
    print("  sudo dnf install nodejs npm   # Fedora")
    return False


def main() -> int:
    pkg = SRC / "package.json"
    if not pkg.is_file():
        print(f"No package.json in {SRC}. Add the React app under client/frontend/.")
        return 1

    if not _ensure_npm():
        return 1

    env = {**os.environ, "BUILD_PATH": str(Path("../webapp_build").as_posix())}
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)

    if _run_npm(["install"], SRC, env) != 0:
        return 1
    if _run_npm(["run", "build"], SRC, env) != 0:
        return 1

    print(f"Done. Flask serves: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
