from __future__ import annotations

import random
from datetime import datetime, timezone

import pytest

from little_meals.models import Classification, HouseholdPreferences, Ingredient, Nutrition, Recipe
from little_meals.planning.plan_builder import (
    build_weekly_plan,
    generate_single_replacement,
    list_controlled_reroll_candidates,
)
from little_meals.store.recipe_store import RecipeStore


def _recipe(name: str) -> Recipe:
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
        created_at=now,
        updated_at=now,
    )


@pytest.mark.requirement("REQ-000000044")
def test_build_weekly_plan_fills_from_library_up_to_recipes_per_week(store: RecipeStore):
    store.create(_recipe("A"))
    store.create(_recipe("B"))
    preferences = HouseholdPreferences(recipes_per_week=2)

    generated = build_weekly_plan(store.list(), preferences, rng=random.Random(0))

    assert len(generated) == 2
    assert {g.recipe.name for g in generated} == {"A", "B"}


@pytest.mark.requirement("REQ-000000044")
def test_build_weekly_plan_yields_a_shorter_plan_when_library_has_too_few_recipes(store: RecipeStore):
    store.create(_recipe("Solo"))
    preferences = HouseholdPreferences(recipes_per_week=3)

    generated = build_weekly_plan(store.list(), preferences, rng=random.Random(0))

    assert len(generated) == 1


@pytest.mark.requirement("REQ-000000026")
def test_generate_single_replacement_prefers_unused_library_recipe(store: RecipeStore):
    store.create(_recipe("A"))
    store.create(_recipe("B"))
    recipes = store.list()

    replacement = generate_single_replacement(
        excluded_recipe_ids={r.id for r in recipes if r.name == "A"},
        recipes=recipes,
        rng=random.Random(0),
    )

    assert replacement is not None
    assert replacement.recipe.name == "B"


@pytest.mark.requirement("REQ-000000026")
def test_generate_single_replacement_returns_none_when_nothing_available(store: RecipeStore):
    store.create(_recipe("Solo"))
    recipes = store.list()

    replacement = generate_single_replacement(
        excluded_recipe_ids={r.id for r in recipes},
        recipes=recipes,
        rng=random.Random(0),
    )

    assert replacement is None


@pytest.mark.requirement("REQ-000000027")
def test_list_controlled_reroll_candidates_excludes_used(store: RecipeStore):
    store.create(_recipe("A"))
    store.create(_recipe("B"))
    store.create(_recipe("C"))
    recipes = store.list()
    used = {r.id for r in recipes if r.name == "A"}

    candidates = list_controlled_reroll_candidates(used, recipes)

    assert {c.name for c in candidates} == {"B", "C"}


@pytest.mark.requirement("REQ-000000027")
def test_list_controlled_reroll_candidates_caps_at_limit():
    recipes = [_recipe(f"R{i}") for i in range(15)]

    candidates = list_controlled_reroll_candidates(set(), recipes, limit=10, rng=random.Random(0))

    assert len(candidates) == 10
