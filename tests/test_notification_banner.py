from __future__ import annotations

from fastapi.testclient import TestClient

from little_meals.store.notification_store import NotificationStore


def test_banner_hidden_by_default(client: TestClient):
    response = client.get("/recipes")
    assert "notification-banner" not in response.text


def test_banner_shown_on_recipes_page_when_pending(client: TestClient, notification_store: NotificationStore):
    notification_store.mark_new_plan_ready()

    response = client.get("/recipes")
    assert "notification-banner" in response.text
    assert "Your new weekly plan is ready" in response.text
    assert '<a href="/plan" class="notification-banner">' in response.text


def test_banner_not_shown_on_plan_page_itself(client: TestClient, notification_store: NotificationStore):
    # Viewing /plan is exactly what the banner points to, so it clears (see
    # test_viewing_plan_page_clears_the_notification below) before this same
    # response renders - no point telling someone "your plan is ready" while
    # they're already looking at it.
    notification_store.mark_new_plan_ready()
    response = client.get("/plan")
    assert "notification-banner" not in response.text


def test_viewing_plan_page_clears_the_notification(client: TestClient, notification_store: NotificationStore):
    notification_store.mark_new_plan_ready()
    assert notification_store.is_pending() is True

    client.get("/plan")

    assert notification_store.is_pending() is False


def test_banner_gone_from_recipes_page_after_plan_viewed(client: TestClient, notification_store: NotificationStore):
    notification_store.mark_new_plan_ready()
    client.get("/plan")

    response = client.get("/recipes")
    assert "notification-banner" not in response.text
