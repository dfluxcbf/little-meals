from __future__ import annotations

import pytest

from little_meals.preflight import check, format_report, main


def _which_all_present(command: str):
    return f"/usr/bin/{command}"


@pytest.mark.requirement("REQ-000000008")
def test_all_present_is_ok():
    result = check(which=_which_all_present)
    assert result.ok
    assert result.missing == []
    assert result.stopped_at_tier is None


def test_missing_dependency_is_reported_with_install_hint():
    def which(command: str):
        if command == "pipx":
            return None
        return f"/usr/bin/{command}"

    result = check(which=which)
    assert not result.ok
    assert [dep.command for dep in result.missing] == ["pipx"]
    assert result.stopped_at_tier == "core tools"

    report = format_report(result)
    assert "pipx" in report


def test_two_missing_in_same_tier_are_both_reported_in_one_pass():
    def which(command: str):
        return None  # nothing on PATH

    result = check(which=which)
    assert not result.ok
    assert {dep.command for dep in result.missing} == {"python3", "pipx"}
    assert result.stopped_at_tier == "core tools"


def test_main_returns_0_when_ok(monkeypatch, capsys):
    monkeypatch.setattr("little_meals.preflight.check", lambda: check(which=_which_all_present))
    assert main() == 0


def test_main_returns_1_when_missing(monkeypatch, capsys):
    def which(command: str):
        return None

    monkeypatch.setattr("little_meals.preflight.check", lambda: check(which=which))
    assert main() == 1
