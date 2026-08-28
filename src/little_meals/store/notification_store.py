from __future__ import annotations

import contextlib
import sqlite3
from pathlib import Path
from typing import Iterator

_ROW_ID = 1


class NotificationStore:
    """A single flag: whether the household has an unseen "new plan is
    ready" notification. Set when the scheduler (Milestone 7) auto-generates
    a plan, cleared the next time the plan review page is viewed - see
    architecture.md's Scheduler entry. Deliberately minimal: this app has no
    email/push notification channel (see the same note), so "notification"
    means an in-app banner, not anything delivered outside the browser tab.
    """

    def __init__(self, db_path: Path):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    new_plan_ready INTEGER NOT NULL DEFAULT 0
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

    def mark_new_plan_ready(self) -> None:
        self._set(1)

    def clear(self) -> None:
        self._set(0)

    def is_pending(self) -> bool:
        with self._connection() as conn:
            row = conn.execute("SELECT new_plan_ready FROM notifications WHERE id = ?", (_ROW_ID,)).fetchone()
        return row is not None and bool(row[0])

    def _set(self, value: int) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO notifications (id, new_plan_ready) VALUES (?, ?)
                ON CONFLICT(id) DO UPDATE SET new_plan_ready = excluded.new_plan_ready
                """,
                (_ROW_ID, value),
            )
