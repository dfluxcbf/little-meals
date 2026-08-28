from __future__ import annotations

from datetime import datetime, timezone

import little_meals.cli as cli_module
from little_meals import __version__
from little_meals.config import Settings


def test_version_flag_prints_version(capsys):
    try:
        cli_module.main(["--version"])
    except SystemExit as exc:
        assert exc.code == 0
    captured = capsys.readouterr()
    assert __version__ in captured.out


def test_serve_calls_uvicorn_run_with_host_and_port(monkeypatch):
    # Isolate from whatever the developer's own shell has exported (e.g. a
    # real vault key file) - otherwise this test would try to prompt for a
    # real passphrase via getpass and fail under pytest's captured stdin.
    monkeypatch.delenv("LITTLE_MEALS_SPOONACULAR_KEY_FILE", raising=False)
    monkeypatch.delenv("LITTLE_MEALS_SPOONACULAR_API_KEY", raising=False)

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


def test_serve_decrypts_spoonacular_key_when_key_file_configured(monkeypatch, tmp_path):
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


def test_import_spoonacular_returns_error_when_no_api_key_configured(monkeypatch, capsys):
    monkeypatch.delenv("LITTLE_MEALS_SPOONACULAR_KEY_FILE", raising=False)
    monkeypatch.delenv("LITTLE_MEALS_SPOONACULAR_API_KEY", raising=False)

    exit_code = cli_module.main(["import-spoonacular"])

    assert exit_code == 1
    assert "no Spoonacular API key configured" in capsys.readouterr().err


def test_import_spoonacular_returns_error_on_wrong_vault_passphrase(monkeypatch, tmp_path, capsys):
    from little_meals.vault import VaultDecryptionFailed

    key_file = tmp_path / "spoonacular.enc"
    key_file.write_bytes(b"irrelevant - decrypt_key_file is mocked below")

    monkeypatch.setattr(Settings, "from_env", classmethod(lambda cls: Settings(spoonacular_key_file=key_file)))
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "wrong-passphrase")

    def fake_decrypt_key_file(path, passphrase):
        raise VaultDecryptionFailed("wrong passphrase")

    monkeypatch.setattr("little_meals.vault.decrypt_key_file", fake_decrypt_key_file)

    exit_code = cli_module.main(["import-spoonacular"])

    assert exit_code == 1
    assert "wrong passphrase" in capsys.readouterr().err


def _seed_household_preferences(db_path, *, recipes_per_week, food_preferences):
    from datetime import time

    from little_meals.models import DayOfWeek, HouseholdPreferencesUpdate
    from little_meals.store.household_store import HouseholdPreferencesStore

    HouseholdPreferencesStore(db_path).put(
        HouseholdPreferencesUpdate(
            recipes_per_week=recipes_per_week,
            recommendation_day=DayOfWeek.SUNDAY,
            recommendation_time=time(9, 0),
            food_preferences=food_preferences,
            ai_suggestions_per_plan=2,
            default_servings="2 adults",
        )
    )


def test_import_spoonacular_uses_household_preferences_and_reports_summary(monkeypatch, tmp_path, capsys):
    import little_meals.planning.spoonacular_import as import_module

    monkeypatch.setattr(
        Settings, "from_env", classmethod(lambda cls: Settings(spoonacular_api_key="test-key", data_dir=tmp_path))
    )
    _seed_household_preferences(tmp_path / "household.db", recipes_per_week=4, food_preferences=["vegetarian", "spicy"])

    captured = {}

    def fake_import_recipes(provider, extractor, store, *, query, count):
        captured["query"] = query
        captured["count"] = count
        return import_module.ImportResult(requested=count, imported=[object(), object()], skipped=1)

    monkeypatch.setattr(import_module, "import_recipes", fake_import_recipes)

    exit_code = cli_module.main(["import-spoonacular"])

    assert exit_code == 0
    assert captured["query"] == "vegetarian spicy"
    assert captured["count"] == 4
    out = capsys.readouterr().out
    assert "Imported 2 of 4 requested recipe(s)" in out
    assert "1 skipped" in out


def test_import_spoonacular_count_flag_overrides_household_default(monkeypatch, tmp_path):
    import little_meals.planning.spoonacular_import as import_module

    monkeypatch.setattr(
        Settings, "from_env", classmethod(lambda cls: Settings(spoonacular_api_key="test-key", data_dir=tmp_path))
    )
    _seed_household_preferences(tmp_path / "household.db", recipes_per_week=4, food_preferences=[])

    captured = {}

    def fake_import_recipes(provider, extractor, store, *, query, count):
        captured["count"] = count
        return import_module.ImportResult(requested=count, imported=[object()])

    monkeypatch.setattr(import_module, "import_recipes", fake_import_recipes)

    exit_code = cli_module.main(["import-spoonacular", "--count", "7"])

    assert exit_code == 0
    assert captured["count"] == 7


def test_import_spoonacular_returns_error_when_nothing_imported(monkeypatch, tmp_path, capsys):
    import little_meals.planning.spoonacular_import as import_module

    monkeypatch.setattr(
        Settings, "from_env", classmethod(lambda cls: Settings(spoonacular_api_key="test-key", data_dir=tmp_path))
    )
    _seed_household_preferences(tmp_path / "household.db", recipes_per_week=3, food_preferences=[])

    monkeypatch.setattr(
        import_module, "import_recipes", lambda *a, **k: import_module.ImportResult(requested=3, skipped=3)
    )

    exit_code = cli_module.main(["import-spoonacular"])

    assert exit_code == 1
    assert "Imported 0 of 3 requested recipe(s)" in capsys.readouterr().out


def _seed_recipe(store, name: str = "Old Recipe"):
    from little_meals.models import Classification, Ingredient, Nutrition, Preference, Recipe

    now = datetime.now(timezone.utc)
    return store.create(
        Recipe(
            id="",
            name=name,
            cook_time_minutes=10,
            classification=Classification.OTHER,
            nutrition=Nutrition(calories_per_serving=100),
            ingredients=[Ingredient(name="salt")],
            steps=["Do it."],
            preference=Preference.LIKED,
            created_at=now,
            updated_at=now,
        )
    )


def test_import_spoonacular_reset_deletes_recipes_then_imports(monkeypatch, tmp_path, capsys):
    import little_meals.planning.spoonacular_import as import_module
    from little_meals.store.recipe_store import RecipeStore

    monkeypatch.setattr(
        Settings, "from_env", classmethod(lambda cls: Settings(spoonacular_api_key="test-key", data_dir=tmp_path))
    )
    _seed_household_preferences(tmp_path / "household.db", recipes_per_week=2, food_preferences=[])

    store = RecipeStore(tmp_path / "recipes")
    _seed_recipe(store)
    assert store.count() == 1

    monkeypatch.setattr(
        import_module, "import_recipes", lambda *a, **k: import_module.ImportResult(requested=2, imported=[object()])
    )

    exit_code = cli_module.main(["import-spoonacular", "--reset", "--yes"])

    assert exit_code == 0
    assert store.count() == 0
    out = capsys.readouterr().out
    assert "Deleted 1 recipe(s)" in out


def test_import_spoonacular_reset_without_yes_prompts_and_aborts_on_no(monkeypatch, tmp_path, capsys):
    import little_meals.planning.spoonacular_import as import_module
    from little_meals.store.recipe_store import RecipeStore

    monkeypatch.setattr(
        Settings, "from_env", classmethod(lambda cls: Settings(spoonacular_api_key="test-key", data_dir=tmp_path))
    )
    _seed_household_preferences(tmp_path / "household.db", recipes_per_week=2, food_preferences=[])

    store = RecipeStore(tmp_path / "recipes")
    _seed_recipe(store)

    monkeypatch.setattr("builtins.input", lambda prompt="": "n")
    import_called = {"called": False}

    def fake_import_recipes(*a, **k):
        import_called["called"] = True
        return import_module.ImportResult(requested=2)

    monkeypatch.setattr(import_module, "import_recipes", fake_import_recipes)

    exit_code = cli_module.main(["import-spoonacular", "--reset"])

    assert exit_code == 1
    assert store.count() == 1
    assert import_called["called"] is False
    assert "Aborted" in capsys.readouterr().err


def test_import_spoonacular_reset_on_empty_library_skips_prompt(monkeypatch, tmp_path, capsys):
    import little_meals.planning.spoonacular_import as import_module

    monkeypatch.setattr(
        Settings, "from_env", classmethod(lambda cls: Settings(spoonacular_api_key="test-key", data_dir=tmp_path))
    )
    _seed_household_preferences(tmp_path / "household.db", recipes_per_week=2, food_preferences=[])

    def fail_if_called(prompt=""):
        raise AssertionError("should not prompt when there is nothing to delete")

    monkeypatch.setattr("builtins.input", fail_if_called)
    monkeypatch.setattr(
        import_module, "import_recipes", lambda *a, **k: import_module.ImportResult(requested=2, imported=[object()])
    )

    exit_code = cli_module.main(["import-spoonacular", "--reset"])

    assert exit_code == 0
    assert "No recipes to delete." in capsys.readouterr().out


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
