"""relaunch_main.py - stop any running lmeals serve, rebuild+reinstall the
wheel, restart the little-meals systemd --user service, and make sure
tailscaled + `tailscale serve` are up.

Invoked by: bazel run //:relaunch

Unlike //:deploy (which assumes the service is already up and just restarts
it), this also tolerates a stray, manually-started `lmeals serve` left over
from before the Milestone 11 systemd unit existed (see docs/first_run.md's
"Remote deployment" section) and checks tailscaled + `tailscale serve` so the
app stays reachable over the M8 tailnet afterwards. Meant to be safe to run
unattended over Claude Remote Control: no step here prompts for input.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(os.path.abspath(__file__)).parent))

from deploy_common import pipx_install_wheel  # noqa: E402
from little_meals.preflight import check, format_report  # noqa: E402

SERVICE_NAME = "little-meals.service"
APP_PORT = 8765


def _stop_existing() -> None:
    print(f"==> [relaunch] stopping {SERVICE_NAME} (if running)")
    subprocess.run(["systemctl", "--user", "stop", SERVICE_NAME], check=False)

    # Catch a manually-started `lmeals serve` that predates/bypasses the
    # systemd unit and would otherwise hold port 8765.
    result = subprocess.run(["pgrep", "-f", "lmeals serve"], capture_output=True, text=True, check=False)
    pids = [pid for pid in result.stdout.split() if pid]
    if pids:
        print(f"==> [relaunch] killing stray lmeals serve process(es): {', '.join(pids)}")
        subprocess.run(["pkill", "-f", "lmeals serve"], check=False)


def _start_service() -> int:
    print(f"==> [relaunch] starting {SERVICE_NAME}")
    result = subprocess.run(["systemctl", "--user", "start", SERVICE_NAME], check=False)
    if result.returncode != 0:
        print(
            "ERROR: systemctl start failed. Is the unit installed? See "
            "docs/first_run.md's 'Remote deployment' section.",
            file=sys.stderr,
        )
    return result.returncode


def _ensure_tailscale() -> None:
    active = subprocess.run(
        ["systemctl", "is-active", "--quiet", "tailscaled"], check=False
    ).returncode == 0
    if active:
        print("==> [relaunch] tailscaled already running")
        return

    print("==> [relaunch] tailscaled not running, attempting to start it")
    result = subprocess.run(["sudo", "-n", "systemctl", "start", "tailscaled"], check=False)
    if result.returncode != 0:
        print(
            "WARNING: could not start tailscaled non-interactively (needs sudo). "
            "The app was relaunched but may not be reachable over the tailnet - "
            "start it manually with: sudo systemctl start tailscaled",
            file=sys.stderr,
        )
    else:
        print("==> [relaunch] tailscaled started")


def _serve_points_at_app_port() -> bool:
    result = subprocess.run(
        ["tailscale", "serve", "status", "--json"], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        return False
    try:
        config = json.loads(result.stdout)
    except json.JSONDecodeError:
        return False
    proxy_target = f"http://127.0.0.1:{APP_PORT}"
    for web_config in (config.get("Web") or {}).values():
        for handler in (web_config.get("Handlers") or {}).values():
            if handler.get("Proxy") == proxy_target:
                return True
    return False


def _ensure_serve() -> None:
    if _serve_points_at_app_port():
        print(f"==> [relaunch] tailscale serve already points at port {APP_PORT}")
        return

    print(f"==> [relaunch] tailscale serve not configured, pointing it at port {APP_PORT}")
    result = subprocess.run(["tailscale", "serve", "--bg", str(APP_PORT)], check=False)
    if result.returncode != 0:
        print(
            "WARNING: 'tailscale serve --bg' failed. The app was relaunched but won't be "
            "reachable over the tailnet - see docs/first_run.md's 'Remote deployment' section "
            "(you likely need 'sudo tailscale set --operator=<you>' run once).",
            file=sys.stderr,
        )
    else:
        print(f"==> [relaunch] tailscale serve now points at port {APP_PORT}")


def main() -> int:
    result = check()
    print(format_report(result))
    if not result.ok:
        return 1

    _stop_existing()

    returncode = pipx_install_wheel("//:relaunch", "relaunch")
    if returncode != 0:
        return returncode

    returncode = _start_service()
    if returncode != 0:
        return returncode

    _ensure_tailscale()
    _ensure_serve()

    print("==> [relaunch] Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
