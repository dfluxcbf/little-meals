from __future__ import annotations

import contextlib
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

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
                    position INTEGER NOT NULL,
                    PRIMARY KEY (plan_id, meal_id)
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

    def create(self, recipe_servings: list[tuple[str, int]]) -> MealPlan:
        """Create a new plan from a list of (recipe_id, servings) pairs, in
        the given order. `recipe_servings` may be empty (e.g. an empty
        library) - the plan is still created, just with no meals yet."""
        plan_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        with self._connection() as conn:
            conn.execute(
                "INSERT INTO meal_plans (id, created_at, finalized) VALUES (?, ?, 0)",
                (plan_id, now.isoformat()),
            )
            for position, (recipe_id, servings) in enumerate(recipe_servings):
                conn.execute(
                    """
                    INSERT INTO plan_meals (plan_id, meal_id, recipe_id, servings, cooked, position)
                    VALUES (?, ?, ?, ?, 0, ?)
                    """,
                    (plan_id, f"m{position + 1}", recipe_id, servings, position),
                )
        return self.get(plan_id)

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
                SELECT meal_id, recipe_id, servings, cooked FROM plan_meals
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

    def finalize(self, plan_id: str) -> MealPlan:
        with self._connection() as conn:
            cursor = conn.execute("UPDATE meal_plans SET finalized = 1 WHERE id = ?", (plan_id,))
            if cursor.rowcount == 0:
                raise PlanNotFound(plan_id)
        return self.get(plan_id)


def _row_to_plan(plan_row: tuple, meal_rows: list[tuple]) -> MealPlan:
    plan_id, created_at, finalized = plan_row
    meals = [
        PlanMeal(id=meal_id, recipe_id=recipe_id, servings=servings, cooked=bool(cooked))
        for meal_id, recipe_id, servings, cooked in meal_rows
    ]
    return MealPlan(id=plan_id, created_at=datetime.fromisoformat(created_at), finalized=bool(finalized), meals=meals)
