from __future__ import annotations

import contextlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


@dataclass(frozen=True)
class IngredientFlags:
    pantry: bool = False
    never_buy: bool = False


def flags_for(catalog: dict[str, IngredientFlags], name: str) -> IngredientFlags:
    """Look up an ingredient's flags by name, normalized the same way
    planning/shopping_list.py keys its merge dict (stripped, lowercased) -
    unknown names default to no flags set."""
    return catalog.get(name.strip().lower(), IngredientFlags())


class IngredientCatalogStore:
    """Reads/writes the household-wide ingredient pantry/never-buy flags in
    SQLite - a global catalog keyed by ingredient name (not per-recipe), so
    tagging "salt" as a pantry item once applies everywhere it appears. Same
    "Other storage" bucket as HouseholdPreferencesStore/ShoppingListStore."""

    def __init__(self, db_path: Path):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ingredient_flags (
                    name TEXT PRIMARY KEY,
                    pantry INTEGER NOT NULL DEFAULT 0,
                    never_buy INTEGER NOT NULL DEFAULT 0
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

    def get_all(self) -> dict[str, IngredientFlags]:
        with self._connection() as conn:
            rows = conn.execute("SELECT name, pantry, never_buy FROM ingredient_flags").fetchall()
        return {
            name.strip().lower(): IngredientFlags(pantry=bool(pantry), never_buy=bool(never_buy))
            for name, pantry, never_buy in rows
        }

    def set_flags(self, name: str, pantry: bool, never_buy: bool) -> None:
        key = name.strip().lower()
        if not key:
            return
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO ingredient_flags (name, pantry, never_buy) VALUES (?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET pantry = excluded.pantry, never_buy = excluded.never_buy
                """,
                (key, int(pantry), int(never_buy)),
            )

    def add(self, name: str) -> None:
        """Upsert a name with both flags false if it isn't tracked yet -
        no-op if it already has a row (doesn't clobber existing flags)."""
        key = name.strip().lower()
        if not key:
            return
        with self._connection() as conn:
            conn.execute(
                "INSERT INTO ingredient_flags (name, pantry, never_buy) VALUES (?, 0, 0) ON CONFLICT(name) DO NOTHING",
                (key,),
            )
