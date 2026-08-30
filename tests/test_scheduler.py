from __future__ import annotations

import pytest

from datetime import datetime, time, timedelta, timezone

from little_meals.models import DayOfWeek, HouseholdPreferencesUpdate
from little_meals.scheduler import WeeklyScheduler, last_scheduled_occurrence
from little_meals.store.household_store import HouseholdPreferencesStore
from little_meals.store.notification_store import NotificationStore
from little_meals.store.plan_store import MealPlanStore, MealSpec


@pytest.mark.requirement("REQ-000000035")
def test_last_scheduled_occurrence_same_day_before_time():
    # Wednesday 2026-01-07 08:00, scheduled for Wednesday 09:00 -> last
    # occurrence was the PREVIOUS Wednesday (a week ago), since today's
    # slot hasn't happened yet.
    now = datetime(2026, 1, 7, 8, 0, tzinfo=timezone.utc)
    result = last_scheduled_occurrence(now, DayOfWeek.WEDNESDAY, time(9, 0))
    assert result == datetime(2025, 12, 31, 9, 0, tzinfo=timezone.utc)


@pytest.mark.requirement("REQ-000000035")
def test_last_scheduled_occurrence_same_day_after_time():
    now = datetime(2026, 1, 7, 10, 0, tzinfo=timezone.utc)
    result = last_scheduled_occurrence(now, DayOfWeek.WEDNESDAY, time(9, 0))
    assert result == datetime(2026, 1, 7, 9, 0, tzinfo=timezone.utc)


@pytest.mark.requirement("REQ-000000035")
def test_last_scheduled_occurrence_earlier_in_the_week():
    # 2026-01-07 is a Wednesday; scheduled for Monday 09:00.
    now = datetime(2026, 1, 7, 10, 0, tzinfo=timezone.utc)
    result = last_scheduled_occurrence(now, DayOfWeek.MONDAY, time(9, 0))
    assert result == datetime(2026, 1, 5, 9, 0, tzinfo=timezone.utc)


@pytest.mark.requirement("REQ-000000035")
def test_last_scheduled_occurrence_later_in_the_week_wraps_to_last_week():
    # Scheduled for Friday, but today is Wednesday - most recent Friday was
    # last week's.
    now = datetime(2026, 1, 7, 10, 0, tzinfo=timezone.utc)
    result = last_scheduled_occurrence(now, DayOfWeek.FRIDAY, time(9, 0))
    assert result == datetime(2026, 1, 2, 9, 0, tzinfo=timezone.utc)


def _stores(tmp_path):
    household_store = HouseholdPreferencesStore(tmp_path / "household.db")
    plan_store = MealPlanStore(tmp_path / "plan.db")
    notification_store = NotificationStore(tmp_path / "notification.db")
    return household_store, plan_store, notification_store


@pytest.mark.requirement("REQ-000000035")
def test_generates_when_no_plan_exists_yet(tmp_path):
    household_store, plan_store, notification_store = _stores(tmp_path)
    calls = []
    scheduler = WeeklyScheduler(
        household_store,
        plan_store,
        notification_store,
        generate_fn=lambda: calls.append(1),
        now_fn=lambda: datetime(2026, 1, 7, 10, 0, tzinfo=timezone.utc),
    )

    generated = scheduler.check_and_maybe_generate()

    assert generated is True
    assert calls == [1]
    assert notification_store.is_pending() is True


@pytest.mark.requirement("REQ-000000035")
def test_does_not_regenerate_when_current_plan_is_newer_than_the_scheduled_slot(tmp_path):
    household_store, plan_store, notification_store = _stores(tmp_path)
    # Default preferences: Sunday 09:00. A plan created "now" is newer than
    # any past Sunday-09:00 slot.
    plan_store.create([MealSpec("some-recipe", 2)])
    calls = []
    scheduler = WeeklyScheduler(
        household_store,
        plan_store,
        notification_store,
        generate_fn=lambda: calls.append(1),
        now_fn=lambda: datetime.now(timezone.utc),
    )

    generated = scheduler.check_and_maybe_generate()

    assert generated is False
    assert calls == []
    assert notification_store.is_pending() is False


@pytest.mark.requirement("REQ-000000035")
def test_regenerates_when_current_plan_predates_the_latest_scheduled_slot(tmp_path):
    household_store, plan_store, notification_store = _stores(tmp_path)

    # The plan store always stamps created_at with the real wall clock, so
    # rather than hardcode a date and risk it landing in the past relative
    # to whenever this test actually runs, pick a "now" far in the future
    # (10 years out) - guaranteed later than any real created_at - and
    # derive the household's scheduled day/time FROM that future moment, so
    # the two stay internally consistent regardless of which real day this
    # test happens to run on.
    old_plan = plan_store.create([MealSpec("some-recipe", 2)])
    future_now = old_plan.created_at + timedelta(days=3650)
    scheduled_day = list(DayOfWeek)[future_now.weekday()]

    household_store.put(
        HouseholdPreferencesUpdate(
            recipes_per_week=5,
            recommendation_enabled=True,
            recommendation_day=scheduled_day,
            recommendation_time=future_now.time(),
            auto_confirm_enabled=False,
            auto_confirm_day=scheduled_day,
            auto_confirm_time=future_now.time(),
            default_servings="2 adults",
        )
    )

    calls = []
    scheduler = WeeklyScheduler(
        household_store,
        plan_store,
        notification_store,
        generate_fn=lambda: calls.append(1),
        now_fn=lambda: future_now,
    )

    generated = scheduler.check_and_maybe_generate()

    assert generated is True
    assert calls == [1]
    assert notification_store.is_pending() is True
    # The outgoing plan never got manually confirmed - it's force-finalized
    # rather than left as a stuck, un-finalized orphan once superseded.
    assert plan_store.get(old_plan.id).finalized is True


@pytest.mark.requirement("REQ-000000048")
def test_does_not_generate_when_recommendation_disabled(tmp_path):
    household_store, plan_store, notification_store = _stores(tmp_path)
    household_store.put(
        HouseholdPreferencesUpdate(
            recipes_per_week=5,
            recommendation_enabled=False,
            recommendation_day=DayOfWeek.SUNDAY,
            recommendation_time=time(9, 0),
            auto_confirm_enabled=False,
            auto_confirm_day=DayOfWeek.SUNDAY,
            auto_confirm_time=time(9, 0),
            default_servings="2 adults",
        )
    )
    calls = []
    scheduler = WeeklyScheduler(
        household_store,
        plan_store,
        notification_store,
        generate_fn=lambda: calls.append(1),
        now_fn=lambda: datetime(2026, 1, 7, 10, 0, tzinfo=timezone.utc),
    )

    generated = scheduler.check_and_maybe_generate()

    assert generated is False
    assert calls == []


@pytest.mark.requirement("REQ-000000049")
def test_confirm_is_a_noop_when_auto_confirm_disabled(tmp_path):
    household_store, plan_store, notification_store = _stores(tmp_path)
    plan_store.create([MealSpec("some-recipe", 2)])
    scheduler = WeeklyScheduler(household_store, plan_store, notification_store, generate_fn=lambda: None)

    assert scheduler.check_and_maybe_confirm() is False


@pytest.mark.requirement("REQ-000000049")
def test_confirm_is_a_noop_when_no_current_plan(tmp_path):
    household_store, plan_store, notification_store = _stores(tmp_path)
    household_store.put(
        HouseholdPreferencesUpdate(
            recipes_per_week=5,
            recommendation_enabled=True,
            recommendation_day=DayOfWeek.SUNDAY,
            recommendation_time=time(9, 0),
            auto_confirm_enabled=True,
            auto_confirm_day=DayOfWeek.SUNDAY,
            auto_confirm_time=time(9, 0),
            default_servings="2 adults",
        )
    )
    scheduler = WeeklyScheduler(household_store, plan_store, notification_store, generate_fn=lambda: None)

    assert scheduler.check_and_maybe_confirm() is False


@pytest.mark.requirement("REQ-000000049")
def test_confirm_is_a_noop_when_plan_already_finalized(tmp_path):
    household_store, plan_store, notification_store = _stores(tmp_path)
    plan = plan_store.create([MealSpec("some-recipe", 2)])
    plan_store.finalize(plan.id)
    household_store.put(
        HouseholdPreferencesUpdate(
            recipes_per_week=5,
            recommendation_enabled=True,
            recommendation_day=DayOfWeek.SUNDAY,
            recommendation_time=time(9, 0),
            auto_confirm_enabled=True,
            auto_confirm_day=DayOfWeek.SUNDAY,
            auto_confirm_time=time(9, 0),
            default_servings="2 adults",
        )
    )
    scheduler = WeeklyScheduler(household_store, plan_store, notification_store, generate_fn=lambda: None)

    assert scheduler.check_and_maybe_confirm() is False


@pytest.mark.requirement("REQ-000000049")
def test_confirm_is_a_noop_when_not_due_yet(tmp_path):
    household_store, plan_store, notification_store = _stores(tmp_path)
    plan = plan_store.create([MealSpec("some-recipe", 2)])
    # Default auto-confirm preferences: Sunday 09:00. A plan created "now" is
    # newer than any past Sunday-09:00 slot.
    household_store.put(
        HouseholdPreferencesUpdate(
            recipes_per_week=5,
            recommendation_enabled=True,
            recommendation_day=DayOfWeek.SUNDAY,
            recommendation_time=time(9, 0),
            auto_confirm_enabled=True,
            auto_confirm_day=DayOfWeek.SUNDAY,
            auto_confirm_time=time(9, 0),
            default_servings="2 adults",
        )
    )
    scheduler = WeeklyScheduler(
        household_store, plan_store, notification_store, generate_fn=lambda: None, now_fn=lambda: datetime.now(timezone.utc)
    )

    assert scheduler.check_and_maybe_confirm() is False
    assert plan_store.get(plan.id).finalized is False


@pytest.mark.requirement("REQ-000000049")
def test_confirm_finalizes_a_draft_plan_when_due(tmp_path):
    household_store, plan_store, notification_store = _stores(tmp_path)

    old_plan = plan_store.create([MealSpec("some-recipe", 2)])
    future_now = old_plan.created_at + timedelta(days=3650)
    scheduled_day = list(DayOfWeek)[future_now.weekday()]

    household_store.put(
        HouseholdPreferencesUpdate(
            recipes_per_week=5,
            recommendation_enabled=True,
            recommendation_day=scheduled_day,
            recommendation_time=future_now.time(),
            auto_confirm_enabled=True,
            auto_confirm_day=scheduled_day,
            auto_confirm_time=future_now.time(),
            default_servings="2 adults",
        )
    )
    scheduler = WeeklyScheduler(
        household_store, plan_store, notification_store, generate_fn=lambda: None, now_fn=lambda: future_now
    )

    confirmed = scheduler.check_and_maybe_confirm()

    assert confirmed is True
    assert plan_store.get(old_plan.id).finalized is True
