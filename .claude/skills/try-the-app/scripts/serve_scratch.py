#!/usr/bin/env python3
"""Serve little-meals from this checkout on a scratch port and data dir: the try-the-app skill's script.

    python3 .claude/skills/try-the-app/scripts/serve_scratch.py [--port 8766] [--data-dir PATH]

Runs `little_meals.cli serve` from src/ (no install needed). Port 8765 is the household's live server, so it is
refused, as is a port something already listens on. Without --data-dir a fresh one is made in the temp folder."""

from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
LIVE_PORT = 8765


def port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        return probe.connect_ex(("127.0.0.1", port)) == 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--data-dir", default=None, help="Default: a new folder in the temp directory")
    args = parser.parse_args(argv)
    if args.port == LIVE_PORT:
        parser.error(f"port {LIVE_PORT} is the household's live server: pick another one")
    if port_in_use(args.port):
        print(f"port {args.port} is already in use: stop what runs there, or pass --port", file=sys.stderr)
        return 1
    data_dir = Path(args.data_dir) if args.data_dir else Path(tempfile.mkdtemp(prefix="little-meals-try-"))
    data_dir.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(p for p in (str(ROOT / "src"), os.environ.get("PYTHONPATH")) if p)}
    print(f"little-meals from {ROOT} at http://127.0.0.1:{args.port} (data dir {data_dir})", flush=True)
    command = [sys.executable, "-m", "little_meals.cli", "serve", "--port", str(args.port), "--data-dir", str(data_dir)]
    try:
        return subprocess.call(command, env=env, cwd=ROOT)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
