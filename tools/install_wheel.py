"""install_wheel.py - preflight-check, then pipx-install the wheel built by Bazel.

Invoked by: bazel run //:install
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from little_meals.preflight import check, format_report


def _runfiles_root() -> Path:
    explicit = os.environ.get("RUNFILES_DIR")
    if explicit:
        return Path(explicit)
    p = Path(os.path.abspath(__file__))
    for parent in p.parents:
        if parent.name.endswith(".runfiles"):
            return parent
    raise RuntimeError(
        f"Cannot locate .runfiles directory starting from {__file__}. "
        "Make sure you invoke this via 'bazel run //:install'."
    )


def _find_wheel(runfiles_dir: Path) -> Path:
    candidates = list(runfiles_dir.glob("_main/src/little_meals/*.whl"))
    if not candidates:
        raise FileNotFoundError(
            f"No wheel found under {runfiles_dir}/_main/src/little_meals/. Run 'bazel build //:wheel' first."
        )
    return sorted(candidates)[-1]


def main() -> int:
    result = check()
    print(format_report(result))
    if not result.ok:
        return 1

    if not os.environ.get("BUILD_WORKSPACE_DIRECTORY"):
        print(
            "ERROR: $BUILD_WORKSPACE_DIRECTORY not set. Run this via 'bazel run //:install'.",
            file=sys.stderr,
        )
        return 1

    runfiles_dir = _runfiles_root()
    wheel = _find_wheel(runfiles_dir)

    print(f"==> [install] pipx installing wheel: {wheel.name}")
    result_proc = subprocess.run(["pipx", "install", "--force", str(wheel)], check=False)
    if result_proc.returncode != 0:
        print("ERROR: pipx install failed.", file=sys.stderr)
        return result_proc.returncode

    print("==> [install] Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
