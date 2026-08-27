from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

VALID_UPDATE_PAYLOAD = {
    "recipes_per_week": 6,
    "recommendation_day": "wednesday",
    "recommendation_time": "18:30",
    "food_preferences": ["vegetarian-friendly"],
    "ai_suggestions_per_plan": 3,
    "default_servings": "2 adults + 1 child",
}


@pytest.mark.requirement("REQ-000000012")
def test_settings_form_shows_current_values(client: TestClient):
    client.put("/api/household-preferences", json=VALID_UPDATE_PAYLOAD)

    response = client.get("/settings")
    assert response.status_code == 200
    text = response.text
    assert 'value="6"' in text
    assert "vegetarian-friendly" in text
    assert "2 adults + 1 child" in text


@pytest.mark.requirement("REQ-000000012")
def test_settings_submit_saves_and_redisplays(client: TestClient):
    response = client.post(
        "/settings",
        data={
            "recipes_per_week": "4",
            "recommendation_day": "friday",
            "recommendation_time": "08:00",
            "food_preferences": "pescetarian, quick-meals",
            "ai_suggestions_per_plan": "1",
            "default_servings": "2 adults",
        },
    )
    assert response.status_code == 200
    assert "Settings saved" in response.text

    fetched = client.get("/api/household-preferences").json()
    assert fetched["recipes_per_week"] == 4
    assert fetched["recommendation_day"] == "friday"
    assert fetched["food_preferences"] == ["pescetarian", "quick-meals"]


def test_settings_submit_with_invalid_day_shows_error(client: TestClient):
    response = client.post(
        "/settings",
        data={
            "recipes_per_week": "4",
            "recommendation_day": "funday",
            "recommendation_time": "08:00",
            "food_preferences": "",
            "ai_suggestions_per_plan": "1",
            "default_servings": "2 adults",
        },
    )
    assert response.status_code == 422
    assert "Could not save settings" in response.text


@pytest.mark.requirement("REQ-000000012")
def test_settings_nav_link_present(client: TestClient):
    response = client.get("/recipes")
    assert 'href="/settings"' in response.text
