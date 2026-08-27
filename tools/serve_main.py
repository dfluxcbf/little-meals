"""serve_main.py - run the web app.

Invoked by: bazel run //:serve
"""

from __future__ import annotations

from little_meals.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["serve"]))
