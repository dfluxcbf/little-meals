"""deploy_main.py - rebuild+reinstall the wheel, then restart the little-meals
systemd --user service.

Invoked by: bazel run //:deploy

Requires the one-time host setup described in docs/first_run.md's "Remote
deployment" section (the little-meals.service unit installed under
~/.config/systemd/user/ and enabled) - this target only rebuilds/reinstalls
and restarts, it doesn't install the unit itself.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(os.path.abspath(__file__)).parent))

from deploy_common import pipx_install_wheel  # noqa: E402
from little_meals.preflight import check, format_report  # noqa: E402

SERVICE_NAME = "little-meals.service"


def main() -> int:
    result = check()
    print(format_report(result))
    if not result.ok:
        return 1

    returncode = pipx_install_wheel("//:deploy", "deploy")
    if returncode != 0:
        return returncode

    print(f"==> [deploy] restarting {SERVICE_NAME}")
    result_proc = subprocess.run(["systemctl", "--user", "restart", SERVICE_NAME], check=False)
    if result_proc.returncode != 0:
        print(
            "ERROR: systemctl restart failed. Is the unit installed? See "
            "docs/first_run.md's 'Remote deployment' section.",
            file=sys.stderr,
        )
        return result_proc.returncode

    print("==> [deploy] Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
