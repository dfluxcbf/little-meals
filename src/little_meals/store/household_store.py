from __future__ import annotations

import contextlib
import json
import sqlite3
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Iterator, Optional

from little_meals.models import DayOfWeek, HouseholdPreferences, HouseholdPreferencesUpdate

_ROW_ID = 1

_SELECT_COLUMNS = (
    "recipes_per_week, recommendation_day, recommendation_time, "
    "food_preferences_text, food_filters, "
    "ai_suggestions_per_plan, default_servings, updated_at"
)

_NEW_COLUMNS = {
    "food_preferences_text": "TEXT NOT NULL DEFAULT ''",
    "food_filters": "TEXT NOT NULL DEFAULT 'null'",
}


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
                    food_preferences_text TEXT NOT NULL DEFAULT '',
                    food_filters TEXT NOT NULL DEFAULT 'null',
                    ai_suggestions_per_plan INTEGER NOT NULL,
                    default_servings TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self._migrate_legacy_schema(conn)

    def _migrate_legacy_schema(self, conn: sqlite3.Connection) -> None:
        """Adds the food_preferences_text/food_filters columns to a
        pre-existing (older-schema) database, best-effort seeds
        food_preferences_text from the legacy `food_preferences` JSON list
        column, then drops that legacy column and the now-obsolete
        `food_filter_count` column (from when the household could have N
        generated filters instead of one) entirely - see
        docs/architecture.md's "Food preference filters" row. A brand-new
        database already has the current columns (and never had either
        legacy one) from the CREATE TABLE above, so this is a no-op there.

        The `food_preferences` column in particular must actually be
        dropped, not just left unused: it was defined `NOT NULL` with no
        default, and neither put() nor save_food_filter() populates it any
        more - SQLite validates NOT NULL constraints on the row an
        INSERT...ON CONFLICT DO UPDATE would construct even when it
        ultimately resolves to the UPDATE branch, so every write against an
        un-migrated database would otherwise fail with "NOT NULL constraint
        failed: household_preferences.food_preferences". `food_filter_count`
        has a default so leaving it wouldn't break writes, but it's dead
        weight once nothing reads or writes it.

        Each ALTER TABLE (add or drop) is guarded against a concurrent
        process (e.g. `lmeals serve` and `lmeals import-spoonacular` both
        starting at once) racing through this same migration - only a
        "duplicate column name" or "no such column" error is swallowed, as
        appropriate, meaning some other connection already did that step.
        """
        existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(household_preferences)")}
        for column, ddl in _NEW_COLUMNS.items():
            if column in existing_columns:
                continue
            try:
                conn.execute(f"ALTER TABLE household_preferences ADD COLUMN {column} {ddl}")
            except sqlite3.OperationalError as exc:
                if "duplicate column name" not in str(exc):
                    raise

        if "food_preferences" in existing_columns:
            try:
                row = conn.execute(
                    "SELECT food_preferences, food_preferences_text FROM household_preferences WHERE id = ?",
                    (_ROW_ID,),
                ).fetchone()
                if row is not None:
                    legacy_raw, text = row
                    if not text:
                        try:
                            legacy_items = json.loads(legacy_raw)
                        except (TypeError, ValueError):
                            legacy_items = None
                        if legacy_items:
                            conn.execute(
                                "UPDATE household_preferences SET food_preferences_text = ? WHERE id = ?",
                                (", ".join(legacy_items), _ROW_ID),
                            )
                conn.execute("ALTER TABLE household_preferences DROP COLUMN food_preferences")
            except sqlite3.OperationalError as exc:
                if "no such column" not in str(exc):
                    raise

        if "food_filter_count" in existing_columns:
            try:
                conn.execute("ALTER TABLE household_preferences DROP COLUMN food_filter_count")
            except sqlite3.OperationalError as exc:
                if "no such column" not in str(exc):
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
        """Saves the general settings fields plus food_preferences_text -
        everything the single settings form submits together. food_filters
        (the household's own Spoonacular query, built on /settings/recipe-preferences) is left untouched
        here - it's only ever written by save_food_filter(), called
        separately by the route right after put() succeeds, so a partial
        JSON API update that omits `food_filter` never clobbers it (see
        HouseholdPreferencesUpdate's docstring)."""
        now = datetime.now(timezone.utc)
        defaults = HouseholdPreferences()
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO household_preferences
                    (id, recipes_per_week, recommendation_day, recommendation_time,
                     food_preferences_text, food_filters,
                     ai_suggestions_per_plan, default_servings, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    recipes_per_week = excluded.recipes_per_week,
                    recommendation_day = excluded.recommendation_day,
                    recommendation_time = excluded.recommendation_time,
                    food_preferences_text = excluded.food_preferences_text,
                    ai_suggestions_per_plan = excluded.ai_suggestions_per_plan,
                    default_servings = excluded.default_servings,
                    updated_at = excluded.updated_at
                """,
                (
                    _ROW_ID,
                    update.recipes_per_week,
                    update.recommendation_day.value,
                    update.recommendation_time.isoformat(timespec="minutes"),
                    update.food_preferences_text,
                    json.dumps(defaults.food_filter),
                    update.ai_suggestions_per_plan,
                    update.default_servings,
                    now.isoformat(),
                ),
            )
        return self.get()

    def save_food_filter(self, filter_: Optional[dict]) -> HouseholdPreferences:
        """Saves the household's own Spoonacular query (or clears it, when
        called with None) - leaves every other field untouched (or
        defaulted, same reasoning as put(), for a genuinely first-ever
        write)."""
        now = datetime.now(timezone.utc)
        defaults = HouseholdPreferences()
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO household_preferences
                    (id, recipes_per_week, recommendation_day, recommendation_time,
                     food_preferences_text, food_filters,
                     ai_suggestions_per_plan, default_servings, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    food_filters = excluded.food_filters,
                    updated_at = excluded.updated_at
                """,
                (
                    _ROW_ID,
                    defaults.recipes_per_week,
                    defaults.recommendation_day.value,
                    defaults.recommendation_time.isoformat(timespec="minutes"),
                    defaults.food_preferences_text,
                    json.dumps(filter_),
                    defaults.ai_suggestions_per_plan,
                    defaults.default_servings,
                    now.isoformat(),
                ),
            )
        return self.get()

    def delete(self) -> HouseholdPreferences:
        with self._connection() as conn:
            conn.execute("DELETE FROM household_preferences WHERE id = ?", (_ROW_ID,))
        return HouseholdPreferences()

    def reset_general_settings(self) -> HouseholdPreferences:
        """Resets recipes_per_week/recommendation_day/recommendation_time/
        ai_suggestions_per_plan/default_servings to their defaults, leaving
        food_preferences_text and the derived food_filter untouched - reuses
        put()'s existing column split (see its docstring), explicitly
        re-passing the current food_preferences_text since put() now owns
        that column too. Used by `lmeals settings --reset`."""
        defaults = HouseholdPreferences()
        current = self.get()
        return self.put(
            HouseholdPreferencesUpdate(
                recipes_per_week=defaults.recipes_per_week,
                recommendation_day=defaults.recommendation_day,
                recommendation_time=defaults.recommendation_time,
                ai_suggestions_per_plan=defaults.ai_suggestions_per_plan,
                default_servings=defaults.default_servings,
                food_preferences_text=current.food_preferences_text,
            )
        )


def _row_to_model(row: tuple) -> HouseholdPreferences:
    (
        recipes_per_week,
        recommendation_day,
        recommendation_time,
        food_preferences_text,
        food_filters,
        ai_suggestions_per_plan,
        default_servings,
        updated_at,
    ) = row
    return HouseholdPreferences(
        recipes_per_week=recipes_per_week,
        recommendation_day=DayOfWeek(recommendation_day),
        recommendation_time=time.fromisoformat(recommendation_time),
        food_preferences_text=food_preferences_text,
        food_filter=_parse_food_filter(food_filters),
        ai_suggestions_per_plan=ai_suggestions_per_plan,
        default_servings=default_servings,
        updated_at=datetime.fromisoformat(updated_at),
    )


def _parse_food_filter(raw: str) -> Optional[dict]:
    """Coerces the current single-object shape, the prior shape (a list of
    filter objects, from when the household could have N LLM-generated
    filters), and the shape before that (a plain list of strings, from the
    original tag-list feature) into one Optional[dict] - so a household
    upgrading from any earlier version of this feature doesn't lose
    whatever it had stored. When the stored value is a non-empty list,
    keeps its first entry. The dict itself is opaque now - just the
    household's own Spoonacular query parameters, built on /settings/recipe-preferences - so unlike
    earlier versions this performs no field validation at all."""
    value = json.loads(raw)
    if value is None:
        return None
    if isinstance(value, list):
        if not value:
            return None
        value = value[0]
    if isinstance(value, str):
        return {"query": value}
    return value or None
