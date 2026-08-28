from __future__ import annotations

from pathlib import Path

import pytest

from little_meals.api.app import create_app
from little_meals.config import Settings
from little_meals.planning.suggestion import NullSearchProvider, SpoonacularSearchProvider


@pytest.mark.requirement("REQ-000000038")
def test_defaults_to_null_search_provider_without_an_api_key(tmp_path: Path):
    app = create_app(settings=Settings(data_dir=tmp_path))
    assert isinstance(app.state.search_provider, NullSearchProvider)


@pytest.mark.requirement("REQ-000000038")
def test_uses_spoonacular_when_api_key_configured(tmp_path: Path):
    app = create_app(settings=Settings(data_dir=tmp_path, spoonacular_api_key="a-real-key"))
    assert isinstance(app.state.search_provider, SpoonacularSearchProvider)


@pytest.mark.requirement("REQ-000000038")
def test_explicit_search_provider_argument_overrides_settings(tmp_path: Path):
    # An explicitly-passed search_provider (as tests elsewhere do) wins
    # regardless of what's configured in Settings.
    explicit = NullSearchProvider()
    app = create_app(
        settings=Settings(data_dir=tmp_path, spoonacular_api_key="a-real-key"),
        search_provider=explicit,
    )
    assert app.state.search_provider is explicit
