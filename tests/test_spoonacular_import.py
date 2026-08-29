from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from little_meals.llm.extraction import RecipeExtractionService
from little_meals.llm.ollama_client import OllamaClient
from little_meals.planning.spoonacular_import import import_recipes
from little_meals.store.recipe_store import RecipeStore

VALID_EXTRACTED = {
    "name": "Fusion Bowl",
    "cook_time_minutes": 25,
    "classification": "vegetarian",
    "nutrition": {"calories_per_serving": 420},
    "servings": 2,
    "ingredients": [{"name": "rice", "quantity": 1, "unit": "cup"}],
    "steps": ["Cook it."],
}


def _extractor(handler) -> RecipeExtractionService:
    transport = httpx.MockTransport(handler)
    client = OllamaClient("http://ollama.test", "test-model", timeout_s=5.0, client=httpx.Client(transport=transport))
    return RecipeExtractionService(client)


def _ok_handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"response": json.dumps(VALID_EXTRACTED)})


class _FakeProvider:
    def __init__(self, texts: list[str]):
        self._texts = texts

    def search_many(self, query, count) -> list[str]:
        return self._texts


@pytest.mark.requirement("REQ-000000041")
def test_import_recipes_stores_every_extracted_recipe(tmp_path: Path):
    provider = _FakeProvider(["Recipe text one", "Recipe text two"])
    store = RecipeStore(tmp_path / "recipes")

    result = import_recipes(provider, _extractor(_ok_handler), store, query={"query": "vegetarian"}, count=2)

    assert result.requested == 2
    assert result.found == 2
    assert result.skipped == 0
    assert len(result.imported) == 2
    assert {recipe.name for recipe in result.imported} == {"Fusion Bowl"}
    assert len(store.list()) == 2


@pytest.mark.requirement("REQ-000000041")
def test_import_recipes_skips_recipes_that_fail_extraction(tmp_path: Path):
    calls = {"n": 0}

    def flaky_handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(200, json={"response": json.dumps({"name": "incomplete"})})
        return _ok_handler(request)

    provider = _FakeProvider(["Bad recipe text", "Good recipe text"])
    store = RecipeStore(tmp_path / "recipes")

    result = import_recipes(provider, _extractor(flaky_handler), store, query=None, count=2)

    assert result.requested == 2
    assert result.found == 2
    assert result.skipped == 1
    assert len(result.imported) == 1
    assert len(store.list()) == 1


@pytest.mark.requirement("REQ-000000041")
def test_import_recipes_handles_no_results(tmp_path: Path):
    provider = _FakeProvider([])
    store = RecipeStore(tmp_path / "recipes")

    result = import_recipes(provider, _extractor(_ok_handler), store, query=None, count=5)

    assert result.requested == 5
    assert result.found == 0
    assert result.imported == []
    assert result.skipped == 0


@pytest.mark.requirement("REQ-000000041")
def test_import_recipes_found_reflects_a_search_shortfall_distinct_from_skipped(tmp_path: Path):
    """Spoonacular can legitimately return fewer candidates than requested
    (a narrow filter has few matches) with no error at all - `found` lets
    the CLI tell that apart from a candidate that failed extraction."""
    provider = _FakeProvider(["Recipe text one"])
    store = RecipeStore(tmp_path / "recipes")

    result = import_recipes(provider, _extractor(_ok_handler), store, query=None, count=20)

    assert result.requested == 20
    assert result.found == 1
    assert result.skipped == 0
    assert len(result.imported) == 1
