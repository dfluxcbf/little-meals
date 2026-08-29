from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from little_meals.store.plan_store import MealPlanStore, MealSpec, PlanMealNotFound, PlanNotFound


@pytest.mark.requirement("REQ-000000019")
def test_get_current_returns_none_when_no_plans_exist(plan_store: MealPlanStore):
    assert plan_store.get_current() is None


@pytest.mark.requirement("REQ-000000019")
def test_create_stores_meals_in_order_with_generated_ids(plan_store: MealPlanStore):
    plan = plan_store.create([MealSpec("recipe-a", 2), MealSpec("recipe-b", 4, is_suggestion=True)])

    assert plan.finalized is False
    assert [meal.id for meal in plan.meals] == ["m1", "m2"]
    assert [meal.recipe_id for meal in plan.meals] == ["recipe-a", "recipe-b"]
    assert [meal.servings for meal in plan.meals] == [2, 4]
    assert [meal.is_suggestion for meal in plan.meals] == [False, True]
    assert all(meal.cooked is False for meal in plan.meals)


@pytest.mark.requirement("REQ-000000019")
def test_create_with_no_recipes_still_creates_an_empty_plan(plan_store: MealPlanStore):
    plan = plan_store.create([])
    assert plan.meals == []


@pytest.mark.requirement("REQ-000000019")
def test_get_current_returns_the_most_recently_created_plan(plan_store: MealPlanStore):
    plan_store.create([MealSpec("recipe-a", 2)])
    second = plan_store.create([MealSpec("recipe-b", 2)])

    current = plan_store.get_current()
    assert current is not None
    assert current.id == second.id


@pytest.mark.requirement("REQ-000000019")
def test_get_unknown_plan_raises(plan_store: MealPlanStore):
    with pytest.raises(PlanNotFound):
        plan_store.get("does-not-exist")


@pytest.mark.requirement("REQ-000000019")
def test_set_servings_updates_only_the_targeted_meal(plan_store: MealPlanStore):
    plan = plan_store.create([MealSpec("recipe-a", 2), MealSpec("recipe-b", 4)])

    updated = plan_store.set_servings(plan.id, "m1", 6)

    assert updated.meals[0].servings == 6
    assert updated.meals[1].servings == 4


@pytest.mark.requirement("REQ-000000019")
def test_set_servings_unknown_meal_raises(plan_store: MealPlanStore):
    plan = plan_store.create([MealSpec("recipe-a", 2)])
    with pytest.raises(PlanMealNotFound):
        plan_store.set_servings(plan.id, "does-not-exist", 3)


@pytest.mark.requirement("REQ-000000019")
def test_set_servings_unknown_plan_raises(plan_store: MealPlanStore):
    with pytest.raises(PlanNotFound):
        plan_store.set_servings("does-not-exist", "m1", 3)


@pytest.mark.requirement("REQ-000000019")
def test_set_cooked_toggles_only_the_targeted_meal(plan_store: MealPlanStore):
    plan = plan_store.create([MealSpec("recipe-a", 2), MealSpec("recipe-b", 4)])

    updated = plan_store.set_cooked(plan.id, "m2", True)

    assert updated.meals[0].cooked is False
    assert updated.meals[1].cooked is True


@pytest.mark.requirement("REQ-000000019")
def test_set_recipe_replaces_a_single_meal_and_resets_cooked(plan_store: MealPlanStore):
    plan = plan_store.create([MealSpec("recipe-a", 2)])
    plan_store.set_cooked(plan.id, "m1", True)

    updated = plan_store.set_recipe(plan.id, "m1", "recipe-z", 3, is_suggestion=True)

    meal = updated.meals[0]
    assert meal.recipe_id == "recipe-z"
    assert meal.servings == 3
    assert meal.is_suggestion is True
    assert meal.cooked is False


@pytest.mark.requirement("REQ-000000019")
def test_set_recipe_unknown_meal_raises(plan_store: MealPlanStore):
    plan = plan_store.create([MealSpec("recipe-a", 2)])
    with pytest.raises(PlanMealNotFound):
        plan_store.set_recipe(plan.id, "does-not-exist", "recipe-z", 2)


@pytest.mark.requirement("REQ-000000019")
def test_set_recipe_unknown_plan_raises(plan_store: MealPlanStore):
    with pytest.raises(PlanNotFound):
        plan_store.set_recipe("does-not-exist", "m1", "recipe-z", 2)


def test_create_records_candidate_recipe_ids_for_a_suggestion_slot(plan_store: MealPlanStore):
    plan = plan_store.create(
        [MealSpec("recipe-a", 2, is_suggestion=True, candidate_recipe_ids=("recipe-a", "recipe-b", "recipe-c"))]
    )
    assert plan_store.get_candidates(plan.id, "m1") == ["recipe-a", "recipe-b", "recipe-c"]


def test_get_candidates_returns_empty_list_when_none_recorded(plan_store: MealPlanStore):
    plan = plan_store.create([MealSpec("recipe-a", 2)])
    assert plan_store.get_candidates(plan.id, "m1") == []


def test_set_recipe_replaces_the_candidate_set(plan_store: MealPlanStore):
    plan = plan_store.create(
        [MealSpec("recipe-a", 2, is_suggestion=True, candidate_recipe_ids=("recipe-a", "recipe-b"))]
    )

    plan_store.set_recipe(plan.id, "m1", "recipe-b", 2, is_suggestion=True, candidate_recipe_ids=("recipe-a", "recipe-b"))
    assert plan_store.get_candidates(plan.id, "m1") == ["recipe-a", "recipe-b"]


def test_set_recipe_default_clears_stale_candidates(plan_store: MealPlanStore):
    # e.g. "select from cookbook" replacing a suggestion slot - the old
    # Spoonacular candidates no longer apply to this slot.
    plan = plan_store.create(
        [MealSpec("recipe-a", 2, is_suggestion=True, candidate_recipe_ids=("recipe-a", "recipe-b"))]
    )

    plan_store.set_recipe(plan.id, "m1", "recipe-z", 2, is_suggestion=False)
    assert plan_store.get_candidates(plan.id, "m1") == []


def test_replace_meals_clears_candidates_from_the_previous_meal_set(plan_store: MealPlanStore):
    plan = plan_store.create(
        [MealSpec("recipe-a", 2, is_suggestion=True, candidate_recipe_ids=("recipe-a", "recipe-b"))]
    )

    plan_store.replace_meals(plan.id, [MealSpec("recipe-c", 2)])
    assert plan_store.get_candidates(plan.id, "m1") == []


@pytest.mark.requirement("REQ-000000019")
def test_replace_meals_swaps_the_whole_list_but_keeps_the_plan_id(plan_store: MealPlanStore):
    plan = plan_store.create([MealSpec("recipe-a", 2), MealSpec("recipe-b", 4)])

    replaced = plan_store.replace_meals(plan.id, [MealSpec("recipe-c", 5, is_suggestion=True)])

    assert replaced.id == plan.id
    assert [m.recipe_id for m in replaced.meals] == ["recipe-c"]
    assert replaced.meals[0].is_suggestion is True
    # Meal ids restart from m1 for the new set, not continue from the old one.
    assert replaced.meals[0].id == "m1"


@pytest.mark.requirement("REQ-000000019")
def test_replace_meals_unknown_plan_raises(plan_store: MealPlanStore):
    with pytest.raises(PlanNotFound):
        plan_store.replace_meals("does-not-exist", [MealSpec("recipe-a", 2)])


@pytest.mark.requirement("REQ-000000019")
def test_finalize_marks_plan_finalized(plan_store: MealPlanStore):
    plan = plan_store.create([MealSpec("recipe-a", 2)])
    assert plan.finalized is False

    finalized = plan_store.finalize(plan.id)
    assert finalized.finalized is True
    # Persisted, not just returned in-memory.
    assert plan_store.get(plan.id).finalized is True


@pytest.mark.requirement("REQ-000000019")
def test_finalize_unknown_plan_raises(plan_store: MealPlanStore):
    with pytest.raises(PlanNotFound):
        plan_store.finalize("does-not-exist")


def test_count_reflects_the_number_of_plans(plan_store: MealPlanStore):
    assert plan_store.count() == 0
    plan_store.create([MealSpec("recipe-a", 2)])
    plan_store.create([MealSpec("recipe-b", 2)])
    assert plan_store.count() == 2


def test_delete_all_removes_every_plan_meal_and_candidate_row(plan_store: MealPlanStore):
    plan = plan_store.create(
        [MealSpec("recipe-a", 2, is_suggestion=True, candidate_recipe_ids=("recipe-a", "recipe-b"))]
    )
    plan_store.create([MealSpec("recipe-c", 2)])

    removed = plan_store.delete_all()

    assert removed == 2
    assert plan_store.count() == 0
    assert plan_store.get_current() is None
    with pytest.raises(PlanNotFound):
        plan_store.get(plan.id)
    assert plan_store.get_candidates(plan.id, "m1") == []


def test_delete_all_is_a_no_op_when_nothing_stored(plan_store: MealPlanStore):
    assert plan_store.delete_all() == 0


@pytest.mark.requirement("REQ-000000019")
def test_opening_a_pre_is_suggestion_db_adds_the_missing_column(tmp_path: Path):
    """Regression test: databases created before the m4 `is_suggestion`

    column was added must be migrated in place on open, not crash.
    """
    db_path = tmp_path / "plans.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE meal_plans (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            finalized INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE plan_meals (
            plan_id TEXT NOT NULL REFERENCES meal_plans(id),
            meal_id TEXT NOT NULL,
            recipe_id TEXT NOT NULL,
            servings INTEGER NOT NULL,
            cooked INTEGER NOT NULL DEFAULT 0,
            position INTEGER NOT NULL,
            PRIMARY KEY (plan_id, meal_id)
        )
        """
    )
    conn.execute("INSERT INTO meal_plans VALUES ('p1', '2026-08-01T00:00:00+00:00', 0)")
    conn.execute("INSERT INTO plan_meals VALUES ('p1', 'm1', 'recipe-a', 2, 0, 0)")
    conn.commit()
    conn.close()

    store = MealPlanStore(db_path)
    plan = store.get_current()

    assert plan is not None
    assert plan.meals[0].is_suggestion is False
