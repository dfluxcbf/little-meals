from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

VALID_UPDATE_PAYLOAD = {
    "recipes_per_week": 6,
    "recommendation_enabled": True,
    "recommendation_day": "wednesday",
    "recommendation_time": "18:30",
    "auto_confirm_enabled": False,
    "auto_confirm_day": "sunday",
    "auto_confirm_time": "09:00",
    "default_servings": "2 adults + 1 child",
}

FORM_FIELDS = {
    "recipes_per_week": "4",
    "recommendation_enabled": "on",
    "recommendation_day": "friday",
    "recommendation_time": "08:00",
    "auto_confirm_day": "sunday",
    "auto_confirm_time": "09:00",
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
    # recommendation_enabled was checked in the submitted form,
    # auto_confirm_enabled was omitted (an unchecked checkbox never gets
    # sent) - each should round-trip to the matching boolean.
    assert fetched["recommendation_enabled"] is True
    assert fetched["auto_confirm_enabled"] is False


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


@pytest.mark.requirement("REQ-000000048")
def test_settings_form_shows_recommendation_enabled_checkbox_state(client: TestClient):
    client.put("/api/household-preferences", json=dict(VALID_UPDATE_PAYLOAD, recommendation_enabled=False))

    response = client.get("/settings")
    text = response.text
    assert '<input type="checkbox" id="recommendation_enabled" name="recommendation_enabled" >' in text


@pytest.mark.requirement("REQ-000000049")
def test_settings_form_shows_auto_confirm_section(client: TestClient):
    client.put(
        "/api/household-preferences",
        json=dict(VALID_UPDATE_PAYLOAD, auto_confirm_enabled=True, auto_confirm_day="friday", auto_confirm_time="20:00"),
    )

    response = client.get("/settings")
    text = response.text
    assert "Auto-confirm plan" in text
    assert '<input type="checkbox" id="auto_confirm_enabled" name="auto_confirm_enabled" checked>' in text
    assert 'id="acday-friday" name="auto_confirm_day" value="friday" checked' in text
    assert 'id="auto_confirm_time"' in text and 'value="20:00"' in text
