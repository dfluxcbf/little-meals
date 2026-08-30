from __future__ import annotations

import sqlite3
from datetime import time
from pathlib import Path

import pytest

from little_meals.models import DayOfWeek, HouseholdPreferencesUpdate
from little_meals.store.household_store import HouseholdPreferencesStore

UPDATE_PAYLOAD = HouseholdPreferencesUpdate(
    recipes_per_week=6,
    recommendation_day=DayOfWeek.WEDNESDAY,
    recommendation_time=time(18, 30),
    default_servings="2 adults + 1 child",
)


@pytest.mark.requirement("REQ-000000010")
def test_get_returns_defaults_before_any_put(household_store: HouseholdPreferencesStore):
    preferences = household_store.get()
    assert preferences.recipes_per_week == 5
    assert preferences.recommendation_day == DayOfWeek.SUNDAY
    assert preferences.recommendation_time == time(9, 0)
    assert preferences.default_servings == "2 adults"
    assert preferences.updated_at is None


@pytest.mark.requirement("REQ-000000010")
def test_put_then_get_round_trips(household_store: HouseholdPreferencesStore):
    saved = household_store.put(UPDATE_PAYLOAD)
    assert saved.recipes_per_week == 6
    assert saved.recommendation_day == DayOfWeek.WEDNESDAY
    assert saved.recommendation_time == time(18, 30)
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


@pytest.mark.requirement("REQ-000000010")
def test_reset_general_settings_restores_defaults(household_store: HouseholdPreferencesStore):
    household_store.put(UPDATE_PAYLOAD)

    reset = household_store.reset_general_settings()

    assert reset.recipes_per_week == 5
    assert reset.recommendation_day == DayOfWeek.SUNDAY
    assert reset.recommendation_time == time(9, 0)
    assert reset.default_servings == "2 adults"

    reread = household_store.get()
    assert reread == reset


def test_persists_across_store_instances(tmp_path: Path, household_store: HouseholdPreferencesStore):
    household_store.put(UPDATE_PAYLOAD)

    reopened = HouseholdPreferencesStore(tmp_path / "household.db")
    assert reopened.get().recipes_per_week == 6


def test_legacy_columns_are_dropped_on_migration(tmp_path: Path):
    # Regression test: databases from before recipe suggestions were removed
    # had food_preferences_text/food_filters/ai_suggestions_per_plan columns
    # - they must be dropped, not just left unused, so the schema doesn't
    # accumulate dead columns forever.
    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE household_preferences (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                recipes_per_week INTEGER NOT NULL,
                recommendation_day TEXT NOT NULL,
                recommendation_time TEXT NOT NULL,
                food_preferences_text TEXT NOT NULL DEFAULT '',
                food_filters TEXT NOT NULL DEFAULT 'null',
                ai_suggestions_per_plan INTEGER NOT NULL,
                default_servings TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO household_preferences
                (id, recipes_per_week, recommendation_day, recommendation_time,
                 food_preferences_text, food_filters, ai_suggestions_per_plan,
                 default_servings, updated_at)
            VALUES (1, 5, 'sunday', '09:00', 'meat lover', 'null', 2, '2 adults', '2026-01-01T00:00:00+00:00')
            """
        )
        conn.commit()
    finally:
        conn.close()

    migrated = HouseholdPreferencesStore(db_path)

    preferences = migrated.get()
    assert preferences.recipes_per_week == 5
    assert preferences.default_servings == "2 adults"

    conn = sqlite3.connect(db_path)
    try:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(household_preferences)")}
    finally:
        conn.close()
    assert columns.isdisjoint({"food_preferences_text", "food_filters", "ai_suggestions_per_plan"})

    # Writes still succeed post-migration too.
    assert migrated.put(UPDATE_PAYLOAD).recipes_per_week == 6


def test_legacy_migration_is_a_noop_when_columns_already_absent(
    household_store: HouseholdPreferencesStore, tmp_path: Path
):
    household_store.put(UPDATE_PAYLOAD)

    reopened = HouseholdPreferencesStore(tmp_path / "household.db")
    assert reopened.get().recipes_per_week == 6


def test_two_stores_opened_concurrently_against_a_legacy_schema_do_not_crash(tmp_path: Path):
    db_path = tmp_path / "legacy_concurrent.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE household_preferences (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                recipes_per_week INTEGER NOT NULL,
                recommendation_day TEXT NOT NULL,
                recommendation_time TEXT NOT NULL,
                food_preferences_text TEXT NOT NULL DEFAULT '',
                ai_suggestions_per_plan INTEGER NOT NULL,
                default_servings TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()

    first = HouseholdPreferencesStore(db_path)
    second = HouseholdPreferencesStore(db_path)

    assert first.get() == second.get()
