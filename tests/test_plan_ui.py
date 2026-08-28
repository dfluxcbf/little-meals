from __future__ import annotations

from fastapi.testclient import TestClient


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


def test_plan_page_shows_generate_prompt_when_no_plan_exists(client: TestClient):
    response = client.get("/plan")
    assert response.status_code == 200
    assert "Generate this week's plan" in response.text


def test_plan_page_highlights_this_week_tab(client: TestClient):
    response = client.get("/plan")
    assert 'class="tab tab-active"' in response.text


def test_generate_then_view_shows_the_meal(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)

    generate_response = client.post("/plan/generate", follow_redirects=False)
    assert generate_response.status_code == 303
    assert generate_response.headers["location"] == "/plan"

    response = client.get("/plan")
    assert response.status_code == 200
    assert sample_recipe.name in response.text
    assert "Mark cooked" in response.text


def test_generate_with_empty_library_shows_empty_state(client: TestClient):
    client.post("/plan/generate", follow_redirects=False)
    response = client.get("/plan")
    assert "No recipes in the cookbook yet" in response.text


def test_servings_update_returns_fragment_not_full_page(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)
    client.post("/plan/generate", follow_redirects=False)
    plan = client.get("/api/plan/current").json()
    meal_id = plan["meals"][0]["id"]

    response = client.post(f"/plan/meals/{meal_id}/servings", data={"servings": "7"})
    assert response.status_code == 200
    assert "<html" not in response.text.lower()
    assert f'id="plan-meal-{meal_id}"' in response.text
    assert 'value="7"' in response.text


def test_cooked_toggle_stamps_the_meal(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)
    client.post("/plan/generate", follow_redirects=False)
    plan = client.get("/api/plan/current").json()
    meal_id = plan["meals"][0]["id"]

    response = client.post(f"/plan/meals/{meal_id}/cooked", data={"cooked": "true"})
    assert response.status_code == 200
    assert "pot-stamp-active" in response.text
    assert "Cooked" in response.text
    assert "Mark cooked" not in response.text

    # Toggling again flips it back off.
    response = client.post(f"/plan/meals/{meal_id}/cooked", data={"cooked": "false"})
    assert "pot-stamp-active" not in response.text


def test_finalize_marks_plan_finalized_and_hides_the_button(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)
    client.post("/plan/generate", follow_redirects=False)

    finalize_response = client.post("/plan/finalize", follow_redirects=False)
    assert finalize_response.status_code == 303

    response = client.get("/plan")
    assert "Finalized" in response.text
    assert "Finalize plan" not in response.text


def test_plan_nav_link_present_on_recipes_page(client: TestClient):
    response = client.get("/recipes")
    assert 'href="/plan"' in response.text


def test_servings_update_redirects_when_no_current_plan(client: TestClient):
    response = client.post("/plan/meals/m1/servings", data={"servings": "3"}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/plan"


def test_servings_update_redirects_when_meal_not_in_current_plan(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)
    client.post("/plan/generate", follow_redirects=False)

    response = client.post("/plan/meals/does-not-exist/servings", data={"servings": "3"}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/plan"


def test_cooked_toggle_redirects_when_no_current_plan(client: TestClient):
    response = client.post("/plan/meals/m1/cooked", data={"cooked": "true"}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/plan"


def test_cooked_toggle_redirects_when_meal_not_in_current_plan(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)
    client.post("/plan/generate", follow_redirects=False)

    response = client.post("/plan/meals/does-not-exist/cooked", data={"cooked": "true"}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/plan"


def test_finalize_with_no_current_plan_is_a_harmless_redirect(client: TestClient):
    response = client.post("/plan/finalize", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/plan"


def test_plan_page_skips_meals_whose_recipe_was_since_deleted(client: TestClient, sample_recipe):
    created = _create_recipe(client, sample_recipe)
    client.post("/plan/generate", follow_redirects=False)
    client.post(f"/recipes/{created['id']}/delete")

    response = client.get("/plan")
    assert response.status_code == 200
    assert sample_recipe.name not in response.text
