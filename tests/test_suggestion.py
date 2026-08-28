from __future__ import annotations

import json
import random
from datetime import datetime, timezone

import httpx
import pytest

from little_meals.llm.extraction import RecipeExtractionService
from little_meals.llm.ollama_client import OllamaClient
from little_meals.models import Classification, Ingredient, Nutrition, Preference, Recipe
from little_meals.planning.suggestion import (
    NullSearchProvider,
    build_combination_text,
    generate_combination_suggestion,
    generate_search_suggestion,
)

VALID_EXTRACTED = {
    "name": "Fusion Bowl",
    "cook_time_minutes": 25,
    "classification": "vegetarian",
    "nutrition": {"calories_per_serving": 420},
    "servings": 2,
    "ingredients": [{"name": "rice", "quantity": 1, "unit": "cup"}],
    "steps": ["Cook it."],
}


def _recipe(name: str, preference: Preference = Preference.LIKED) -> Recipe:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return Recipe(
        id=name.lower().replace(" ", "-"),
        name=name,
        cook_time_minutes=20,
        classification=Classification.OTHER,
        nutrition=Nutrition(calories_per_serving=400),
        servings=2,
        ingredients=[Ingredient(name="something", quantity=1, unit="cup")],
        steps=["Cook it."],
        preference=preference,
        created_at=now,
        updated_at=now,
    )


def _extractor(handler) -> RecipeExtractionService:
    transport = httpx.MockTransport(handler)
    client = OllamaClient("http://ollama.test", "test-model", timeout_s=5.0, client=httpx.Client(transport=transport))
    return RecipeExtractionService(client)


def _ok_handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"response": json.dumps(VALID_EXTRACTED)})


def _bad_handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"response": json.dumps({"name": "incomplete"})})


@pytest.mark.requirement("REQ-000000023")
def test_null_search_provider_returns_no_results():
    assert NullSearchProvider().search("anything") == []


@pytest.mark.requirement("REQ-000000022")
def test_build_combination_text_includes_both_recipes():
    a = _recipe("Chicken Soup")
    b = _recipe("Veg Stir Fry")

    text = build_combination_text(a, b)

    assert "Chicken Soup" in text
    assert "Veg Stir Fry" in text
    assert "Cook it." in text


@pytest.mark.requirement("REQ-000000022")
def test_generate_combination_suggestion_returns_none_with_fewer_than_two_liked():
    assert generate_combination_suggestion([_recipe("Only One")], _extractor(_ok_handler)) is None
    assert generate_combination_suggestion([], _extractor(_ok_handler)) is None


@pytest.mark.requirement("REQ-000000022")
def test_generate_combination_suggestion_returns_extracted_recipe():
    liked = [_recipe("A"), _recipe("B"), _recipe("C")]

    result = generate_combination_suggestion(liked, _extractor(_ok_handler), rng=random.Random(0))

    assert result is not None
    assert result.name == "Fusion Bowl"


@pytest.mark.requirement("REQ-000000022")
def test_generate_combination_suggestion_ignores_disliked_pool_input():
    # The function trusts its caller to pre-filter to liked recipes; passing
    # a disliked one through just means it's eligible to be picked - this
    # documents that filtering happens one layer up (plan_builder).
    liked = [_recipe("A"), _recipe("B", Preference.DISLIKED)]
    result = generate_combination_suggestion(liked, _extractor(_ok_handler), rng=random.Random(0))
    assert result is not None


@pytest.mark.requirement("REQ-000000022")
def test_generate_combination_suggestion_returns_none_on_extraction_error():
    liked = [_recipe("A"), _recipe("B")]
    result = generate_combination_suggestion(liked, _extractor(_bad_handler), rng=random.Random(0))
    assert result is None


@pytest.mark.requirement("REQ-000000023")
def test_generate_search_suggestion_returns_none_with_no_results():
    result = generate_search_suggestion(NullSearchProvider(), "dinner", _extractor(_ok_handler))
    assert result is None


class _FakeSearchProvider:
    def __init__(self, results: list[str]):
        self._results = results

    def search(self, query: str) -> list[str]:
        return self._results


@pytest.mark.requirement("REQ-000000023")
def test_generate_search_suggestion_uses_first_result():
    provider = _FakeSearchProvider(["a promising recipe blurb"])
    result = generate_search_suggestion(provider, "dinner", _extractor(_ok_handler))
    assert result is not None
    assert result.name == "Fusion Bowl"


@pytest.mark.requirement("REQ-000000023")
def test_generate_search_suggestion_returns_none_on_extraction_error():
    provider = _FakeSearchProvider(["a promising recipe blurb"])
    result = generate_search_suggestion(provider, "dinner", _extractor(_bad_handler))
    assert result is None


class _ExplodingSearchProvider:
    def search(self, query: str) -> list[str]:
        raise RuntimeError("provider is down")


@pytest.mark.requirement("REQ-000000023")
def test_generate_search_suggestion_returns_none_when_provider_raises():
    result = generate_search_suggestion(_ExplodingSearchProvider(), "dinner", _extractor(_ok_handler))
    assert result is None
