from __future__ import annotations

from datetime import time
from pathlib import Path

import pytest

from little_meals.models import DayOfWeek, HouseholdPreferencesUpdate
from little_meals.store.household_store import HouseholdPreferencesStore

UPDATE_PAYLOAD = HouseholdPreferencesUpdate(
    recipes_per_week=6,
    recommendation_day=DayOfWeek.WEDNESDAY,
    recommendation_time=time(18, 30),
    food_preferences=["vegetarian-friendly", "low-carb"],
    ai_suggestions_per_plan=3,
    default_servings="2 adults + 1 child",
)


@pytest.mark.requirement("REQ-000000010")
def test_get_returns_defaults_before_any_put(household_store: HouseholdPreferencesStore):
    preferences = household_store.get()
    assert preferences.recipes_per_week == 5
    assert preferences.recommendation_day == DayOfWeek.SUNDAY
    assert preferences.recommendation_time == time(9, 0)
    assert preferences.food_preferences == []
    assert preferences.ai_suggestions_per_plan == 2
    assert preferences.default_servings == "2 adults"
    assert preferences.updated_at is None


@pytest.mark.requirement("REQ-000000010")
def test_put_then_get_round_trips(household_store: HouseholdPreferencesStore):
    saved = household_store.put(UPDATE_PAYLOAD)
    assert saved.recipes_per_week == 6
    assert saved.recommendation_day == DayOfWeek.WEDNESDAY
    assert saved.recommendation_time == time(18, 30)
    assert saved.food_preferences == ["vegetarian-friendly", "low-carb"]
    assert saved.ai_suggestions_per_plan == 3
    assert saved.default_servings == "2 adults + 1 child"
    assert saved.updated_at is not None

    reread = household_store.get()
    assert reread == saved


def test_put_overwrites_previous_values(household_store: HouseholdPreferencesStore):
    household_store.put(UPDATE_PAYLOAD)
    second = household_store.put(UPDATE_PAYLOAD.model_copy(update={"recipes_per_week": 3}))

    assert second.recipes_per_week == 3
    assert household_store.get().recipes_per_week == 3


def test_delete_resets_to_defaults(household_store: HouseholdPreferencesStore):
    household_store.put(UPDATE_PAYLOAD)
    reset = household_store.delete()

    assert reset.recipes_per_week == 5
    assert reset.updated_at is None
    assert household_store.get().recipes_per_week == 5


def test_persists_across_store_instances(tmp_path: Path, household_store: HouseholdPreferencesStore):
    household_store.put(UPDATE_PAYLOAD)

    reopened = HouseholdPreferencesStore(tmp_path / "household.db")
    assert reopened.get().recipes_per_week == 6
