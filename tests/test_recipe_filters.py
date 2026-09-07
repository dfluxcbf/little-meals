from __future__ import annotations

from datetime import datetime, timezone

import pytest

from little_meals.models import Classification, Difficulty, Ingredient, Nutrition, Recipe
from little_meals.planning.recipe_filters import GlobScope, RecipeFilter, SortDirection, SortField, filter_recipes, sort_recipes


def _recipe(
    name: str,
    *,
    cook_time_minutes: int = 20,
    classification: Classification = Classification.OTHER,
    difficulty: Difficulty = Difficulty.UNDEFINED,
    calories: int | None = 400,
    protein: float | None = 20.0,
    fiber: float | None = 5.0,
    ingredients: list[Ingredient] | None = None,
    steps: list[str] | None = None,
) -> Recipe:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return Recipe(
        id=name.lower().replace(" ", "-"),
        name=name,
        cook_time_minutes=cook_time_minutes,
        classification=classification,
        difficulty=difficulty,
        nutrition=Nutrition(calories_per_serving=calories, protein_g=protein, fiber_g=fiber),
        servings=2,
        ingredients=ingredients or [Ingredient(name="something", quantity=1, unit="cup")],
        steps=steps or ["Cook it."],
        created_at=now,
        updated_at=now,
    )


REQ = "REQ-000000055"


@pytest.mark.requirement(REQ)
def test_no_criteria_passes_everything():
    recipes = [_recipe("A"), _recipe("B")]
    assert filter_recipes(recipes, RecipeFilter()) == recipes


@pytest.mark.requirement(REQ)
def test_min_calories_excludes_below_bound():
    recipes = [_recipe("Low", calories=100), _recipe("High", calories=500)]
    result = filter_recipes(recipes, RecipeFilter(min_calories=300))
    assert [r.name for r in result] == ["High"]


@pytest.mark.requirement(REQ)
def test_max_calories_excludes_above_bound():
    recipes = [_recipe("Low", calories=100), _recipe("High", calories=500)]
    result = filter_recipes(recipes, RecipeFilter(max_calories=300))
    assert [r.name for r in result] == ["Low"]


@pytest.mark.requirement(REQ)
def test_min_and_max_calories_combine_as_a_range():
    recipes = [_recipe("Low", calories=100), _recipe("Mid", calories=300), _recipe("High", calories=500)]
    result = filter_recipes(recipes, RecipeFilter(min_calories=200, max_calories=400))
    assert [r.name for r in result] == ["Mid"]


@pytest.mark.requirement(REQ)
def test_unknown_value_excluded_when_bound_is_set():
    recipes = [_recipe("Known", calories=300), _recipe("Unknown", calories=None)]
    result = filter_recipes(recipes, RecipeFilter(min_calories=100))
    assert [r.name for r in result] == ["Known"]


@pytest.mark.requirement(REQ)
def test_unknown_value_passes_when_no_bound_is_set():
    recipes = [_recipe("Known", calories=300), _recipe("Unknown", calories=None)]
    result = filter_recipes(recipes, RecipeFilter(min_protein=0))
    assert {r.name for r in result} == {"Known", "Unknown"}


@pytest.mark.requirement(REQ)
def test_protein_range():
    recipes = [_recipe("Low", protein=5.0), _recipe("High", protein=40.0)]
    result = filter_recipes(recipes, RecipeFilter(min_protein=10.0))
    assert [r.name for r in result] == ["High"]


@pytest.mark.requirement(REQ)
def test_fiber_range():
    recipes = [_recipe("Low", fiber=1.0), _recipe("High", fiber=10.0)]
    result = filter_recipes(recipes, RecipeFilter(max_fiber=5.0))
    assert [r.name for r in result] == ["Low"]


@pytest.mark.requirement(REQ)
def test_cook_time_range():
    recipes = [_recipe("Fast", cook_time_minutes=10), _recipe("Slow", cook_time_minutes=60)]
    result = filter_recipes(recipes, RecipeFilter(min_cook_time=30, max_cook_time=90))
    assert [r.name for r in result] == ["Slow"]


@pytest.mark.requirement(REQ)
def test_empty_classification_set_shows_all():
    recipes = [_recipe("Veg", classification=Classification.VEGETARIAN), _recipe("Other", classification=Classification.OTHER)]
    result = filter_recipes(recipes, RecipeFilter())
    assert len(result) == 2


@pytest.mark.requirement(REQ)
def test_classification_filter_restricts_to_selected_set():
    recipes = [
        _recipe("Veg", classification=Classification.VEGETARIAN),
        _recipe("Vegan", classification=Classification.VEGAN),
        _recipe("Other", classification=Classification.OTHER),
    ]
    result = filter_recipes(recipes, RecipeFilter(classifications=frozenset({Classification.VEGETARIAN, Classification.VEGAN})))
    assert {r.name for r in result} == {"Veg", "Vegan"}


@pytest.mark.requirement(REQ)
def test_empty_difficulty_set_shows_all():
    recipes = [_recipe("Easy", difficulty=Difficulty.EASY), _recipe("Hard", difficulty=Difficulty.HARD)]
    result = filter_recipes(recipes, RecipeFilter())
    assert len(result) == 2


@pytest.mark.requirement(REQ)
def test_difficulty_filter_restricts_to_selected_set():
    recipes = [_recipe("Easy", difficulty=Difficulty.EASY), _recipe("Hard", difficulty=Difficulty.HARD)]
    result = filter_recipes(recipes, RecipeFilter(difficulties=frozenset({Difficulty.EASY})))
    assert [r.name for r in result] == ["Easy"]


@pytest.mark.requirement(REQ)
def test_multiple_criteria_combine_with_and():
    recipes = [
        _recipe("Match", classification=Classification.VEGAN, calories=300),
        _recipe("Wrong classification", classification=Classification.OTHER, calories=300),
        _recipe("Wrong calories", classification=Classification.VEGAN, calories=900),
    ]
    result = filter_recipes(
        recipes, RecipeFilter(max_calories=500, classifications=frozenset({Classification.VEGAN}))
    )
    assert [r.name for r in result] == ["Match"]


@pytest.mark.requirement(REQ)
def test_sort_by_name_ascending_is_case_insensitive():
    recipes = [_recipe("banana"), _recipe("Apple"), _recipe("cherry")]
    result = sort_recipes(recipes, SortField.NAME, SortDirection.ASC)
    assert [r.name for r in result] == ["Apple", "banana", "cherry"]


@pytest.mark.requirement(REQ)
def test_sort_by_name_descending():
    recipes = [_recipe("banana"), _recipe("Apple"), _recipe("cherry")]
    result = sort_recipes(recipes, SortField.NAME, SortDirection.DESC)
    assert [r.name for r in result] == ["cherry", "banana", "Apple"]


@pytest.mark.requirement(REQ)
@pytest.mark.parametrize(
    "field_,attr",
    [
        (SortField.CALORIES, "calories"),
        (SortField.PROTEIN, "protein"),
        (SortField.FIBER, "fiber"),
    ],
)
def test_sort_by_nutrition_field_ascending_and_descending(field_, attr):
    recipes = [_recipe("Mid", **{attr: 50}), _recipe("Low", **{attr: 10}), _recipe("High", **{attr: 90})]
    asc = sort_recipes(recipes, field_, SortDirection.ASC)
    assert [r.name for r in asc] == ["Low", "Mid", "High"]
    desc = sort_recipes(recipes, field_, SortDirection.DESC)
    assert [r.name for r in desc] == ["High", "Mid", "Low"]


@pytest.mark.requirement(REQ)
def test_sort_by_cook_time():
    recipes = [_recipe("Slow", cook_time_minutes=60), _recipe("Fast", cook_time_minutes=10)]
    result = sort_recipes(recipes, SortField.COOK_TIME, SortDirection.ASC)
    assert [r.name for r in result] == ["Fast", "Slow"]


@pytest.mark.requirement(REQ)
def test_sort_missing_values_sort_last_ascending():
    recipes = [_recipe("Unknown", calories=None), _recipe("Known", calories=100)]
    result = sort_recipes(recipes, SortField.CALORIES, SortDirection.ASC)
    assert [r.name for r in result] == ["Known", "Unknown"]


@pytest.mark.requirement(REQ)
def test_sort_missing_values_sort_last_descending():
    recipes = [_recipe("Unknown", calories=None), _recipe("Known", calories=100)]
    result = sort_recipes(recipes, SortField.CALORIES, SortDirection.DESC)
    assert [r.name for r in result] == ["Known", "Unknown"]


GLOB_REQ = "REQ-000000063"


@pytest.mark.requirement(GLOB_REQ)
def test_blank_glob_pattern_matches_everything():
    recipes = [_recipe("Chicken Soup"), _recipe("Beef Stew")]
    result = filter_recipes(recipes, RecipeFilter(glob_pattern=""))
    assert len(result) == 2


@pytest.mark.requirement(GLOB_REQ)
def test_glob_scope_name_matches_only_recipe_name():
    recipes = [
        _recipe("Chicken Soup", ingredients=[Ingredient(name="broth", quantity=1, unit="cup")]),
        _recipe("Beef Stew", ingredients=[Ingredient(name="chicken stock", quantity=1, unit="cup")]),
    ]
    result = filter_recipes(recipes, RecipeFilter(glob_pattern="*chicken*", glob_scope=GlobScope.NAME))
    assert [r.name for r in result] == ["Chicken Soup"]


@pytest.mark.requirement(GLOB_REQ)
def test_glob_scope_ingredients_matches_any_ingredient_name():
    recipes = [
        _recipe("Soup", ingredients=[Ingredient(name="garlic clove", quantity=2, unit="piece")]),
        _recipe("Stew", ingredients=[Ingredient(name="beef", quantity=1, unit="kg")]),
    ]
    result = filter_recipes(recipes, RecipeFilter(glob_pattern="garlic*", glob_scope=GlobScope.INGREDIENTS))
    assert [r.name for r in result] == ["Soup"]


@pytest.mark.requirement(GLOB_REQ)
def test_glob_scope_steps_matches_any_step_text():
    recipes = [
        _recipe("Soup", steps=["Simmer for 20 minutes."]),
        _recipe("Stew", steps=["Roast the beef."]),
    ]
    result = filter_recipes(recipes, RecipeFilter(glob_pattern="*simmer*", glob_scope=GlobScope.STEPS))
    assert [r.name for r in result] == ["Soup"]


@pytest.mark.requirement(GLOB_REQ)
def test_glob_scope_all_matches_name_ingredients_or_steps():
    recipes = [
        _recipe("Garlic Soup"),
        _recipe("Beef Stew", ingredients=[Ingredient(name="garlic clove", quantity=1, unit="piece")]),
        _recipe("Chicken Bake", steps=["Add garlic and roast."]),
        _recipe("Plain Rice"),
    ]
    result = filter_recipes(recipes, RecipeFilter(glob_pattern="*garlic*", glob_scope=GlobScope.ALL))
    assert {r.name for r in result} == {"Garlic Soup", "Beef Stew", "Chicken Bake"}


@pytest.mark.requirement(GLOB_REQ)
def test_glob_pattern_is_case_insensitive():
    recipes = [_recipe("Chicken Soup")]
    result = filter_recipes(recipes, RecipeFilter(glob_pattern="CHICKEN*", glob_scope=GlobScope.NAME))
    assert len(result) == 1
