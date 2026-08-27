"""Tests that hit a real local Ollama daemon, not a mock.

Excluded from the default test run (see the `real_ollama` marker in
pytest.ini and the `tags = ["manual"]` real_ollama_tests target in
tests/BUILD.bazel) because they need `ollama serve` up with a model pulled.
Everything else in this suite mocks Ollama; this file exists to catch the
kind of drift a mock can't - e.g. Ollama's actual JSON-schema `format`
support, or a prompt that parses in theory but confuses the real model.

Run explicitly with:
    pytest -m real_ollama tests/test_ollama_client_real.py
    bazel test //tests:real_ollama_tests --test_output=all
"""

from __future__ import annotations

import pytest

from little_meals.config import Settings
from little_meals.llm.extraction import RecipeExtractionService
from little_meals.llm.ollama_client import OllamaClient
from little_meals.models import ExtractedRecipe

pytestmark = pytest.mark.real_ollama


@pytest.fixture
def real_client():
    settings = Settings.from_env()
    client = OllamaClient(settings.ollama_base_url, settings.ollama_model, settings.ollama_timeout_s)
    if not client.is_available():
        client.close()
        pytest.skip(f"Ollama not reachable at {settings.ollama_base_url} - is `ollama serve` running?")
    yield client
    client.close()


def test_real_ollama_is_reachable(real_client: OllamaClient):
    assert real_client.is_available() is True


def test_real_ollama_extracts_a_recipe_matching_the_schema(real_client: OllamaClient):
    service = RecipeExtractionService(real_client)

    result = service.extract(
        "Simple tomato soup: saute a chopped onion and two cloves of garlic, "
        "add a can of crushed tomatoes and a cup of vegetable broth, simmer "
        "for 15 minutes, then blend until smooth. Serves 2."
    )

    assert isinstance(result, ExtractedRecipe)
    assert result.name
    assert result.cook_time_minutes >= 1
    assert result.nutrition.calories_per_serving >= 0
    assert len(result.ingredients) >= 1
    assert len(result.steps) >= 1
