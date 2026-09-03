"""relaunch_main.py - rebuild+reinstall the little-meals wheel, then restart
the running `lmeals serve` process so the new code takes effect.

Invoked by: bazel run //:relaunch

The app is expected to be running as a little-termstyle mux "server" session
(tab 9, `: server lmeals serve` - see the lterm MCP's autostart config and
docs/first_run.md's "Remote deployment" section). That session runs `lmeals
serve` through little-termstyle's own crash-respawning wrapper
(`little-termstyle server run <command>`, see little-termstyle's
docs/design.md), so killing just the `lmeals serve` process is enough: the
wrapper notices it died and starts a fresh one - picking up the wheel just
installed - a few seconds later, without tearing down the mux tab/session
itself. Unlike the systemd-managed setup this replaced (`bazel run
//:deploy` still uses that), nothing here brings the process up if it
wasn't already running - see the warning `_restart_server` prints in that
case.

tailscaled/`tailscale serve` are assumed to already be up (tab 0 runs its
own `tailscale serve` mux session) and are no longer managed here.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(os.path.abspath(__file__)).parent))

from deploy_common import pipx_install_wheel  # noqa: E402
from little_meals.preflight import check, format_report  # noqa: E402

# The exact path systemd's ExecStart also uses (see
# ~/.config/systemd/user/little-meals.service) - matching on it rather than
# just "lmeals serve" keeps this from also catching little-termstyle's own
# `server run "lmeals serve"` wrapper process, whose command line contains
# that same substring.
SERVER_CMDLINE_MATCH = str(Path.home() / ".local/bin/lmeals serve")


def _restart_server() -> None:
    result = subprocess.run(["pgrep", "-f", SERVER_CMDLINE_MATCH], capture_output=True, text=True, check=False)
    pids = [pid for pid in result.stdout.split() if pid]
    if not pids:
        print(
            "==> [relaunch] lmeals serve was not running - nothing to restart. "
            "Start it with ': server lmeals serve' in little-termstyle tab 9's input pane.",
            file=sys.stderr,
        )
        return

    print(f"==> [relaunch] stopping lmeals serve process(es): {', '.join(pids)}")
    subprocess.run(["pkill", "-f", SERVER_CMDLINE_MATCH], check=False)
    print("==> [relaunch] little-termstyle's server wrapper will relaunch it (with the new build) shortly")


def main() -> int:
    result = check()
    print(format_report(result))
    if not result.ok:
        return 1

    returncode = pipx_install_wheel("//:relaunch", "relaunch")
    if returncode != 0:
        return returncode

    _restart_server()

    print("==> [relaunch] Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
