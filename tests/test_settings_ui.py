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


def _create_recipe(client: TestClient, sample_recipe) -> dict:
    return client.post(
        "/api/recipes",
        json={
            "name": sample_recipe.name,
            "cook_time_minutes": sample_recipe.cook_time_minutes,
            "classification": sample_recipe.classification.value,
            "nutrition": sample_recipe.nutrition.model_dump(exclude_none=True),
            "servings": sample_recipe.servings,
            "ingredients": [i.model_dump(exclude_none=True) for i in sample_recipe.ingredients],
            "steps": sample_recipe.steps,
        },
    ).json()


@pytest.mark.requirement("REQ-000000062")
def test_settings_page_shows_development_section(client: TestClient):
    response = client.get("/settings")
    assert "Development" in response.text
    assert 'action="/settings/dev/clear-shopping-list"' in response.text


@pytest.mark.requirement("REQ-000000062")
def test_clear_shopping_list_deletes_list_but_keeps_plan(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)
    client.post("/plan/generate", follow_redirects=False)
    client.post("/plan/finalize", follow_redirects=False)
    client.post("/shopping/generate", follow_redirects=False)
    assert client.get("/api/shopping-list/current").status_code == 200

    response = client.post("/settings/dev/clear-shopping-list", follow_redirects=False)
    assert response.status_code == 200
    assert "Shopping list cleared." in response.text

    assert client.get("/api/shopping-list/current").status_code == 404
    assert client.get("/api/plan/current").status_code == 200


@pytest.mark.requirement("REQ-000000062")
def test_clear_shopping_list_is_a_no_op_when_no_plan_exists(client: TestClient):
    response = client.post("/settings/dev/clear-shopping-list", follow_redirects=False)
    assert response.status_code == 200


@pytest.mark.requirement("REQ-000000057")
def test_ingredients_settings_page_lists_recipe_ingredients(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)

    response = client.get("/settings/ingredients")
    assert response.status_code == 200
    for ingredient in sample_recipe.ingredients:
        assert ingredient.name.lower() in response.text.lower()


@pytest.mark.requirement("REQ-000000057")
def test_ingredients_settings_page_shows_three_lists(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)

    response = client.get("/settings/ingredients")
    assert "Regular Ingredients" in response.text
    assert "Pantry Ingredients" in response.text
    assert "Never Buy" in response.text


@pytest.mark.requirement("REQ-000000057")
def test_move_ingredient_to_pantry(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)
    ingredient_name = sample_recipe.ingredients[0].name

    response = client.post("/settings/ingredients/move", data={"name": ingredient_name, "category": "pantry"})
    assert response.status_code == 200

    catalog = client.app.state.ingredient_catalog_store.get_all()
    flags = catalog[ingredient_name.strip().lower()]
    assert flags.pantry is True
    assert flags.never_buy is False


@pytest.mark.requirement("REQ-000000057")
def test_move_ingredient_to_never_buy_then_back_to_regular(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)
    ingredient_name = sample_recipe.ingredients[0].name

    client.post("/settings/ingredients/move", data={"name": ingredient_name, "category": "never_buy"})
    catalog = client.app.state.ingredient_catalog_store.get_all()
    assert catalog[ingredient_name.strip().lower()].never_buy is True

    client.post("/settings/ingredients/move", data={"name": ingredient_name, "category": "regular"})
    catalog = client.app.state.ingredient_catalog_store.get_all()
    flags = catalog[ingredient_name.strip().lower()]
    assert flags.pantry is False
    assert flags.never_buy is False


@pytest.mark.requirement("REQ-000000057")
def test_move_multiple_ingredients_at_once(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)
    names = [i.name for i in sample_recipe.ingredients]

    response = client.post(
        "/settings/ingredients/move",
        data={"name": [names[0], names[1]], "category": "pantry"},
    )
    assert response.status_code == 200

    catalog = client.app.state.ingredient_catalog_store.get_all()
    assert catalog[names[0].strip().lower()].pantry is True
    assert catalog[names[1].strip().lower()].pantry is True
    assert names[2].strip().lower() not in catalog


@pytest.mark.requirement("REQ-000000057")
def test_move_ingredient_with_invalid_category_is_a_no_op(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)
    ingredient_name = sample_recipe.ingredients[0].name

    response = client.post("/settings/ingredients/move", data={"name": ingredient_name, "category": "bogus"})
    assert response.status_code == 200

    catalog = client.app.state.ingredient_catalog_store.get_all()
    assert ingredient_name.strip().lower() not in catalog


@pytest.mark.requirement("REQ-000000057")
def test_ingredients_settings_filters_by_glob(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)
    non_matching = [i.name for i in sample_recipe.ingredients if "chicken" not in i.name.lower()]

    response = client.get("/settings/ingredients", params={"q": "*chicken*"})
    lists_text = response.text[response.text.index('id="ingredient-lists"') :].lower()
    assert "chicken breast" in lists_text
    for name in non_matching:
        assert name.lower() not in lists_text


@pytest.mark.requirement("REQ-000000057")
def test_ingredients_settings_add_tracks_a_new_name(client: TestClient):
    response = client.post("/settings/ingredients/add", data={"name": "water"}, follow_redirects=False)
    assert response.status_code == 303

    response = client.get("/settings/ingredients")
    assert "water" in response.text.lower()
