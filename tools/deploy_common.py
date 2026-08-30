"""deploy_common.py - shared runfiles/wheel/pipx helpers for install_wheel.py,
deploy_main.py, and relaunch_main.py.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def runfiles_root(invoked_via: str) -> Path:
    explicit = os.environ.get("RUNFILES_DIR")
    if explicit:
        return Path(explicit)
    p = Path(os.path.abspath(__file__))
    for parent in p.parents:
        if parent.name.endswith(".runfiles"):
            return parent
    raise RuntimeError(
        f"Cannot locate .runfiles directory starting from {__file__}. "
        f"Make sure you invoke this via 'bazel run {invoked_via}'."
    )


def find_wheel(runfiles_dir: Path) -> Path:
    candidates = list(runfiles_dir.glob("_main/src/little_meals/*.whl"))
    if not candidates:
        raise FileNotFoundError(
            f"No wheel found under {runfiles_dir}/_main/src/little_meals/. Run 'bazel build //:wheel' first."
        )
    return sorted(candidates)[-1]


def require_workspace_dir(invoked_via: str) -> bool:
    if not os.environ.get("BUILD_WORKSPACE_DIRECTORY"):
        print(
            f"ERROR: $BUILD_WORKSPACE_DIRECTORY not set. Run this via 'bazel run {invoked_via}'.",
            file=sys.stderr,
        )
        return False
    return True


def pipx_install_wheel(invoked_via: str, label: str) -> int:
    """Resolve the wheel and pipx-install it. Returns a process exit code (0 on success)."""
    if not require_workspace_dir(invoked_via):
        return 1

    wheel = find_wheel(runfiles_root(invoked_via))
    print(f"==> [{label}] pipx installing wheel: {wheel.name}")
    result = subprocess.run(["pipx", "install", "--force", str(wheel)], check=False)
    if result.returncode != 0:
        print("ERROR: pipx install failed.", file=sys.stderr)
    return result.returncode
