from __future__ import annotations

import contextlib
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

from little_meals.models import ShoppingList, ShoppingListItem
from little_meals.planning.shopping_list import MergedItem


class ShoppingListStoreError(RuntimeError):
    """Base error for the shopping list store."""


class ShoppingListNotFound(ShoppingListStoreError):
    def __init__(self, list_id: str):
        super().__init__(f"Shopping list not found: {list_id}")
        self.list_id = list_id


class ShoppingListItemNotFound(ShoppingListStoreError):
    def __init__(self, list_id: str, item_id: str):
        super().__init__(f"Item {item_id} not found in shopping list {list_id}")
        self.list_id = list_id
        self.item_id = item_id


class ShoppingListStore:
    """Reads/writes shopping lists in SQLite - one per finalized MealPlan
    (see design.md's "Shopping list" concept), app-managed like the plan
    and household-preferences stores."""

    def __init__(self, db_path: Path):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS shopping_lists (
                    id TEXT PRIMARY KEY,
                    plan_id TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    actual_cost REAL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS shopping_list_items (
                    list_id TEXT NOT NULL REFERENCES shopping_lists(id),
                    item_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    quantity REAL,
                    unit TEXT,
                    checked INTEGER NOT NULL DEFAULT 0,
                    position INTEGER NOT NULL,
                    PRIMARY KEY (list_id, item_id)
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

    def create(self, plan_id: str, items: list[MergedItem]) -> ShoppingList:
        """Create the shopping list for a plan. Raises ValueError if one
        already exists for that plan - the caller (routes) should check
        `get_for_plan` first; this only guards against a genuine race."""
        list_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        with self._connection() as conn:
            try:
                conn.execute(
                    "INSERT INTO shopping_lists (id, plan_id, created_at, actual_cost) VALUES (?, ?, ?, NULL)",
                    (list_id, plan_id, now.isoformat()),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError(f"A shopping list already exists for plan {plan_id}") from exc
            for position, item in enumerate(items):
                conn.execute(
                    """
                    INSERT INTO shopping_list_items (list_id, item_id, name, quantity, unit, checked, position)
                    VALUES (?, ?, ?, ?, ?, 0, ?)
                    """,
                    (list_id, f"i{position + 1}", item.name, item.quantity, item.unit, position),
                )
        return self.get(list_id)

    def get_for_plan(self, plan_id: str) -> Optional[ShoppingList]:
        with self._connection() as conn:
            row = conn.execute("SELECT id FROM shopping_lists WHERE plan_id = ?", (plan_id,)).fetchone()
        if row is None:
            return None
        return self.get(row[0])

    def get(self, list_id: str) -> ShoppingList:
        with self._connection() as conn:
            list_row = conn.execute(
                "SELECT id, plan_id, created_at, actual_cost FROM shopping_lists WHERE id = ?", (list_id,)
            ).fetchone()
            if list_row is None:
                raise ShoppingListNotFound(list_id)
            item_rows = conn.execute(
                """
                SELECT item_id, name, quantity, unit, checked FROM shopping_list_items
                WHERE list_id = ? ORDER BY position ASC
                """,
                (list_id,),
            ).fetchall()
        return _row_to_list(list_row, item_rows)

    def set_item_checked(self, list_id: str, item_id: str, checked: bool) -> ShoppingList:
        with self._connection() as conn:
            cursor = conn.execute(
                "UPDATE shopping_list_items SET checked = ? WHERE list_id = ? AND item_id = ?",
                (int(checked), list_id, item_id),
            )
            if cursor.rowcount == 0:
                if conn.execute("SELECT 1 FROM shopping_lists WHERE id = ?", (list_id,)).fetchone() is None:
                    raise ShoppingListNotFound(list_id)
                raise ShoppingListItemNotFound(list_id, item_id)
        return self.get(list_id)

    def set_actual_cost(self, list_id: str, actual_cost: float) -> ShoppingList:
        with self._connection() as conn:
            cursor = conn.execute(
                "UPDATE shopping_lists SET actual_cost = ? WHERE id = ?",
                (actual_cost, list_id),
            )
            if cursor.rowcount == 0:
                raise ShoppingListNotFound(list_id)
        return self.get(list_id)


def _row_to_list(list_row: tuple, item_rows: list[tuple]) -> ShoppingList:
    list_id, plan_id, created_at, actual_cost = list_row
    items = [
        ShoppingListItem(id=item_id, name=name, quantity=quantity, unit=unit, checked=bool(checked))
        for item_id, name, quantity, unit, checked in item_rows
    ]
    return ShoppingList(
        id=list_id,
        plan_id=plan_id,
        created_at=datetime.fromisoformat(created_at),
        items=items,
        actual_cost=actual_cost,
    )
