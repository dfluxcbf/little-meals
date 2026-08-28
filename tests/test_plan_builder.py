from __future__ import annotations

import json
import random
from datetime import datetime, timezone

import httpx
import pytest

from little_meals.llm.extraction import RecipeExtractionService
from little_meals.llm.ollama_client import OllamaClient
from little_meals.models import Classification, HouseholdPreferences, Ingredient, Nutrition, Preference, Recipe
from little_meals.planning.plan_builder import build_weekly_plan, generate_single_replacement, list_controlled_reroll_candidates
from little_meals.planning.suggestion import NullSearchProvider
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


@pytest.mark.requirement("REQ-000000024")
def test_build_weekly_plan_fills_from_library_when_no_ai_suggestions_requested(store: RecipeStore):
    store.create(_recipe("A"))
    store.create(_recipe("B"))
    preferences = HouseholdPreferences(recipes_per_week=2, ai_suggestions_per_plan=0)

    generated = build_weekly_plan(
        store.list(), preferences, store, _extractor(_ok_handler), NullSearchProvider(), rng=random.Random(0)
    )

    assert len(generated) == 2
    assert all(not g.is_suggestion for g in generated)


@pytest.mark.requirement("REQ-000000024")
def test_build_weekly_plan_reserves_slots_for_ai_suggestions(store: RecipeStore):
    for name in ["A", "B", "C", "D"]:
        store.create(_recipe(name))
    preferences = HouseholdPreferences(recipes_per_week=4, ai_suggestions_per_plan=1)

    generated = build_weekly_plan(
        store.list(), preferences, store, _extractor(_ok_handler), NullSearchProvider(), rng=random.Random(0)
    )

    # 3 library slots (4 - 1 reserved) + 1 generated suggestion.
    library_meals = [g for g in generated if not g.is_suggestion]
    suggestion_meals = [g for g in generated if g.is_suggestion]
    assert len(library_meals) == 3
    assert len(suggestion_meals) == 1
    assert suggestion_meals[0].recipe.name == "Fusion Bowl"
    # The suggestion was actually written into the library, liked by default.
    assert store.get(suggestion_meals[0].recipe.id).preference == Preference.LIKED


@pytest.mark.requirement("REQ-000000024")
def test_build_weekly_plan_skips_a_suggestion_slot_when_fewer_than_two_liked_recipes(store: RecipeStore):
    store.create(_recipe("Solo"))
    preferences = HouseholdPreferences(recipes_per_week=3, ai_suggestions_per_plan=2)

    generated = build_weekly_plan(
        store.list(), preferences, store, _extractor(_ok_handler), NullSearchProvider(), rng=random.Random(0)
    )

    # 1 library slot (only 1 liked recipe exists) + 0 suggestions (need >= 2 to combine).
    assert len(generated) == 1
    assert generated[0].is_suggestion is False


@pytest.mark.requirement("REQ-000000024")
def test_build_weekly_plan_uses_search_provider_when_it_has_results(store: RecipeStore):
    store.create(_recipe("A"))

    class _Provider:
        def search(self, query: str) -> list[str]:
            return ["a great dinner idea"]

    preferences = HouseholdPreferences(recipes_per_week=1, ai_suggestions_per_plan=1)
    generated = build_weekly_plan(store.list(), preferences, store, _extractor(_ok_handler), _Provider(), rng=random.Random(0))

    suggestion_meals = [g for g in generated if g.is_suggestion]
    assert len(suggestion_meals) == 1
    assert suggestion_meals[0].recipe.name == "Fusion Bowl"


@pytest.mark.requirement("REQ-000000026")
def test_generate_single_replacement_prefers_unused_library_recipe(store: RecipeStore):
    store.create(_recipe("A"))
    store.create(_recipe("B"))
    recipes = store.list()
    preferences = HouseholdPreferences()

    replacement = generate_single_replacement(
        excluded_recipe_ids={r.id for r in recipes if r.name == "A"},
        recipes=recipes,
        recipe_store=store,
        extractor=_extractor(_ok_handler),
        search_provider=NullSearchProvider(),
        preferences=preferences,
        rng=random.Random(0),
    )

    assert replacement is not None
    assert replacement.recipe.name == "B"
    assert replacement.is_suggestion is False


@pytest.mark.requirement("REQ-000000026")
def test_generate_single_replacement_falls_back_to_a_generated_suggestion(store: RecipeStore):
    store.create(_recipe("A"))
    store.create(_recipe("B"))
    recipes = store.list()
    preferences = HouseholdPreferences()

    # Both A and B are already "in use" in the plan, so nothing's left in
    # the library - falls back to combining them into something new.
    replacement = generate_single_replacement(
        excluded_recipe_ids={r.id for r in recipes},
        recipes=recipes,
        recipe_store=store,
        extractor=_extractor(_ok_handler),
        search_provider=NullSearchProvider(),
        preferences=preferences,
        rng=random.Random(0),
    )

    assert replacement is not None
    assert replacement.is_suggestion is True
    assert replacement.recipe.name == "Fusion Bowl"


@pytest.mark.requirement("REQ-000000026")
def test_generate_single_replacement_returns_none_when_nothing_available(store: RecipeStore):
    store.create(_recipe("Solo"))
    recipes = store.list()
    preferences = HouseholdPreferences()

    replacement = generate_single_replacement(
        excluded_recipe_ids={r.id for r in recipes},
        recipes=recipes,
        recipe_store=store,
        extractor=_extractor(_ok_handler),
        search_provider=NullSearchProvider(),
        preferences=preferences,
        rng=random.Random(0),
    )

    assert replacement is None


@pytest.mark.requirement("REQ-000000027")
def test_list_controlled_reroll_candidates_excludes_used_and_disliked(store: RecipeStore):
    store.create(_recipe("A"))
    store.create(_recipe("B"))
    store.create(_recipe("C", Preference.DISLIKED))
    recipes = store.list()
    used = {r.id for r in recipes if r.name == "A"}

    candidates = list_controlled_reroll_candidates(used, recipes)

    assert {c.name for c in candidates} == {"B"}


@pytest.mark.requirement("REQ-000000027")
def test_list_controlled_reroll_candidates_caps_at_limit():
    recipes = [_recipe(f"R{i}") for i in range(15)]

    candidates = list_controlled_reroll_candidates(set(), recipes, limit=10, rng=random.Random(0))

    assert len(candidates) == 10
