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


def test_serve_decrypts_spoonacular_key_when_key_file_configured(monkeypatch, tmp_path):
    from little_meals.config import Settings

    key_file = tmp_path / "spoonacular.enc"
    key_file.write_bytes(b"irrelevant - decrypt_key_file is mocked below")

    monkeypatch.setattr(Settings, "from_env", classmethod(lambda cls: Settings(spoonacular_key_file=key_file)))
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "the-passphrase")

    captured = {}

    def fake_decrypt_key_file(path, passphrase):
        captured["path"] = path
        captured["passphrase"] = passphrase
        return "the-real-api-key"

    monkeypatch.setattr("little_meals.vault.decrypt_key_file", fake_decrypt_key_file)

    from little_meals.api import app as app_module

    def fake_create_app(settings, enable_scheduler=False, **kwargs):
        captured["settings"] = settings
        return object()

    monkeypatch.setattr(app_module, "create_app", fake_create_app)

    import uvicorn

    monkeypatch.setattr(uvicorn, "run", lambda *a, **k: None)

    exit_code = cli_module.main(["serve"])

    assert exit_code == 0
    assert captured["path"] == key_file
    assert captured["passphrase"] == "the-passphrase"
    assert captured["settings"].spoonacular_api_key == "the-real-api-key"


def test_serve_returns_error_on_wrong_vault_passphrase(monkeypatch, tmp_path, capsys):
    from little_meals.config import Settings
    from little_meals.vault import VaultDecryptionFailed

    key_file = tmp_path / "spoonacular.enc"
    key_file.write_bytes(b"irrelevant - decrypt_key_file is mocked below")

    monkeypatch.setattr(Settings, "from_env", classmethod(lambda cls: Settings(spoonacular_key_file=key_file)))
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "wrong-passphrase")

    def fake_decrypt_key_file(path, passphrase):
        raise VaultDecryptionFailed("wrong passphrase")

    monkeypatch.setattr("little_meals.vault.decrypt_key_file", fake_decrypt_key_file)

    exit_code = cli_module.main(["serve"])

    assert exit_code == 1
    assert "wrong passphrase" in capsys.readouterr().err
