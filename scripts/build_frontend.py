#!/usr/bin/env python3
"""
Cross-platform frontend build: clone/pull React repo, then npm install + build.
Output: client/webapp_build (Flask static_folder).

One command from repo root:
  python scripts/build_frontend.py

Repo URL and branch are read from the root Makefile (FRONTEND_REPO, FRONTEND_BRANCH).
Requires Git. Node.js/npm are checked; script can attempt install via winget/brew.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Paths relative to repo root
REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "client" / "frontend-src"
OUT = REPO_ROOT / "client" / "webapp_build"
MAKEFILE = REPO_ROOT / "Makefile"
DEFAULT_BRANCH = "main"


def _read_makefile_repo() -> str | None:
    if not MAKEFILE.is_file():
        return None
    text = MAKEFILE.read_text(encoding="utf-8", errors="replace")
    # FRONTEND_REPO := url  or  FRONTEND_REPO ?= url  or  FRONTEND_REPO=url
    m = re.search(
        r"^\s*FRONTEND_REPO\s*[?:]?=\s*(.+?)\s*(?:#.*)?$",
        text,
        re.MULTILINE,
    )
    if not m:
        return None
    url = m.group(1).strip().strip('"').strip("'")
    if not url or url.startswith("$(") or "YOUR_" in url or "org/repo" in url:
        return None
    return url


def _read_makefile_branch() -> str | None:
    if not MAKEFILE.is_file():
        return None
    text = MAKEFILE.read_text(encoding="utf-8", errors="replace")
    m = re.search(
        r"^\s*FRONTEND_BRANCH\s*[?:]?=\s*(.+?)\s*(?:#.*)?$",
        text,
        re.MULTILINE,
    )
    if not m:
        return None
    b = m.group(1).strip().strip('"').strip("'")
    return b if b else None


def _which(cmd: str) -> str | None:
    return shutil.which(cmd)


def _run(cmd: list[str], cwd: Path | None = None, env: dict | None = None) -> int:
    r = subprocess.run(cmd, cwd=cwd, env=env)
    return r.returncode


def _run_npm(args: list[str], cwd: Path, env: dict) -> int:
    """
    Run npm on Windows reliably. npm is shipped as npm.cmd; subprocess.run(["npm", ...])
    uses CreateProcess and fails with WinError 2 because there is no npm.exe.
    """
    if sys.platform == "win32":
        # shell=True lets cmd.exe resolve npm.cmd; list2cmdline handles quoting
        cmdline = subprocess.list2cmdline(["npm", *args])
        r = subprocess.run(cmdline, cwd=cwd, env=env, shell=True)
        return r.returncode
    r = subprocess.run(["npm", *args], cwd=cwd, env=env)
    return r.returncode


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


def _clone_or_pull(url: str, branch: str) -> bool:
    if not _which("git"):
        print("Git not found. Install Git and retry.")
        return False
    if not (SRC / ".git").is_dir():
        SRC.parent.mkdir(parents=True, exist_ok=True)
        print(f"Cloning {branch} -> {SRC}")
        return (
            _run(
                ["git", "clone", "--depth", "1", "-b", branch, url, str(SRC)],
                cwd=REPO_ROOT,
            )
            == 0
        )
    print(f"Pulling {branch} in {SRC}")
    return (
        _run(["git", "fetch", "origin", branch], cwd=SRC) == 0
        and _run(["git", "checkout", branch], cwd=SRC) == 0
        and _run(["git", "pull", "origin", branch], cwd=SRC) == 0
    )


def _npm_build() -> bool:
    pkg = SRC / "package.json"
    if not pkg.is_file():
        print(f"No package.json in {SRC}. Clone failed or wrong repo.")
        return False
    # BUILD_PATH must be relative to SRC so CRA writes to client/webapp_build
    env = {**os.environ, "BUILD_PATH": str(Path("../webapp_build").as_posix())}
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    if _run_npm(["install"], SRC, env) != 0:
        return False
    return _run_npm(["run", "build"], SRC, env) == 0


def main() -> int:
    url = (sys.argv[1] if len(sys.argv) > 1 else "").strip() or _read_makefile_repo()
    if not url:
        print("Set FRONTEND_REPO in Makefile (FRONTEND_REPO := https://...) or pass URL as argument.")
        return 1
    branch = (
        (sys.argv[2] if len(sys.argv) > 2 else "").strip()
        or os.environ.get("FRONTEND_BRANCH")
        or _read_makefile_branch()
        or DEFAULT_BRANCH
    )

    if not _ensure_npm():
        return 1
    if not _clone_or_pull(url, branch):
        return 1
    if not _npm_build():
        return 1
    print(f"Done. Flask serves: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
