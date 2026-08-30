from __future__ import annotations

import contextlib
import sqlite3
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Iterator

from little_meals.models import DayOfWeek, HouseholdPreferences, HouseholdPreferencesUpdate

_ROW_ID = 1

_SELECT_COLUMNS = (
    "recipes_per_week, recommendation_enabled, recommendation_day, recommendation_time, "
    "auto_confirm_enabled, auto_confirm_day, auto_confirm_time, default_servings, updated_at"
)

_LEGACY_COLUMNS = ("food_preferences_text", "food_filters", "food_preferences", "food_filter_count", "ai_suggestions_per_plan")

_NEW_COLUMNS = (
    ("recommendation_enabled", "INTEGER NOT NULL DEFAULT 1"),
    ("auto_confirm_enabled", "INTEGER NOT NULL DEFAULT 0"),
    ("auto_confirm_day", "TEXT NOT NULL DEFAULT 'sunday'"),
    ("auto_confirm_time", "TEXT NOT NULL DEFAULT '09:00'"),
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
                    recommendation_enabled INTEGER NOT NULL DEFAULT 1,
                    recommendation_day TEXT NOT NULL,
                    recommendation_time TEXT NOT NULL,
                    auto_confirm_enabled INTEGER NOT NULL DEFAULT 0,
                    auto_confirm_day TEXT NOT NULL DEFAULT 'sunday',
                    auto_confirm_time TEXT NOT NULL DEFAULT '09:00',
                    default_servings TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self._migrate_legacy_schema(conn)
            self._migrate_new_columns(conn)

    def _migrate_legacy_schema(self, conn: sqlite3.Connection) -> None:
        """Drops columns from earlier versions of this feature (free-text
        food preferences, the Spoonacular search filter, AI-suggestions-per-plan)
        now that recipe suggestions have been removed entirely - see
        docs/milestones.md's removal milestone. A brand-new database never had
        any of these columns, so this is a no-op there.

        Each DROP COLUMN is guarded against a concurrent process racing
        through this same migration - only a "no such column" error is
        swallowed, meaning some other connection already dropped it.
        """
        existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(household_preferences)")}
        for column in _LEGACY_COLUMNS:
            if column not in existing_columns:
                continue
            try:
                conn.execute(f"ALTER TABLE household_preferences DROP COLUMN {column}")  # noqa: S608 - column is a fixed internal literal
            except sqlite3.OperationalError as exc:
                if "no such column" not in str(exc):
                    raise

    def _migrate_new_columns(self, conn: sqlite3.Connection) -> None:
        """Adds columns introduced after this table's first release (the
        recommendation-day on/off toggle and the auto-confirm-plan schedule -
        see docs/milestones.md's M14 entry) to a database created before they
        existed. A brand-new database already has them from CREATE TABLE
        above, so this is a no-op there.

        Each ADD COLUMN is guarded against a concurrent process racing
        through this same migration - only a "duplicate column name" error is
        swallowed, meaning some other connection already added it."""
        existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(household_preferences)")}
        for column, definition in _NEW_COLUMNS:
            if column in existing_columns:
                continue
            try:
                conn.execute(f"ALTER TABLE household_preferences ADD COLUMN {column} {definition}")  # noqa: S608 - column/definition are fixed internal literals
            except sqlite3.OperationalError as exc:
                if "duplicate column name" not in str(exc):
                    raise

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
                    (id, recipes_per_week, recommendation_enabled, recommendation_day, recommendation_time,
                     auto_confirm_enabled, auto_confirm_day, auto_confirm_time, default_servings, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    recipes_per_week = excluded.recipes_per_week,
                    recommendation_enabled = excluded.recommendation_enabled,
                    recommendation_day = excluded.recommendation_day,
                    recommendation_time = excluded.recommendation_time,
                    auto_confirm_enabled = excluded.auto_confirm_enabled,
                    auto_confirm_day = excluded.auto_confirm_day,
                    auto_confirm_time = excluded.auto_confirm_time,
                    default_servings = excluded.default_servings,
                    updated_at = excluded.updated_at
                """,
                (
                    _ROW_ID,
                    update.recipes_per_week,
                    int(update.recommendation_enabled),
                    update.recommendation_day.value,
                    update.recommendation_time.isoformat(timespec="minutes"),
                    int(update.auto_confirm_enabled),
                    update.auto_confirm_day.value,
                    update.auto_confirm_time.isoformat(timespec="minutes"),
                    update.default_servings,
                    now.isoformat(),
                ),
            )
        return self.get()

    def delete(self) -> HouseholdPreferences:
        with self._connection() as conn:
            conn.execute("DELETE FROM household_preferences WHERE id = ?", (_ROW_ID,))
        return HouseholdPreferences()

    def reset_general_settings(self) -> HouseholdPreferences:
        """Resets recipes_per_week/recommendation settings/auto-confirm
        settings/default_servings to their defaults. Used by `lmeals settings
        --reset`."""
        defaults = HouseholdPreferences()
        return self.put(
            HouseholdPreferencesUpdate(
                recipes_per_week=defaults.recipes_per_week,
                recommendation_enabled=defaults.recommendation_enabled,
                recommendation_day=defaults.recommendation_day,
                recommendation_time=defaults.recommendation_time,
                auto_confirm_enabled=defaults.auto_confirm_enabled,
                auto_confirm_day=defaults.auto_confirm_day,
                auto_confirm_time=defaults.auto_confirm_time,
                default_servings=defaults.default_servings,
            )
        )


def _row_to_model(row: tuple) -> HouseholdPreferences:
    (
        recipes_per_week,
        recommendation_enabled,
        recommendation_day,
        recommendation_time,
        auto_confirm_enabled,
        auto_confirm_day,
        auto_confirm_time,
        default_servings,
        updated_at,
    ) = row
    return HouseholdPreferences(
        recipes_per_week=recipes_per_week,
        recommendation_enabled=bool(recommendation_enabled),
        recommendation_day=DayOfWeek(recommendation_day),
        recommendation_time=time.fromisoformat(recommendation_time),
        auto_confirm_enabled=bool(auto_confirm_enabled),
        auto_confirm_day=DayOfWeek(auto_confirm_day),
        auto_confirm_time=time.fromisoformat(auto_confirm_time),
        default_servings=default_servings,
        updated_at=datetime.fromisoformat(updated_at),
    )
