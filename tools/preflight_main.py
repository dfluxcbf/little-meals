"""preflight_main.py - system-dependency check.

Invoked by: bazel run //:preflight
"""

from __future__ import annotations

from little_meals.preflight import main

if __name__ == "__main__":
    raise SystemExit(main())
