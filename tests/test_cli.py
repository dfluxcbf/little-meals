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


def test_serve_calls_uvicorn_run_with_host_and_port(monkeypatch, tmp_path):
    # Isolate from the developer's real data directory - this reaches a
    # genuine create_app()/HouseholdPreferencesStore construction (unlike
    # the other `serve` tests below, which mock create_app or error out
    # before reaching it), so without this it reads/writes real household.db
    # and friends under ~/.local/share/little-meals.
    monkeypatch.setenv("LITTLE_MEALS_DATA_DIR", str(tmp_path))

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


def test_serve_data_dir_flag_is_converted_to_a_path(monkeypatch, tmp_path):
    # Regression test: --data-dir used to be passed straight through as the
    # raw CLI string, which crashed the first time anything did
    # `settings.data_dir / "recipes"` (str / str isn't valid).
    from little_meals.api import app as app_module

    captured = {}

    def fake_create_app(settings, enable_scheduler=False, **kwargs):
        captured["settings"] = settings
        return object()

    monkeypatch.setattr(app_module, "create_app", fake_create_app)

    import uvicorn

    monkeypatch.setattr(uvicorn, "run", lambda *a, **k: None)

    exit_code = cli_module.main(["serve", "--data-dir", str(tmp_path)])

    assert exit_code == 0
    from pathlib import Path

    assert captured["settings"].data_dir == Path(tmp_path)
    assert isinstance(captured["settings"].data_dir, Path)


def _seed_household_preferences(db_path, *, recipes_per_week):
    from datetime import time

    from little_meals.models import DayOfWeek, HouseholdPreferencesUpdate
    from little_meals.store.household_store import HouseholdPreferencesStore

    HouseholdPreferencesStore(db_path).put(
        HouseholdPreferencesUpdate(
            recipes_per_week=recipes_per_week,
            recommendation_enabled=True,
            recommendation_day=DayOfWeek.SUNDAY,
            recommendation_time=time(9, 0),
            auto_confirm_enabled=False,
            auto_confirm_day=DayOfWeek.SUNDAY,
            auto_confirm_time=time(9, 0),
            default_servings="2 adults",
        )
    )


def _seed_recipe(store, name: str = "Old Recipe"):
    from little_meals.models import Classification, Ingredient, Nutrition, Recipe

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
            created_at=now,
            updated_at=now,
        )
    )


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


def _settings_store(tmp_path):
    from little_meals.store.household_store import HouseholdPreferencesStore

    return HouseholdPreferencesStore(tmp_path / "household.db")


def test_settings_without_reset_flag_errors(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(Settings, "from_env", classmethod(lambda cls: Settings(data_dir=tmp_path)))
    exit_code = cli_module.main(["settings"])
    assert exit_code == 1
    assert "--reset" in capsys.readouterr().err


def test_settings_reset_resets_settings_but_keeps_recipes(monkeypatch, tmp_path, capsys):
    from datetime import time

    from little_meals.models import DayOfWeek, HouseholdPreferencesUpdate
    from little_meals.planning.shopping_list import MergedItem
    from little_meals.store.plan_store import MealPlanStore, MealSpec
    from little_meals.store.recipe_store import RecipeStore
    from little_meals.store.shopping_list_store import ShoppingListStore

    monkeypatch.setattr(Settings, "from_env", classmethod(lambda cls: Settings(data_dir=tmp_path)))

    household_store = _settings_store(tmp_path)
    household_store.put(
        HouseholdPreferencesUpdate(
            recipes_per_week=7,
            recommendation_enabled=True,
            recommendation_day=DayOfWeek.SUNDAY,
            recommendation_time=time(9, 0),
            auto_confirm_enabled=False,
            auto_confirm_day=DayOfWeek.SUNDAY,
            auto_confirm_time=time(9, 0),
            default_servings="2 adults",
        )
    )

    store = RecipeStore(tmp_path / "recipes")
    _seed_recipe(store)

    plan_store = MealPlanStore(tmp_path / "plan.db")
    plan = plan_store.create([MealSpec("recipe-a", 2)])
    shopping_store = ShoppingListStore(tmp_path / "shopping_list.db")
    shopping_store.create(plan.id, [MergedItem("Onion", 1.0, "piece")])

    monkeypatch.setattr("builtins.input", lambda prompt="": "y")

    exit_code = cli_module.main(["settings", "--reset"])

    assert exit_code == 0
    preferences = household_store.get()
    assert preferences.recipes_per_week == 5
    assert len(store.list()) == 1
    assert plan_store.count() == 0
    assert shopping_store.count() == 0
    out = capsys.readouterr().out
    assert "Deleted 1 meal plan(s) and 1 shopping list(s)" in out


def test_settings_reset_with_yes_skips_prompt(monkeypatch, tmp_path):
    monkeypatch.setattr(Settings, "from_env", classmethod(lambda cls: Settings(data_dir=tmp_path)))

    def fail_if_called(prompt=""):
        raise AssertionError("should not prompt when --yes is given")

    monkeypatch.setattr("builtins.input", fail_if_called)

    exit_code = cli_module.main(["settings", "--reset", "--yes"])
    assert exit_code == 0


def test_settings_reset_without_yes_aborts_on_no(monkeypatch, tmp_path, capsys):
    from little_meals.store.plan_store import MealPlanStore, MealSpec

    monkeypatch.setattr(Settings, "from_env", classmethod(lambda cls: Settings(data_dir=tmp_path)))
    _seed_household_preferences(tmp_path / "household.db", recipes_per_week=7)
    plan_store = MealPlanStore(tmp_path / "plan.db")
    plan_store.create([MealSpec("recipe-a", 2)])

    monkeypatch.setattr("builtins.input", lambda prompt="": "n")

    exit_code = cli_module.main(["settings", "--reset"])

    assert exit_code == 1
    assert "Aborted" in capsys.readouterr().err
    assert plan_store.count() == 1
    assert _settings_store(tmp_path).get().recipes_per_week == 7


def test_settings_reset_data_dir_flag_is_converted_to_a_path(monkeypatch, tmp_path):
    monkeypatch.setattr(Settings, "from_env", classmethod(lambda cls: Settings()))
    exit_code = cli_module.main(["settings", "--reset", "--yes", "--data-dir", str(tmp_path)])
    assert exit_code == 0
    assert (tmp_path / "household.db").exists()
