from __future__ import annotations

import little_meals.cli as cli_module
from little_meals import __version__


def test_version_flag_prints_version(capsys):
    try:
        cli_module.main(["--version"])
    except SystemExit as exc:
        assert exc.code == 0
    captured = capsys.readouterr()
    assert __version__ in captured.out


def test_serve_calls_uvicorn_run_with_host_and_port(monkeypatch):
    calls = {}

    def fake_run(app, host, port, reload, log_level):
        calls["host"] = host
        calls["port"] = port
        calls["reload"] = reload

    import uvicorn

    monkeypatch.setattr(uvicorn, "run", fake_run)

    exit_code = cli_module.main(["serve", "--host", "0.0.0.0", "--port", "9000"])
    assert exit_code == 0
    assert calls["host"] == "0.0.0.0"
    assert calls["port"] == 9000
    assert calls["reload"] is False


def test_preflight_subcommand_matches_preflight_main(monkeypatch, capsys):
    from little_meals import preflight as preflight_module

    monkeypatch.setattr(
        preflight_module,
        "check",
        lambda: preflight_module.PreflightResult(missing=[], stopped_at_tier=None, warnings=[]),
    )
    exit_code = cli_module.main(["preflight"])
    assert exit_code == 0


def test_no_subcommand_returns_nonzero(capsys):
    exit_code = cli_module.main([])
    assert exit_code != 0
