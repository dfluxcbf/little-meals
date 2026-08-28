from __future__ import annotations

from pathlib import Path

from little_meals.config import Settings


def test_spoonacular_key_file_unset_by_default(monkeypatch):
    monkeypatch.delenv("LITTLE_MEALS_SPOONACULAR_KEY_FILE", raising=False)
    monkeypatch.delenv("LITTLE_MEALS_SPOONACULAR_API_KEY", raising=False)
    settings = Settings.from_env()
    assert settings.spoonacular_key_file is None
    assert settings.spoonacular_api_key is None


def test_spoonacular_key_file_read_from_env(monkeypatch):
    monkeypatch.setenv("LITTLE_MEALS_SPOONACULAR_KEY_FILE", "~/.vault/spoonacular.enc")
    settings = Settings.from_env()
    assert settings.spoonacular_key_file == Path("~/.vault/spoonacular.enc").expanduser()
