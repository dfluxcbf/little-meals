from __future__ import annotations

import logging
from datetime import datetime, time, timedelta, timezone
from typing import Callable

from little_meals.models import DayOfWeek
from little_meals.store.household_store import HouseholdPreferencesStore
from little_meals.store.notification_store import NotificationStore
from little_meals.store.plan_store import MealPlanStore

logger = logging.getLogger(__name__)

_WEEKDAY_INDEX = {
    DayOfWeek.MONDAY: 0,
    DayOfWeek.TUESDAY: 1,
    DayOfWeek.WEDNESDAY: 2,
    DayOfWeek.THURSDAY: 3,
    DayOfWeek.FRIDAY: 4,
    DayOfWeek.SATURDAY: 5,
    DayOfWeek.SUNDAY: 6,
}


def last_scheduled_occurrence(now: datetime, day: DayOfWeek, at: time) -> datetime:
    """The most recent UTC datetime matching `day`/`at` that is <= `now`.

    `now` must be timezone-aware. `recommendation_time` (household
    preferences) has no timezone field of its own, so it's interpreted here
    as UTC - see architecture.md's Scheduler entry for why, and what a
    household on another timezone needs to account for until a timezone
    field is added.
    """
    target_weekday = _WEEKDAY_INDEX[day]
    days_since = (now.weekday() - target_weekday) % 7
    candidate_date = (now - timedelta(days=days_since)).date()
    candidate = datetime.combine(candidate_date, at, tzinfo=timezone.utc)
    if candidate > now:
        candidate -= timedelta(days=7)
    return candidate


class WeeklyScheduler:
    """Polls on a short interval rather than firing one precisely-timed job
    per week, so a change to household preferences' recommendation day/time
    takes effect on the very next check without anything needing to
    reschedule a job. See architecture.md's Scheduler entry.
    """

    def __init__(
        self,
        household_store: HouseholdPreferencesStore,
        plan_store: MealPlanStore,
        notification_store: NotificationStore,
        generate_fn: Callable[[], None],
        now_fn: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ):
        self._household_store = household_store
        self._plan_store = plan_store
        self._notification_store = notification_store
        self._generate_fn = generate_fn
        self._now_fn = now_fn

    def check_and_maybe_generate(self) -> bool:
        """Called periodically. Returns True if it generated a new plan on
        this call - mainly useful for tests; production callers don't need
        the return value."""
        preferences = self._household_store.get()
        now = self._now_fn()
        scheduled_at = last_scheduled_occurrence(now, preferences.recommendation_day, preferences.recommendation_time)

        current = self._plan_store.get_current()
        if current is not None and current.created_at >= scheduled_at:
            return False

        logger.info("Auto-generating this week's plan (scheduled for %s)", scheduled_at.isoformat())
        self._generate_fn()
        self._notification_store.mark_new_plan_ready()
        return True
