from __future__ import annotations

import contextlib
import json
import sqlite3
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Iterator

from little_meals.models import DayOfWeek, HouseholdPreferences, HouseholdPreferencesUpdate

_ROW_ID = 1

_SELECT_COLUMNS = (
    "recipes_per_week, recommendation_day, recommendation_time, "
    "food_preferences, ai_suggestions_per_plan, default_servings, updated_at"
)


class HouseholdPreferencesStore:
    """Reads/writes the single household-preferences row in SQLite.

    Household preferences are shared by every device, not per person (see
    design.md's non-goals), so this is a singleton row rather than a keyed
    collection - there is nothing to list or look up by id.
    """

    def __init__(self, db_path: Path):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS household_preferences (
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

    @contextlib.contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._db_path)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def get(self) -> HouseholdPreferences:
        with self._connection() as conn:
            row = conn.execute(
                f"SELECT {_SELECT_COLUMNS} FROM household_preferences WHERE id = ?", (_ROW_ID,)
            ).fetchone()
        if row is None:
            return HouseholdPreferences()
        return _row_to_model(row)

    def put(self, update: HouseholdPreferencesUpdate) -> HouseholdPreferences:
        now = datetime.now(timezone.utc)
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO household_preferences
                    (id, recipes_per_week, recommendation_day, recommendation_time,
                     food_preferences, ai_suggestions_per_plan, default_servings, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    recipes_per_week = excluded.recipes_per_week,
                    recommendation_day = excluded.recommendation_day,
                    recommendation_time = excluded.recommendation_time,
                    food_preferences = excluded.food_preferences,
                    ai_suggestions_per_plan = excluded.ai_suggestions_per_plan,
                    default_servings = excluded.default_servings,
                    updated_at = excluded.updated_at
                """,
                (
                    _ROW_ID,
                    update.recipes_per_week,
                    update.recommendation_day.value,
                    update.recommendation_time.isoformat(timespec="minutes"),
                    json.dumps(update.food_preferences),
                    update.ai_suggestions_per_plan,
                    update.default_servings,
                    now.isoformat(),
                ),
            )
        return self.get()

    def delete(self) -> HouseholdPreferences:
        with self._connection() as conn:
            conn.execute("DELETE FROM household_preferences WHERE id = ?", (_ROW_ID,))
        return HouseholdPreferences()


def _row_to_model(row: tuple) -> HouseholdPreferences:
    (
        recipes_per_week,
        recommendation_day,
        recommendation_time,
        food_preferences,
        ai_suggestions_per_plan,
        default_servings,
        updated_at,
    ) = row
    return HouseholdPreferences(
        recipes_per_week=recipes_per_week,
        recommendation_day=DayOfWeek(recommendation_day),
        recommendation_time=time.fromisoformat(recommendation_time),
        food_preferences=json.loads(food_preferences),
        ai_suggestions_per_plan=ai_suggestions_per_plan,
        default_servings=default_servings,
        updated_at=datetime.fromisoformat(updated_at),
    )
