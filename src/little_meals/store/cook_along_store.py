from __future__ import annotations

import contextlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

from little_meals.models import CookAlongSession


class CookAlongStore:
    """Tracks in-progress cook-along position per recipe - a household only
    ever has one active cook-along per recipe at a time, so this is a single
    row keyed by recipe_id, not a session-id collection. A row existing
    means "left mid-session, resumable"; finishing (cooked or not) always
    deletes the row so the next cook-along for that recipe starts fresh."""

    def __init__(self, db_path: Path):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cook_along_sessions (
                    recipe_id TEXT PRIMARY KEY,
                    current_step INTEGER NOT NULL DEFAULT 0,
                    checked_ingredients TEXT NOT NULL DEFAULT '[]',
                    started_at TEXT NOT NULL,
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

    def get(self, recipe_id: str) -> Optional[CookAlongSession]:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT recipe_id, current_step, checked_ingredients, started_at, updated_at "
                "FROM cook_along_sessions WHERE recipe_id = ?",
                (recipe_id,),
            ).fetchone()
        if row is None:
            return None
        return _row_to_session(row)

    def start(self, recipe_id: str) -> CookAlongSession:
        """Create (or reset, if one already exists - used by "Start Over")
        a session at step 0 with an empty ingredient checklist."""
        now = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO cook_along_sessions (recipe_id, current_step, checked_ingredients, started_at, updated_at)
                VALUES (?, 0, '[]', ?, ?)
                ON CONFLICT(recipe_id) DO UPDATE SET
                    current_step = 0, checked_ingredients = '[]', updated_at = excluded.updated_at
                """,
                (recipe_id, now, now),
            )
        return self.get(recipe_id)

    def save_step(self, recipe_id: str, step: int) -> CookAlongSession:
        """Persist current position - called as a side effect of viewing
        any step, creating the session on the fly if none exists yet (e.g.
        someone hits a mid-URL directly without going through cook_start)."""
        now = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO cook_along_sessions (recipe_id, current_step, checked_ingredients, started_at, updated_at)
                VALUES (?, ?, '[]', ?, ?)
                ON CONFLICT(recipe_id) DO UPDATE SET
                    current_step = excluded.current_step, updated_at = excluded.updated_at
                """,
                (recipe_id, step, now, now),
            )
        return self.get(recipe_id)

    def toggle_ingredient(self, recipe_id: str, index: int) -> CookAlongSession:
        """Flip one ingredient's checked state by its 0-based index into
        recipe.ingredients. Creates the session on the fly if missing."""
        session = self.get(recipe_id) or self.start(recipe_id)
        checked = set(session.checked_ingredients)
        if index in checked:
            checked.discard(index)
        else:
            checked.add(index)
        now = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            conn.execute(
                "UPDATE cook_along_sessions SET checked_ingredients = ?, updated_at = ? WHERE recipe_id = ?",
                (json.dumps(sorted(checked)), now, recipe_id),
            )
        return self.get(recipe_id)

    def delete(self, recipe_id: str) -> None:
        """No-op if no session exists. Called when a cook-along finishes
        (either "Mark as cooked" or "Leave uncooked")."""
        with self._connection() as conn:
            conn.execute("DELETE FROM cook_along_sessions WHERE recipe_id = ?", (recipe_id,))


def _row_to_session(row: tuple) -> CookAlongSession:
    recipe_id, current_step, checked_ingredients, started_at, updated_at = row
    return CookAlongSession(
        recipe_id=recipe_id,
        current_step=current_step,
        checked_ingredients=json.loads(checked_ingredients),
        started_at=datetime.fromisoformat(started_at),
        updated_at=datetime.fromisoformat(updated_at),
    )
