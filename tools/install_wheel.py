"""install_wheel.py - preflight-check, then pipx-install the wheel built by Bazel.

Invoked by: bazel run //:install
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(os.path.abspath(__file__)).parent))

from deploy_common import pipx_install_wheel  # noqa: E402
from little_meals.preflight import check, format_report  # noqa: E402


def main() -> int:
    result = check()
    print(format_report(result))
    if not result.ok:
        return 1

    returncode = pipx_install_wheel("//:install", "install")
    if returncode != 0:
        return returncode

    print("==> [install] Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
