from __future__ import annotations

import contextlib
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, NamedTuple, Optional

from little_meals.models import MealPlan, PlanMeal


class PlanStoreError(RuntimeError):
    """Base error for the meal plan store."""


class PlanNotFound(PlanStoreError):
    def __init__(self, plan_id: str):
        super().__init__(f"Meal plan not found: {plan_id}")
        self.plan_id = plan_id


class PlanMealNotFound(PlanStoreError):
    def __init__(self, plan_id: str, meal_id: str):
        super().__init__(f"Meal {meal_id} not found in plan {plan_id}")
        self.plan_id = plan_id
        self.meal_id = meal_id


class MealSpec(NamedTuple):
    """One meal's persisted fields, independent of its position/id - used
    both to create a plan's initial meals and to replace them wholesale on a
    whole-plan reroll."""

    recipe_id: str
    servings: int
    is_suggestion: bool = False
    candidate_recipe_ids: tuple[str, ...] = ()
    """Sibling recipe ids fetched together with recipe_id in the same
    Spoonacular batch (including recipe_id itself) - see
    plan_meal_candidates below. Empty for library picks."""


class MealPlanStore:
    """Reads/writes weekly meal plans in SQLite - see design.md's "Meal
    plan" concept and architecture.md's "Other storage" decision (app-managed,
    relational, not something the user hand-edits, unlike the recipe store).
    """

    def __init__(self, db_path: Path):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS meal_plans (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    finalized INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS plan_meals (
                    plan_id TEXT NOT NULL REFERENCES meal_plans(id),
                    meal_id TEXT NOT NULL,
                    recipe_id TEXT NOT NULL,
                    servings INTEGER NOT NULL,
                    cooked INTEGER NOT NULL DEFAULT 0,
                    is_suggestion INTEGER NOT NULL DEFAULT 0,
                    position INTEGER NOT NULL,
                    PRIMARY KEY (plan_id, meal_id)
                )
                """
            )
            existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(plan_meals)")}
            if "is_suggestion" not in existing_columns:
                conn.execute("ALTER TABLE plan_meals ADD COLUMN is_suggestion INTEGER NOT NULL DEFAULT 0")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS plan_meal_candidates (
                    plan_id TEXT NOT NULL REFERENCES meal_plans(id),
                    meal_id TEXT NOT NULL,
                    recipe_id TEXT NOT NULL,
                    PRIMARY KEY (plan_id, meal_id, recipe_id)
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

    def create(self, meals: list[MealSpec]) -> MealPlan:
        """Create a new plan from a list of meal specs, in the given order.
        `meals` may be empty (e.g. an empty library) - the plan is still
        created, just with no meals yet."""
        plan_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        with self._connection() as conn:
            conn.execute(
                "INSERT INTO meal_plans (id, created_at, finalized) VALUES (?, ?, 0)",
                (plan_id, now.isoformat()),
            )
            self._insert_meals(conn, plan_id, meals)
        return self.get(plan_id)

    def replace_meals(self, plan_id: str, meals: list[MealSpec]) -> MealPlan:
        """Whole-plan reroll: discard this plan's current meals and insert a
        fresh set, keeping the same plan id (and its finalized state)."""
        with self._connection() as conn:
            if conn.execute("SELECT 1 FROM meal_plans WHERE id = ?", (plan_id,)).fetchone() is None:
                raise PlanNotFound(plan_id)
            conn.execute("DELETE FROM plan_meals WHERE plan_id = ?", (plan_id,))
            conn.execute("DELETE FROM plan_meal_candidates WHERE plan_id = ?", (plan_id,))
            self._insert_meals(conn, plan_id, meals)
        return self.get(plan_id)

    def _insert_meals(self, conn: sqlite3.Connection, plan_id: str, meals: list[MealSpec]) -> None:
        for position, meal in enumerate(meals):
            meal_id = f"m{position + 1}"
            conn.execute(
                """
                INSERT INTO plan_meals (plan_id, meal_id, recipe_id, servings, cooked, is_suggestion, position)
                VALUES (?, ?, ?, ?, 0, ?, ?)
                """,
                (plan_id, meal_id, meal.recipe_id, meal.servings, int(meal.is_suggestion), position),
            )
            self._set_candidates(conn, plan_id, meal_id, meal.candidate_recipe_ids)

    def _set_candidates(
        self, conn: sqlite3.Connection, plan_id: str, meal_id: str, candidate_recipe_ids: tuple[str, ...]
    ) -> None:
        conn.execute(
            "DELETE FROM plan_meal_candidates WHERE plan_id = ? AND meal_id = ?", (plan_id, meal_id)
        )
        conn.executemany(
            "INSERT INTO plan_meal_candidates (plan_id, meal_id, recipe_id) VALUES (?, ?, ?)",
            [(plan_id, meal_id, recipe_id) for recipe_id in candidate_recipe_ids],
        )

    def get_candidates(self, plan_id: str, meal_id: str) -> list[str]:
        """The (up to `_CANDIDATES_PER_SUGGESTION`) recipe ids fetched
        together for one AI-suggestion slot, including whichever is
        currently assigned - see plan_builder.py's `_generate_suggestion_meal`.
        Empty for a slot that was never filled by a fresh suggestion fetch
        (a library pick, a combination suggestion, or a "select from
        cookbook" choice)."""
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT recipe_id FROM plan_meal_candidates WHERE plan_id = ? AND meal_id = ?", (plan_id, meal_id)
            ).fetchall()
        return [row[0] for row in rows]

    def get_current(self) -> Optional[MealPlan]:
        """The most recently created plan, or None if none exist yet."""
        with self._connection() as conn:
            row = conn.execute("SELECT id FROM meal_plans ORDER BY created_at DESC, rowid DESC LIMIT 1").fetchone()
        if row is None:
            return None
        return self.get(row[0])

    def get(self, plan_id: str) -> MealPlan:
        with self._connection() as conn:
            plan_row = conn.execute(
                "SELECT id, created_at, finalized FROM meal_plans WHERE id = ?", (plan_id,)
            ).fetchone()
            if plan_row is None:
                raise PlanNotFound(plan_id)
            meal_rows = conn.execute(
                """
                SELECT meal_id, recipe_id, servings, cooked, is_suggestion FROM plan_meals
                WHERE plan_id = ? ORDER BY position ASC
                """,
                (plan_id,),
            ).fetchall()
        return _row_to_plan(plan_row, meal_rows)

    def set_servings(self, plan_id: str, meal_id: str, servings: int) -> MealPlan:
        self._update_meal(plan_id, meal_id, "servings", servings)
        return self.get(plan_id)

    def set_cooked(self, plan_id: str, meal_id: str, cooked: bool) -> MealPlan:
        self._update_meal(plan_id, meal_id, "cooked", int(cooked))
        return self.get(plan_id)

    def set_recipe(
        self,
        plan_id: str,
        meal_id: str,
        recipe_id: str,
        servings: int,
        is_suggestion: bool = False,
        candidate_recipe_ids: tuple[str, ...] = (),
    ) -> MealPlan:
        """Reroll one meal (single-meal reroll, controlled reroll, or
        picking among a suggestion slot's candidates): swap in a different
        recipe for an existing slot, resetting its cooked state (it hasn't
        been cooked yet - it's a different dish now). Always replaces the
        slot's candidate set too - defaulting to empty clears any stale
        Spoonacular candidates left over from a prior suggestion (correct
        for a library pick or "select from cookbook"); a caller re-picking
        among an existing suggestion's own candidates passes them back in
        unchanged so the household can keep toggling between them."""
        with self._connection() as conn:
            cursor = conn.execute(
                """
                UPDATE plan_meals SET recipe_id = ?, servings = ?, is_suggestion = ?, cooked = 0
                WHERE plan_id = ? AND meal_id = ?
                """,
                (recipe_id, servings, int(is_suggestion), plan_id, meal_id),
            )
            if cursor.rowcount == 0:
                if conn.execute("SELECT 1 FROM meal_plans WHERE id = ?", (plan_id,)).fetchone() is None:
                    raise PlanNotFound(plan_id)
                raise PlanMealNotFound(plan_id, meal_id)
            self._set_candidates(conn, plan_id, meal_id, candidate_recipe_ids)
        return self.get(plan_id)

    def _update_meal(self, plan_id: str, meal_id: str, column: str, value) -> None:
        with self._connection() as conn:
            cursor = conn.execute(
                f"UPDATE plan_meals SET {column} = ? WHERE plan_id = ? AND meal_id = ?",  # noqa: S608 - column is a fixed internal literal, never user input
                (value, plan_id, meal_id),
            )
            if cursor.rowcount == 0:
                if conn.execute("SELECT 1 FROM meal_plans WHERE id = ?", (plan_id,)).fetchone() is None:
                    raise PlanNotFound(plan_id)
                raise PlanMealNotFound(plan_id, meal_id)

    def count(self) -> int:
        """Number of stored plans - used by `lmeals settings --reset` to
        report how many will be deleted before asking for confirmation."""
        with self._connection() as conn:
            return conn.execute("SELECT COUNT(*) FROM meal_plans").fetchone()[0]

    def delete_all(self) -> int:
        """Deletes every plan (and its meals/candidate rows) - used by
        `lmeals settings --reset`. Returns the number of plans removed."""
        with self._connection() as conn:
            removed = conn.execute("SELECT COUNT(*) FROM meal_plans").fetchone()[0]
            conn.execute("DELETE FROM plan_meal_candidates")
            conn.execute("DELETE FROM plan_meals")
            conn.execute("DELETE FROM meal_plans")
        return removed

    def finalize(self, plan_id: str) -> MealPlan:
        with self._connection() as conn:
            cursor = conn.execute("UPDATE meal_plans SET finalized = 1 WHERE id = ?", (plan_id,))
            if cursor.rowcount == 0:
                raise PlanNotFound(plan_id)
        return self.get(plan_id)


def _row_to_plan(plan_row: tuple, meal_rows: list[tuple]) -> MealPlan:
    plan_id, created_at, finalized = plan_row
    meals = [
        PlanMeal(id=meal_id, recipe_id=recipe_id, servings=servings, cooked=bool(cooked), is_suggestion=bool(is_suggestion))
        for meal_id, recipe_id, servings, cooked, is_suggestion in meal_rows
    ]
    return MealPlan(id=plan_id, created_at=datetime.fromisoformat(created_at), finalized=bool(finalized), meals=meals)
