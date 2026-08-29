from __future__ import annotations

import json
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
    ai_suggestions_per_plan=3,
    default_servings="2 adults + 1 child",
)


@pytest.mark.requirement("REQ-000000010")
def test_get_returns_defaults_before_any_put(household_store: HouseholdPreferencesStore):
    preferences = household_store.get()
    assert preferences.recipes_per_week == 5
    assert preferences.recommendation_day == DayOfWeek.SUNDAY
    assert preferences.recommendation_time == time(9, 0)
    assert preferences.food_preferences_text == ""
    assert preferences.food_filter is None
    assert preferences.ai_suggestions_per_plan == 2
    assert preferences.default_servings == "2 adults"
    assert preferences.updated_at is None


@pytest.mark.requirement("REQ-000000010")
def test_put_then_get_round_trips(household_store: HouseholdPreferencesStore):
    saved = household_store.put(UPDATE_PAYLOAD)
    assert saved.recipes_per_week == 6
    assert saved.recommendation_day == DayOfWeek.WEDNESDAY
    assert saved.recommendation_time == time(18, 30)
    assert saved.ai_suggestions_per_plan == 3
    assert saved.default_servings == "2 adults + 1 child"
    assert saved.updated_at is not None

    reread = household_store.get()
    assert reread == saved


@pytest.mark.requirement("REQ-000000043")
def test_put_also_saves_food_preferences_text(household_store: HouseholdPreferencesStore):
    saved = household_store.put(UPDATE_PAYLOAD.model_copy(update={"food_preferences_text": "spicy food"}))
    assert saved.food_preferences_text == "spicy food"
    assert household_store.get().food_preferences_text == "spicy food"


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


def test_reset_general_settings_restores_defaults_but_keeps_food_preferences(
    household_store: HouseholdPreferencesStore,
):
    household_store.put(UPDATE_PAYLOAD.model_copy(update={"food_preferences_text": "spicy food"}))
    household_store.save_food_filter({"query": "spicy chicken"})

    reset = household_store.reset_general_settings()

    assert reset.recipes_per_week == 5
    assert reset.recommendation_day == DayOfWeek.SUNDAY
    assert reset.recommendation_time == time(9, 0)
    assert reset.ai_suggestions_per_plan == 2
    assert reset.default_servings == "2 adults"
    assert reset.food_preferences_text == "spicy food"
    assert reset.food_filter == {"query": "spicy chicken"}

    reread = household_store.get()
    assert reread == reset


def test_persists_across_store_instances(tmp_path: Path, household_store: HouseholdPreferencesStore):
    household_store.put(UPDATE_PAYLOAD)

    reopened = HouseholdPreferencesStore(tmp_path / "household.db")
    assert reopened.get().recipes_per_week == 6


@pytest.mark.requirement("REQ-000000043")
def test_save_food_filter_round_trips(household_store: HouseholdPreferencesStore):
    filter_ = {"query": "pork with lemon", "diet": "Pescetarian", "cuisine": "Italian", "excludeIngredients": "peanuts"}

    saved = household_store.save_food_filter(filter_)
    assert saved.food_filter == filter_
    assert saved.updated_at is not None

    reread = household_store.get()
    assert reread == saved


@pytest.mark.requirement("REQ-000000043")
def test_save_food_filter_none_clears_it(household_store: HouseholdPreferencesStore):
    household_store.save_food_filter({"query": "spicy chicken"})
    saved = household_store.save_food_filter(None)
    assert saved.food_filter is None
    assert household_store.get().food_filter is None


@pytest.mark.requirement("REQ-000000043")
def test_save_food_filter_leaves_general_settings_alone(household_store: HouseholdPreferencesStore):
    household_store.put(UPDATE_PAYLOAD)

    saved = household_store.save_food_filter({"query": "spicy chicken"})

    assert saved.recipes_per_week == 6
    assert saved.recommendation_day == DayOfWeek.WEDNESDAY
    assert saved.default_servings == "2 adults + 1 child"
    assert saved.food_filter == {"query": "spicy chicken"}


@pytest.mark.requirement("REQ-000000043")
def test_put_leaves_previously_saved_food_filter_alone(household_store: HouseholdPreferencesStore):
    household_store.save_food_filter({"query": "spicy chicken"})

    saved = household_store.put(UPDATE_PAYLOAD)

    assert saved.recipes_per_week == 6
    assert saved.food_filter == {"query": "spicy chicken"}


@pytest.mark.requirement("REQ-000000043")
def test_get_coerces_legacy_plain_string_food_filters_list(household_store: HouseholdPreferencesStore, tmp_path: Path):
    # Households that generated filters under the very first version of this
    # feature had a plain list-of-strings JSON blob stored - reading it back
    # must not lose that, even though it's now a single structured object.
    db_path = tmp_path / "household.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO household_preferences
                (id, recipes_per_week, recommendation_day, recommendation_time,
                 food_preferences_text, food_filters,
                 ai_suggestions_per_plan, default_servings, updated_at)
            VALUES (1, 5, 'sunday', '09:00', 'meat lover', ?, 2, '2 adults', '2026-01-01T00:00:00+00:00')
            """,
            (json.dumps(["chicken", "pork with lemon"]),),
        )
        conn.commit()
    finally:
        conn.close()

    preferences = household_store.get()

    assert preferences.food_filter == {"query": "chicken"}


@pytest.mark.requirement("REQ-000000043")
def test_get_coerces_legacy_structured_filter_list(household_store: HouseholdPreferencesStore, tmp_path: Path):
    # Households that generated filters when the household could have N
    # structured filters (instead of the current single one) had a JSON
    # list of filter objects stored - keep the first as the new single one.
    db_path = tmp_path / "household.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO household_preferences
                (id, recipes_per_week, recommendation_day, recommendation_time,
                 food_preferences_text, food_filters,
                 ai_suggestions_per_plan, default_servings, updated_at)
            VALUES (1, 5, 'sunday', '09:00', 'meat lover', ?, 2, '2 adults', '2026-01-01T00:00:00+00:00')
            """,
            (json.dumps([{"query": "chicken", "diet": "Vegan"}, {"query": "beef"}]),),
        )
        conn.commit()
    finally:
        conn.close()

    preferences = household_store.get()

    assert preferences.food_filter == {"query": "chicken", "diet": "Vegan"}


def test_get_treats_stored_empty_list_as_no_filter(household_store: HouseholdPreferencesStore, tmp_path: Path):
    db_path = tmp_path / "household.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO household_preferences
                (id, recipes_per_week, recommendation_day, recommendation_time,
                 food_preferences_text, food_filters,
                 ai_suggestions_per_plan, default_servings, updated_at)
            VALUES (1, 5, 'sunday', '09:00', '', '[]', 2, '2 adults', '2026-01-01T00:00:00+00:00')
            """
        )
        conn.commit()
    finally:
        conn.close()

    assert household_store.get().food_filter is None


@pytest.mark.requirement("REQ-000000043")
def test_legacy_food_preferences_column_backfills_text_on_migration(tmp_path: Path):
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
                food_preferences TEXT NOT NULL,
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
                 food_preferences, ai_suggestions_per_plan, default_servings, updated_at)
            VALUES (1, 5, 'sunday', '09:00', ?, 2, '2 adults', '2026-01-01T00:00:00+00:00')
            """,
            (json.dumps(["vegetarian-friendly", "low-carb"]),),
        )
        conn.commit()
    finally:
        conn.close()

    migrated = HouseholdPreferencesStore(db_path)

    preferences = migrated.get()
    assert preferences.food_preferences_text == "vegetarian-friendly, low-carb"
    assert preferences.food_filter is None

    conn = sqlite3.connect(db_path)
    try:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(household_preferences)")}
    finally:
        conn.close()
    assert "food_preferences" not in columns


@pytest.mark.requirement("REQ-000000043")
def test_put_and_save_food_filter_succeed_against_a_migrated_legacy_database(tmp_path: Path):
    # Regression test: the legacy `food_preferences` column was NOT NULL
    # with no default. Leaving it in place (rather than dropping it during
    # migration) made every write against an old database fail, since
    # SQLite validates NOT NULL on the row an INSERT...ON CONFLICT DO
    # UPDATE would construct even when it resolves to the UPDATE branch -
    # neither put() nor save_food_filter() populates that column any
    # more. get()-only assertions (as in the test above) don't exercise
    # this path, which is exactly how this one shipped broken initially.
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
                food_preferences TEXT NOT NULL,
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
                 food_preferences, ai_suggestions_per_plan, default_servings, updated_at)
            VALUES (1, 5, 'sunday', '09:00', ?, 2, '2 adults', '2026-01-01T00:00:00+00:00')
            """,
            (json.dumps(["vegetarian-friendly"]),),
        )
        conn.commit()
    finally:
        conn.close()

    migrated = HouseholdPreferencesStore(db_path)

    put_result = migrated.put(UPDATE_PAYLOAD)
    assert put_result.recipes_per_week == 6

    filter_result = migrated.save_food_filter({"query": "spicy chicken"})
    assert filter_result.food_filter == {"query": "spicy chicken"}


@pytest.mark.requirement("REQ-000000043")
def test_food_filter_count_column_is_dropped_on_migration(tmp_path: Path):
    # Regression test: databases created during the "N structured filters"
    # era had a food_filter_count column - it must be dropped, not just
    # left unused, so the schema doesn't accumulate dead columns forever.
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
                food_filter_count INTEGER NOT NULL DEFAULT 5,
                food_filters TEXT NOT NULL DEFAULT '[]',
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
                 food_preferences_text, food_filter_count, food_filters,
                 ai_suggestions_per_plan, default_servings, updated_at)
            VALUES (1, 5, 'sunday', '09:00', 'meat lover', 4, ?, 2, '2 adults', '2026-01-01T00:00:00+00:00')
            """,
            (json.dumps([{"query": "chicken"}, {"query": "beef"}]),),
        )
        conn.commit()
    finally:
        conn.close()

    migrated = HouseholdPreferencesStore(db_path)

    preferences = migrated.get()
    assert preferences.food_preferences_text == "meat lover"
    assert preferences.food_filter == {"query": "chicken"}

    conn = sqlite3.connect(db_path)
    try:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(household_preferences)")}
    finally:
        conn.close()
    assert "food_filter_count" not in columns

    # Writes still succeed post-migration too.
    assert migrated.put(UPDATE_PAYLOAD).recipes_per_week == 6


@pytest.mark.requirement("REQ-000000043")
def test_legacy_migration_is_a_noop_when_new_columns_already_present(
    household_store: HouseholdPreferencesStore, tmp_path: Path
):
    household_store.put(UPDATE_PAYLOAD.model_copy(update={"food_preferences_text": "spicy food"}))

    reopened = HouseholdPreferencesStore(tmp_path / "household.db")
    assert reopened.get().food_preferences_text == "spicy food"


@pytest.mark.requirement("REQ-000000043")
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
                food_preferences TEXT NOT NULL,
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
