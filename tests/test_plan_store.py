from __future__ import annotations

import pytest

from little_meals.store.plan_store import MealPlanStore, PlanMealNotFound, PlanNotFound


def test_get_current_returns_none_when_no_plans_exist(plan_store: MealPlanStore):
    assert plan_store.get_current() is None


def test_create_stores_meals_in_order_with_generated_ids(plan_store: MealPlanStore):
    plan = plan_store.create([("recipe-a", 2), ("recipe-b", 4)])

    assert plan.finalized is False
    assert [meal.id for meal in plan.meals] == ["m1", "m2"]
    assert [meal.recipe_id for meal in plan.meals] == ["recipe-a", "recipe-b"]
    assert [meal.servings for meal in plan.meals] == [2, 4]
    assert all(meal.cooked is False for meal in plan.meals)


def test_create_with_no_recipes_still_creates_an_empty_plan(plan_store: MealPlanStore):
    plan = plan_store.create([])
    assert plan.meals == []


def test_get_current_returns_the_most_recently_created_plan(plan_store: MealPlanStore):
    plan_store.create([("recipe-a", 2)])
    second = plan_store.create([("recipe-b", 2)])

    current = plan_store.get_current()
    assert current is not None
    assert current.id == second.id


def test_get_unknown_plan_raises(plan_store: MealPlanStore):
    with pytest.raises(PlanNotFound):
        plan_store.get("does-not-exist")


def test_set_servings_updates_only_the_targeted_meal(plan_store: MealPlanStore):
    plan = plan_store.create([("recipe-a", 2), ("recipe-b", 4)])

    updated = plan_store.set_servings(plan.id, "m1", 6)

    assert updated.meals[0].servings == 6
    assert updated.meals[1].servings == 4


def test_set_servings_unknown_meal_raises(plan_store: MealPlanStore):
    plan = plan_store.create([("recipe-a", 2)])
    with pytest.raises(PlanMealNotFound):
        plan_store.set_servings(plan.id, "does-not-exist", 3)


def test_set_servings_unknown_plan_raises(plan_store: MealPlanStore):
    with pytest.raises(PlanNotFound):
        plan_store.set_servings("does-not-exist", "m1", 3)


def test_set_cooked_toggles_only_the_targeted_meal(plan_store: MealPlanStore):
    plan = plan_store.create([("recipe-a", 2), ("recipe-b", 4)])

    updated = plan_store.set_cooked(plan.id, "m2", True)

    assert updated.meals[0].cooked is False
    assert updated.meals[1].cooked is True


def test_finalize_marks_plan_finalized(plan_store: MealPlanStore):
    plan = plan_store.create([("recipe-a", 2)])
    assert plan.finalized is False

    finalized = plan_store.finalize(plan.id)
    assert finalized.finalized is True
    # Persisted, not just returned in-memory.
    assert plan_store.get(plan.id).finalized is True


def test_finalize_unknown_plan_raises(plan_store: MealPlanStore):
    with pytest.raises(PlanNotFound):
        plan_store.finalize("does-not-exist")
