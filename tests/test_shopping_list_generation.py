from __future__ import annotations

from datetime import datetime, timezone

from little_meals.models import Classification, Ingredient, MealPlan, Nutrition, PlanMeal, Recipe
from little_meals.planning.shopping_list import build_shopping_list_items
from little_meals.store.recipe_store import RecipeStore


def _recipe(name: str, servings: int, ingredients: list[Ingredient]) -> Recipe:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return Recipe(
        id="",
        name=name,
        cook_time_minutes=20,
        classification=Classification.OTHER,
        nutrition=Nutrition(calories_per_serving=400),
        servings=servings,
        ingredients=ingredients,
        steps=["Cook it."],
        created_at=now,
        updated_at=now,
    )


def _plan(meals: list[PlanMeal]) -> MealPlan:
    return MealPlan(id="p1", created_at=datetime(2026, 1, 1, tzinfo=timezone.utc), finalized=True, meals=meals)


def test_scales_quantities_to_meal_servings(store: RecipeStore):
    recipe = store.create(_recipe("Soup", servings=2, ingredients=[Ingredient(name="Carrot", quantity=2, unit="pieces")]))
    plan = _plan([PlanMeal(id="m1", recipe_id=recipe.id, servings=4)])

    items = build_shopping_list_items(plan, store)

    assert len(items) == 1
    assert items[0].name == "Carrot"
    assert items[0].quantity == 4.0  # 2 pieces for 2 servings -> 4 for 4 servings
    assert items[0].unit == "pieces"


def test_merges_same_name_and_unit_across_meals(store: RecipeStore):
    a = store.create(_recipe("A", servings=2, ingredients=[Ingredient(name="Garlic", quantity=2, unit="cloves")]))
    b = store.create(_recipe("B", servings=2, ingredients=[Ingredient(name="garlic", quantity=3, unit="Cloves")]))
    plan = _plan([PlanMeal(id="m1", recipe_id=a.id, servings=2), PlanMeal(id="m2", recipe_id=b.id, servings=2)])

    items = build_shopping_list_items(plan, store)

    assert len(items) == 1
    assert items[0].quantity == 5.0


def test_keeps_mismatched_units_as_separate_lines(store: RecipeStore):
    a = store.create(_recipe("A", servings=2, ingredients=[Ingredient(name="Flour", quantity=2, unit="cups")]))
    b = store.create(_recipe("B", servings=2, ingredients=[Ingredient(name="Flour", quantity=500, unit="g")]))
    plan = _plan([PlanMeal(id="m1", recipe_id=a.id, servings=2), PlanMeal(id="m2", recipe_id=b.id, servings=2)])

    items = build_shopping_list_items(plan, store)

    assert len(items) == 2
    units = {item.unit for item in items}
    assert units == {"cups", "g"}


def test_ingredients_with_no_quantity_are_deduplicated_by_name(store: RecipeStore):
    a = store.create(_recipe("A", servings=2, ingredients=[Ingredient(name="Salt", quantity=None, unit=None)]))
    b = store.create(_recipe("B", servings=2, ingredients=[Ingredient(name="Salt", quantity=None, unit=None)]))
    plan = _plan([PlanMeal(id="m1", recipe_id=a.id, servings=2), PlanMeal(id="m2", recipe_id=b.id, servings=2)])

    items = build_shopping_list_items(plan, store)

    assert len(items) == 1
    assert items[0].quantity is None


def test_preserves_first_appearance_order(store: RecipeStore):
    recipe = store.create(
        _recipe(
            "Multi",
            servings=2,
            ingredients=[
                Ingredient(name="Zucchini", quantity=1, unit="piece"),
                Ingredient(name="Apple", quantity=1, unit="piece"),
            ],
        )
    )
    plan = _plan([PlanMeal(id="m1", recipe_id=recipe.id, servings=2)])

    items = build_shopping_list_items(plan, store)

    assert [item.name for item in items] == ["Zucchini", "Apple"]


def test_skips_meals_whose_recipe_was_deleted(store: RecipeStore):
    recipe = store.create(_recipe("Gone", servings=2, ingredients=[Ingredient(name="X", quantity=1, unit="g")]))
    store.delete(recipe.id)
    plan = _plan([PlanMeal(id="m1", recipe_id=recipe.id, servings=2)])

    items = build_shopping_list_items(plan, store)

    assert items == []


def test_empty_plan_yields_empty_list(store: RecipeStore):
    plan = _plan([])
    assert build_shopping_list_items(plan, store) == []
