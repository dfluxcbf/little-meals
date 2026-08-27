from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass, field
from typing import Callable, Optional

from little_meals.config import Settings


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
    (
        "local LLM runtime",
        [
            SystemDependency(
                command="ollama",
                purpose="local LLM used by the recipe extraction service",
                install_hint="curl -fsSL https://ollama.com/install.sh | sh",
            ),
        ],
    ),
]


@dataclass(frozen=True)
class PreflightResult:
    missing: list[SystemDependency] = field(default_factory=list)
    stopped_at_tier: Optional[str] = None
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.missing


def check(
    which: Callable[[str], Optional[str]] = shutil.which,
    probe_ollama: Optional[Callable[[], bool]] = None,
    settings: Optional[Settings] = None,
) -> PreflightResult:
    for tier_name, deps in TIERS:
        missing = [dep for dep in deps if which(dep.command) is None]
        if missing:
            return PreflightResult(missing=missing, stopped_at_tier=tier_name)

    warnings: list[str] = []
    if probe_ollama is None:
        settings = settings or Settings.from_env()

        def probe_ollama() -> bool:
            # Imported lazily so httpx is not required for the hard checks.
            from little_meals.llm.ollama_client import OllamaClient

            client = OllamaClient(settings.ollama_base_url, settings.ollama_model, timeout_s=3.0)
            try:
                return client.is_available()
            finally:
                client.close()

    if not probe_ollama():
        warnings.append(
            "ollama is installed but its API did not respond at the configured URL. "
            "Start it with `ollama serve`, and make sure the model is pulled: "
            f"`ollama pull {(settings or Settings.from_env()).ollama_model}`."
        )

    return PreflightResult(missing=[], stopped_at_tier=None, warnings=warnings)


def format_report(result: PreflightResult) -> str:
    if result.ok and not result.warnings:
        return "All system dependencies are present."

    lines: list[str] = []
    if not result.ok:
        lines.append(f"Missing system dependencies (tier: {result.stopped_at_tier}):")
        for dep in result.missing:
            lines.append(f"  - {dep.command}: {dep.purpose}")
            lines.append(f"      install: {dep.install_hint}")
        lines.append("Resolve these, then re-run.")
    for warning in result.warnings:
        lines.append(f"warning: {warning}")
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    result = check()
    print(format_report(result))
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
