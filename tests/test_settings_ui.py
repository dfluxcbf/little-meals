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

FORM_FIELDS = {
    "recipes_per_week": "4",
    "recommendation_day": "friday",
    "recommendation_time": "08:00",
    "ai_suggestions_per_plan": "1",
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


@pytest.mark.requirement("REQ-000000043")
def test_settings_links_to_recipe_preferences_page(client: TestClient):
    response = client.get("/settings")
    text = response.text
    assert 'href="/settings/recipe-preferences"' in text
    # The old free-form JSON textarea is gone from the general settings page.
    assert 'name="food_filter_json"' not in text


@pytest.mark.requirement("REQ-000000043")
def test_recipe_preferences_form_has_no_dropdowns_and_exposes_every_field(client: TestClient):
    response = client.get("/settings/recipe-preferences")
    assert response.status_code == 200
    text = response.text
    assert "<select" not in text
    # A representative field of each kind: free text, single-select
    # (diet), multi-select (cuisine/intolerances), boolean, and a nutrient
    # min/max pair.
    assert 'name="query"' in text
    assert 'name="diet"' in text
    assert 'name="cuisine"' in text
    assert 'name="intolerances"' in text
    assert 'name="ignorePantry"' in text
    assert 'name="minCalories"' in text
    assert 'name="maxCalories"' in text
    # sort/type/instructionsRequired/addRecipeNutrition/number are hardcoded
    # by the app (see suggestion._ALWAYS_ON_SEARCH_PARAMS) and deliberately
    # not editable here.
    assert 'name="sort"' not in text
    assert 'name="type"' not in text
    assert 'name="instructionsRequired"' not in text
    assert 'name="addRecipeNutrition"' not in text
    assert 'name="number"' not in text


@pytest.mark.requirement("REQ-000000043")
def test_recipe_preferences_submit_saves_structured_fields(client: TestClient):
    response = client.post(
        "/settings/recipe-preferences",
        data={
            "query": "dinner",
            "diet": "Vegan",
            "cuisine": ["Italian", "Mexican"],
            "intolerances": ["Peanut"],
            "maxCalories": "850",
            "minFiber": "8",
            "ignorePantry": "on",
        },
    )

    assert response.status_code == 200
    assert "saved" in response.text.lower()

    food_filter = client.get("/api/household-preferences").json()["food_filter"]
    assert food_filter == {
        "query": "dinner",
        "diet": "Vegan",
        "cuisine": "Italian,Mexican",
        "intolerances": "Peanut",
        "maxCalories": 850,
        "minFiber": 8,
        "ignorePantry": True,
    }


@pytest.mark.requirement("REQ-000000043")
def test_recipe_preferences_form_renders_a_legacy_list_valued_filter(client: TestClient):
    """A household that saved its filter before this page existed (a
    hand-pasted JSON filter, or a direct PUT against the JSON API) may
    have a JSON list stored for a multi-select field like cuisine -
    the page must still render, not 500."""
    client.put(
        "/api/household-preferences",
        json={
            "recipes_per_week": 5,
            "recommendation_day": "sunday",
            "recommendation_time": "09:00",
            "ai_suggestions_per_plan": 2,
            "default_servings": "2 adults",
            "food_filter": {"cuisine": ["Italian", "Mexican"], "intolerances": ["Peanut"]},
        },
    )

    response = client.get("/settings/recipe-preferences")

    assert response.status_code == 200
    assert 'value="Italian" checked' in response.text
    assert 'value="Peanut" checked' in response.text


@pytest.mark.requirement("REQ-000000043")
def test_recipe_preferences_form_prefills_saved_values(client: TestClient):
    client.post("/settings/recipe-preferences", data={"query": "dinner", "maxCalories": "850"})

    response = client.get("/settings/recipe-preferences")
    text = response.text
    assert 'value="dinner"' in text
    assert 'value="850"' in text


@pytest.mark.requirement("REQ-000000043")
def test_recipe_preferences_submit_with_bad_number_shows_error_and_does_not_save(client: TestClient):
    response = client.post("/settings/recipe-preferences", data={"maxCalories": "not-a-number"})

    assert response.status_code == 422
    assert "must be a number" in response.text
    assert client.get("/api/household-preferences").json()["food_filter"] is None


@pytest.mark.requirement("REQ-000000043")
def test_recipe_preferences_submit_blank_form_clears_a_previous_filter(client: TestClient):
    client.post("/settings/recipe-preferences", data={"query": "dinner"})

    response = client.post("/settings/recipe-preferences", data={})

    assert response.status_code == 200
    assert client.get("/api/household-preferences").json()["food_filter"] is None


@pytest.mark.requirement("REQ-000000043")
def test_recipe_preferences_search_always_builds_from_saved_settings(client: TestClient):
    """Every Spoonacular search (live suggestions and import-spoonacular)
    builds its request via suggestion.build_complex_search_params(
    preferences.food_filter, ...) - see plan_builder._search_filter and
    cli.py's import command - so whatever is saved here is always what
    gets sent, with no separate code path that could drift from it."""
    client.post("/settings/recipe-preferences", data={"query": "dinner", "diet": "Vegan"})

    from little_meals.planning.suggestion import build_complex_search_params

    preferences = client.get("/api/household-preferences").json()
    params = build_complex_search_params(preferences["food_filter"], count=3)
    assert params["query"] == "dinner"
    assert params["diet"] == "Vegan"
    assert params["number"] == 3
