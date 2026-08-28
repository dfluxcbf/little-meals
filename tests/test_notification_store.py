from __future__ import annotations

from pathlib import Path

from little_meals.store.notification_store import NotificationStore


def test_is_pending_defaults_to_false(tmp_path: Path):
    store = NotificationStore(tmp_path / "notification.db")
    assert store.is_pending() is False


def test_mark_new_plan_ready_sets_pending(tmp_path: Path):
    store = NotificationStore(tmp_path / "notification.db")
    store.mark_new_plan_ready()
    assert store.is_pending() is True


def test_clear_unsets_pending(tmp_path: Path):
    store = NotificationStore(tmp_path / "notification.db")
    store.mark_new_plan_ready()
    store.clear()
    assert store.is_pending() is False


def test_state_persists_across_instances(tmp_path: Path):
    db_path = tmp_path / "notification.db"
    NotificationStore(db_path).mark_new_plan_ready()
    assert NotificationStore(db_path).is_pending() is True
