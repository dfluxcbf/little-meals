"""Sanity test for the little-runner server manifest (.lrun/config.toml).

Configuration, not code: it is exercised for real by `lrun server up little-meals`
(little-runner REQ-000000013/019). This only guards against the manifest drifting
from what the app actually is (entry point, port, tailscale mapping).
"""

from __future__ import annotations

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / ".lrun" / "config.toml"


def test_manifest_matches_the_app() -> None:
    data = tomllib.loads(MANIFEST.read_text(encoding="utf-8"))
    server = data["server"]
    assert server["name"] == "little-meals"
    assert server["command"] == "lmeals serve"                 # pyproject [project.scripts] lmeals
    assert server["port"] == 8765                              # uvicorn default in little_meals.cli
    assert server["match"].endswith("lmeals serve")
    assert server["install"] == ["bazel", "run", "//:install"]
    assert server["tailscale"]["https_port"] == 443
    assert data["issue"]["integration_branch"] == "dev"


def test_server_workflows_installed() -> None:
    workflows = REPO_ROOT / ".github" / "workflows"
    for name in ("claude-issue.yml", "server-up.yml", "server-down.yml"):
        text = (workflows / name).read_text(encoding="utf-8")
        assert "runs-on: [self-hosted, little-runner]" in text, name
