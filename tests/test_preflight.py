from __future__ import annotations

import pytest

from little_meals.preflight import check, format_report, main


def _which_all_present(command: str):
    return f"/usr/bin/{command}"


@pytest.mark.requirement("REQ-000000008")
def test_all_present_is_ok():
    result = check(which=_which_all_present, probe_ollama=lambda: True, is_wsl=lambda: False)
    assert result.ok
    assert result.missing == []
    assert result.stopped_at_tier is None


def test_ollama_missing_is_reported_with_install_hint():
    def which(command: str):
        if command == "ollama":
            return None
        return f"/usr/bin/{command}"

    result = check(which=which, probe_ollama=lambda: True, is_wsl=lambda: False)
    assert not result.ok
    assert [dep.command for dep in result.missing] == ["ollama"]
    assert result.stopped_at_tier == "local LLM runtime"

    report = format_report(result)
    assert "curl -fsSL https://ollama.com/install.sh | sh" in report


def test_two_missing_in_same_tier_are_both_reported_in_one_pass():
    def which(command: str):
        return None  # nothing on PATH

    result = check(which=which, probe_ollama=lambda: True, is_wsl=lambda: False)
    assert not result.ok
    assert {dep.command for dep in result.missing} == {"python3", "pipx"}
    assert result.stopped_at_tier == "core tools"


def test_tier_one_missing_stops_before_tier_two_is_evaluated():
    probe_calls = {"count": 0}

    def which(command: str):
        return None

    def probe_ollama() -> bool:
        probe_calls["count"] += 1
        return True

    result = check(which=which, probe_ollama=probe_ollama, is_wsl=lambda: False)
    assert result.stopped_at_tier == "core tools"
    assert probe_calls["count"] == 0


def test_ollama_present_but_daemon_down_is_ok_with_warning():
    result = check(which=_which_all_present, probe_ollama=lambda: False, is_wsl=lambda: False)
    assert result.ok
    assert result.warnings
    assert "ollama serve" in result.warnings[0]


def test_main_returns_0_when_ok(monkeypatch, capsys):
    monkeypatch.setattr(
        "little_meals.preflight.check",
        lambda: check(which=_which_all_present, probe_ollama=lambda: True, is_wsl=lambda: False),
    )
    assert main() == 0


def test_main_returns_1_when_missing(monkeypatch, capsys):
    def which(command: str):
        return None

    monkeypatch.setattr(
        "little_meals.preflight.check",
        lambda: check(which=which, probe_ollama=lambda: True, is_wsl=lambda: False),
    )
    assert main() == 1


def test_wsl_skips_which_and_checks_ollama_over_curl_instead():
    def which(command: str):
        if command == "ollama":
            return None  # not on the WSL PATH even though it's reachable
        return f"/usr/bin/{command}"

    result = check(which=which, probe_ollama=lambda: True, is_wsl=lambda: True, ollama_reachable=lambda: True)
    assert result.ok
    assert result.missing == []


def test_wsl_ollama_unreachable_is_reported_with_wsl_hint():
    result = check(
        which=_which_all_present,
        probe_ollama=lambda: True,
        is_wsl=lambda: True,
        ollama_reachable=lambda: False,
    )
    assert not result.ok
    assert [dep.command for dep in result.missing] == ["ollama"]
    assert result.stopped_at_tier == "local LLM runtime"

    report = format_report(result)
    assert "curl http://127.0.0.1:11434/api/tags" in report
    assert "install.sh" not in report
