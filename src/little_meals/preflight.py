from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass(frozen=True)
class SystemDependency:
    command: str
    purpose: str
    install_hint: str


TIERS: list[tuple[str, list[SystemDependency]]] = [
    (
        "core tools",
        [
            SystemDependency(
                command="python3",
                purpose="runs the app and the build scripts",
                install_hint="sudo apt install -y python3",
            ),
            SystemDependency(
                command="pipx",
                purpose="installs the little-meals CLI in an isolated venv",
                install_hint="sudo apt install -y pipx   (or: python3 -m pip install --user pipx)",
            ),
        ],
    ),
]


@dataclass(frozen=True)
class PreflightResult:
    missing: list[SystemDependency] = field(default_factory=list)
    stopped_at_tier: Optional[str] = None

    @property
    def ok(self) -> bool:
        return not self.missing


def check(which: Callable[[str], Optional[str]] = shutil.which) -> PreflightResult:
    for tier_name, deps in TIERS:
        missing = [dep for dep in deps if which(dep.command) is None]
        if missing:
            return PreflightResult(missing=missing, stopped_at_tier=tier_name)

    return PreflightResult(missing=[], stopped_at_tier=None)


def format_report(result: PreflightResult) -> str:
    if result.ok:
        return "All system dependencies are present."

    lines: list[str] = []
    lines.append(f"Missing system dependencies (tier: {result.stopped_at_tier}):")
    for dep in result.missing:
        lines.append(f"  - {dep.command}: {dep.purpose}")
        lines.append(f"      install: {dep.install_hint}")
    lines.append("Resolve these, then re-run.")
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    result = check()
    print(format_report(result))
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
