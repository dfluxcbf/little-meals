from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

VALID_UPDATE_PAYLOAD = {
    "recipes_per_week": 6,
    "recommendation_day": "wednesday",
    "recommendation_time": "18:30",
    "default_servings": "2 adults + 1 child",
}

FORM_FIELDS = {
    "recipes_per_week": "4",
    "recommendation_day": "friday",
    "recommendation_time": "08:00",
    "default_servings": "2 adults",
}


@pytest.mark.requirement("REQ-000000012")
def test_settings_form_shows_current_values(client: TestClient):
    client.put("/api/household-preferences", json=VALID_UPDATE_PAYLOAD)

    response = client.get("/settings")
    assert response.status_code == 200
    text = response.text
    assert 'value="6"' in text
    assert "2 adults + 1 child" in text


@pytest.mark.requirement("REQ-000000012")
def test_settings_submit_saves_and_redisplays(client: TestClient):
    response = client.post("/settings", data=FORM_FIELDS)
    assert response.status_code == 200
    assert "Settings saved" in response.text

    fetched = client.get("/api/household-preferences").json()
    assert fetched["recipes_per_week"] == 4
    assert fetched["recommendation_day"] == "friday"


def test_settings_submit_with_invalid_day_shows_error(client: TestClient):
    response = client.post("/settings", data=dict(FORM_FIELDS, recommendation_day="funday"))
    assert response.status_code == 422
    assert "Could not save settings" in response.text


@pytest.mark.requirement("REQ-000000012")
def test_settings_nav_link_present(client: TestClient):
    response = client.get("/recipes")
    assert 'href="/settings"' in response.text


@pytest.mark.requirement("REQ-000000017")
def test_settings_day_picker_marks_current_day_checked(client: TestClient):
    client.put("/api/household-preferences", json=VALID_UPDATE_PAYLOAD)

    response = client.get("/settings")
    text = response.text
    assert 'id="day-wednesday"' in text
    assert 'id="day-wednesday" name="recommendation_day" value="wednesday" checked' in text
    # A different day's radio should not be marked checked.
    assert 'id="day-monday" name="recommendation_day" value="monday" checked' not in text
