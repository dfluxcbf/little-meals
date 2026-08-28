"""Tests that hit the real Spoonacular API, not a mock.

Excluded from the default test run (see the `real_spoonacular` marker in
pytest.ini and the `tags = ["manual"]` real_spoonacular_tests target in
tests/BUILD.bazel) because they need a real LITTLE_MEALS_SPOONACULAR_API_KEY.
Everything else in this suite mocks Spoonacular; this file exists to catch
the kind of drift a mock can't - e.g. a real response shape Spoonacular
actually returns today, not what its docs say it returns.

Run explicitly with:
    LITTLE_MEALS_SPOONACULAR_API_KEY=... pytest -m real_spoonacular tests/test_spoonacular_provider_real.py
    bazel test //tests:real_spoonacular_tests --test_output=all --test_env=LITTLE_MEALS_SPOONACULAR_API_KEY
"""

from __future__ import annotations

import pytest

from little_meals.config import Settings
from little_meals.llm.extraction import RecipeExtractionService
from little_meals.llm.ollama_client import OllamaClient
from little_meals.planning.suggestion import SpoonacularSearchProvider

pytestmark = pytest.mark.real_spoonacular


@pytest.fixture
def real_provider():
    settings = Settings.from_env()
    if not settings.spoonacular_api_key:
        pytest.skip("LITTLE_MEALS_SPOONACULAR_API_KEY not set")
    provider = SpoonacularSearchProvider(
        settings.spoonacular_api_key,
        base_url=settings.spoonacular_base_url,
        timeout_s=settings.spoonacular_timeout_s,
    )
    yield provider
    provider.close()


def test_real_spoonacular_search_returns_recipe_text(real_provider: SpoonacularSearchProvider):
    results = real_provider.search("vegetarian pasta")

    assert len(results) == 1
    text = results[0]
    assert "Ingredients:" in text
    assert "Instructions:" in text
    assert len(text) > 50


def test_real_spoonacular_search_with_an_unlikely_query_returns_no_results_gracefully(
    real_provider: SpoonacularSearchProvider,
):
    # Not asserting == [] here - Spoonacular may still surface something for
    # an odd query - just that a genuinely obscure query doesn't raise.
    results = real_provider.search("xyzzy nonexistent dish qwertyuiop12345")
    assert isinstance(results, list)


def test_real_spoonacular_result_feeds_the_real_extraction_pipeline(real_provider: SpoonacularSearchProvider):
    """The end-to-end path generate_search_suggestion exercises: a real
    Spoonacular hit, fed into the real local extraction service. Needs both
    a Spoonacular key and a reachable Ollama daemon - skips cleanly if
    Ollama isn't up, since that's this test's second real dependency."""
    settings = Settings.from_env()
    ollama_client = OllamaClient(settings.ollama_base_url, settings.ollama_model, settings.ollama_timeout_s)
    if not ollama_client.is_available():
        ollama_client.close()
        pytest.skip(f"Ollama not reachable at {settings.ollama_base_url} - is `ollama serve` running?")

    results = real_provider.search("chicken soup")
    assert results, "expected at least one Spoonacular result for a common query"

    service = RecipeExtractionService(ollama_client)
    extracted = service.extract(results[0])
    ollama_client.close()

    assert extracted.name
    assert extracted.cook_time_minutes >= 1
    assert len(extracted.ingredients) >= 1
    assert len(extracted.steps) >= 1
