from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

VALID_UPDATE_PAYLOAD = {
    "recipes_per_week": 6,
    "recommendation_day": "wednesday",
    "recommendation_time": "18:30",
    "ai_suggestions_per_plan": 3,
    "default_servings": "2 adults + 1 child",
}


@pytest.mark.requirement("REQ-000000011")
def test_get_returns_defaults_before_any_put(client: TestClient):
    response = client.get("/api/household-preferences")
    assert response.status_code == 200
    body = response.json()
    assert body["recipes_per_week"] == 5
    assert body["updated_at"] is None


@pytest.mark.requirement("REQ-000000011")
def test_put_then_get_round_trip(client: TestClient):
    updated = client.put("/api/household-preferences", json=VALID_UPDATE_PAYLOAD)
    assert updated.status_code == 200
    body = updated.json()
    assert body["recipes_per_week"] == 6
    assert body["recommendation_day"] == "wednesday"
    assert body["recommendation_time"] == "18:30:00"
    assert body["ai_suggestions_per_plan"] == 3
    assert body["default_servings"] == "2 adults + 1 child"
    assert body["updated_at"] is not None

    fetched = client.get("/api/household-preferences")
    assert fetched.json() == body


@pytest.mark.requirement("REQ-000000011")
def test_delete_resets_to_defaults(client: TestClient):
    client.put("/api/household-preferences", json=VALID_UPDATE_PAYLOAD)
    reset = client.delete("/api/household-preferences")

    assert reset.status_code == 200
    assert reset.json()["recipes_per_week"] == 5
    assert client.get("/api/household-preferences").json()["recipes_per_week"] == 5


def test_malformed_update_returns_400(client: TestClient):
    response = client.put("/api/household-preferences", json={"recipes_per_week": 0})
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_invalid_day_returns_400(client: TestClient):
    payload = dict(VALID_UPDATE_PAYLOAD, recommendation_day="funday")
    response = client.put("/api/household-preferences", json=payload)
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_put_rejects_food_preferences_text_over_2000_chars(client: TestClient):
    response = client.put(
        "/api/household-preferences", json=dict(VALID_UPDATE_PAYLOAD, food_preferences_text="x" * 2001)
    )
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.requirement("REQ-000000043")
def test_put_with_food_filter_saves_it_verbatim(client: TestClient):
    food_filter = {"query": "dinner", "cuisine": "Italian,Mexican", "maxCalories": 850}

    response = client.put(
        "/api/household-preferences", json=dict(VALID_UPDATE_PAYLOAD, food_filter=food_filter)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["food_filter"] == food_filter

    fetched = client.get("/api/household-preferences").json()
    assert fetched["food_filter"] == food_filter


@pytest.mark.requirement("REQ-000000043")
def test_put_omitting_food_filter_leaves_previous_one_untouched(client: TestClient):
    food_filter = {"query": "dinner"}
    client.put("/api/household-preferences", json=dict(VALID_UPDATE_PAYLOAD, food_filter=food_filter))

    response = client.put("/api/household-preferences", json=VALID_UPDATE_PAYLOAD)

    assert response.status_code == 200
    assert response.json()["food_filter"] == food_filter
    assert client.get("/api/household-preferences").json()["food_filter"] == food_filter


@pytest.mark.requirement("REQ-000000043")
def test_put_with_explicit_null_food_filter_clears_it(client: TestClient):
    client.put("/api/household-preferences", json=dict(VALID_UPDATE_PAYLOAD, food_filter={"query": "dinner"}))

    response = client.put("/api/household-preferences", json=dict(VALID_UPDATE_PAYLOAD, food_filter=None))

    assert response.status_code == 200
    assert response.json()["food_filter"] is None
    assert client.get("/api/household-preferences").json()["food_filter"] is None


def test_put_with_non_object_food_filter_returns_400(client: TestClient):
    response = client.put("/api/household-preferences", json=dict(VALID_UPDATE_PAYLOAD, food_filter=["a", "b"]))
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"
