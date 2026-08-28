from __future__ import annotations

import pytest

import random
from datetime import datetime, timezone

from little_meals.models import Classification, Ingredient, Nutrition, Preference, Recipe
from little_meals.planning.selection import select_recipes_for_plan


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


@pytest.mark.requirement("REQ-000000018")
def test_excludes_disliked_recipes():
    recipes = [_recipe("Liked One"), _recipe("Disliked One", Preference.DISLIKED)]

    selected = select_recipes_for_plan(recipes, recipes_per_week=5)

    assert [r.name for r in selected] == ["Liked One"]


@pytest.mark.requirement("REQ-000000018")
def test_caps_at_recipes_per_week():
    recipes = [_recipe(f"Recipe {i}") for i in range(10)]

    selected = select_recipes_for_plan(recipes, recipes_per_week=3, rng=random.Random(0))

    assert len(selected) == 3
    # Every selected recipe actually came from the liked pool.
    assert set(r.id for r in selected) <= set(r.id for r in recipes)


@pytest.mark.requirement("REQ-000000018")
def test_returns_all_liked_recipes_when_fewer_than_recipes_per_week():
    recipes = [_recipe("Only One")]

    selected = select_recipes_for_plan(recipes, recipes_per_week=5)

    assert [r.name for r in selected] == ["Only One"]


@pytest.mark.requirement("REQ-000000018")
def test_empty_library_yields_empty_plan():
    assert select_recipes_for_plan([], recipes_per_week=5) == []


@pytest.mark.requirement("REQ-000000018")
def test_negative_recipes_per_week_is_treated_as_zero():
    recipes = [_recipe("A"), _recipe("B")]
    assert select_recipes_for_plan(recipes, recipes_per_week=-1) == []


@pytest.mark.requirement("REQ-000000018")
def test_selection_is_randomized_across_calls_with_different_rngs():
    recipes = [_recipe(f"Recipe {i}") for i in range(20)]

    first = {r.id for r in select_recipes_for_plan(recipes, recipes_per_week=5, rng=random.Random(1))}
    second = {r.id for r in select_recipes_for_plan(recipes, recipes_per_week=5, rng=random.Random(2))}

    assert first != second
