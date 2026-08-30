from __future__ import annotations

import pytest
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


@pytest.mark.requirement("REQ-000000021")
def test_plan_page_shows_generate_prompt_when_no_plan_exists(client: TestClient):
    response = client.get("/plan")
    assert response.status_code == 200
    assert "Generate this week's plan" in response.text


@pytest.mark.requirement("REQ-000000021")
def test_plan_page_highlights_this_week_tab(client: TestClient):
    response = client.get("/plan")
    assert 'class="tab tab-active"' in response.text


@pytest.mark.requirement("REQ-000000021")
def test_generate_then_view_shows_the_meal(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)

    generate_response = client.post("/plan/generate", follow_redirects=False)
    assert generate_response.status_code == 303
    assert generate_response.headers["location"] == "/plan"

    response = client.get("/plan")
    assert response.status_code == 200
    assert sample_recipe.name in response.text
    assert "Mark cooked" in response.text


@pytest.mark.requirement("REQ-000000021")
def test_generate_with_empty_library_shows_empty_state(client: TestClient):
    client.post("/plan/generate", follow_redirects=False)
    response = client.get("/plan")
    assert "No recipes in the cookbook yet" in response.text


@pytest.mark.requirement("REQ-000000021")
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


@pytest.mark.requirement("REQ-000000021")
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


@pytest.mark.requirement("REQ-000000021")
def test_finalize_marks_plan_finalized_and_hides_the_button(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)
    client.post("/plan/generate", follow_redirects=False)

    finalize_response = client.post("/plan/finalize", follow_redirects=False)
    assert finalize_response.status_code == 303

    response = client.get("/plan")
    assert "Finalized" in response.text
    assert "Finalize plan" not in response.text


@pytest.mark.requirement("REQ-000000021")
def test_plan_nav_link_present_on_recipes_page(client: TestClient):
    response = client.get("/recipes")
    assert 'href="/plan"' in response.text


@pytest.mark.requirement("REQ-000000021")
def test_servings_update_redirects_when_no_current_plan(client: TestClient):
    response = client.post("/plan/meals/m1/servings", data={"servings": "3"}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/plan"


@pytest.mark.requirement("REQ-000000021")
def test_servings_update_redirects_when_meal_not_in_current_plan(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)
    client.post("/plan/generate", follow_redirects=False)

    response = client.post("/plan/meals/does-not-exist/servings", data={"servings": "3"}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/plan"


@pytest.mark.requirement("REQ-000000021")
def test_cooked_toggle_redirects_when_no_current_plan(client: TestClient):
    response = client.post("/plan/meals/m1/cooked", data={"cooked": "true"}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/plan"


@pytest.mark.requirement("REQ-000000021")
def test_cooked_toggle_redirects_when_meal_not_in_current_plan(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)
    client.post("/plan/generate", follow_redirects=False)

    response = client.post("/plan/meals/does-not-exist/cooked", data={"cooked": "true"}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/plan"


@pytest.mark.requirement("REQ-000000021")
def test_finalize_with_no_current_plan_is_a_harmless_redirect(client: TestClient):
    response = client.post("/plan/finalize", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/plan"


def test_plan_cancel_clears_the_plan(client: TestClient, sample_recipe, plan_store):
    _create_recipe(client, sample_recipe)
    client.post("/plan/generate", follow_redirects=False)
    assert plan_store.get_current() is not None

    response = client.post("/plan/cancel", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/plan"

    assert plan_store.get_current() is None
    response = client.get("/plan")
    assert "Generate this week's plan" in response.text


def test_plan_cancel_clears_the_shopping_list_too(client: TestClient, sample_recipe, plan_store, shopping_list_store):
    _create_recipe(client, sample_recipe)
    client.post("/plan/generate", follow_redirects=False)
    plan = plan_store.get_current()
    client.post("/plan/finalize", follow_redirects=False)
    client.post("/shopping/generate", follow_redirects=False)
    assert shopping_list_store.get_for_plan(plan.id) is not None

    client.post("/plan/cancel", follow_redirects=False)

    assert shopping_list_store.get_for_plan(plan.id) is None


def test_plan_cancel_is_a_no_op_when_no_current_plan(client: TestClient, plan_store):
    response = client.post("/plan/cancel", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/plan"
    assert plan_store.count() == 0


def test_plan_cancel_works_when_finalized(client: TestClient, sample_recipe, plan_store):
    _create_recipe(client, sample_recipe)
    client.post("/plan/generate", follow_redirects=False)
    client.post("/plan/finalize", follow_redirects=False)

    client.post("/plan/cancel", follow_redirects=False)

    assert plan_store.get_current() is None


def test_plan_page_shows_cancel_button_when_plan_exists(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)
    client.post("/plan/generate", follow_redirects=False)

    response = client.get("/plan")
    assert 'action="/plan/cancel"' in response.text
    assert "Cancel week's plans" in response.text


def _set_preferences(client: TestClient, **overrides) -> None:
    payload = {
        "recipes_per_week": 1,
        "recommendation_day": "sunday",
        "recommendation_time": "09:00",
        "default_servings": "2 adults",
    }
    payload.update(overrides)
    client.put("/api/household-preferences", json=payload)


@pytest.mark.requirement("REQ-000000028")
def test_plan_preference_toggle_updates_the_recipe(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)
    client.post("/plan/generate", follow_redirects=False)
    plan = client.get("/api/plan/current").json()
    meal_id = plan["meals"][0]["id"]
    recipe_id = plan["meals"][0]["recipe_id"]

    response = client.post(f"/plan/meals/{meal_id}/preference", data={"preference": "disliked"})
    assert response.status_code == 200
    assert "thumb-disliked" in response.text

    recipe = client.get(f"/api/recipes/{recipe_id}").json()
    assert recipe["preference"] == "disliked"


@pytest.mark.requirement("REQ-000000028")
def test_plan_preference_toggle_redirects_when_no_current_plan(client: TestClient):
    response = client.post("/plan/meals/m1/preference", data={"preference": "liked"}, follow_redirects=False)
    assert response.status_code == 303


@pytest.mark.requirement("REQ-000000028")
def test_plan_preference_toggle_redirects_when_meal_not_in_plan(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)
    client.post("/plan/generate", follow_redirects=False)
    response = client.post("/plan/meals/does-not-exist/preference", data={"preference": "liked"}, follow_redirects=False)
    assert response.status_code == 303


@pytest.mark.requirement("REQ-000000025")
def test_plan_reroll_whole_replaces_meals(client: TestClient, sample_recipe):
    created = _create_recipe(client, sample_recipe)
    _set_preferences(client)
    client.post("/plan/generate", follow_redirects=False)

    response = client.post("/plan/reroll", follow_redirects=False)
    assert response.status_code == 303

    plan = client.get("/api/plan/current").json()
    assert plan["meals"][0]["recipe_id"] == created["id"]


@pytest.mark.requirement("REQ-000000025")
def test_plan_reroll_whole_is_a_no_op_when_no_current_plan(client: TestClient):
    response = client.post("/plan/reroll", follow_redirects=False)
    assert response.status_code == 303


@pytest.mark.requirement("REQ-000000025")
def test_plan_reroll_whole_is_a_no_op_when_finalized(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)
    client.post("/plan/generate", follow_redirects=False)
    client.post("/plan/finalize", follow_redirects=False)
    before = client.get("/api/plan/current").json()

    client.post("/plan/reroll", follow_redirects=False)

    after = client.get("/api/plan/current").json()
    assert after["meals"] == before["meals"]


@pytest.mark.requirement("REQ-000000026")
def test_plan_meal_reroll_swaps_the_recipe(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)
    other = {
        "name": "Other Dish",
        "cook_time_minutes": sample_recipe.cook_time_minutes,
        "classification": sample_recipe.classification.value,
        "nutrition": sample_recipe.nutrition.model_dump(exclude_none=True),
        "servings": sample_recipe.servings,
        "ingredients": [i.model_dump(exclude_none=True) for i in sample_recipe.ingredients],
        "steps": sample_recipe.steps,
    }
    client.post("/api/recipes", json=other)
    _set_preferences(client)
    client.post("/plan/generate", follow_redirects=False)
    plan = client.get("/api/plan/current").json()
    meal_id = plan["meals"][0]["id"]
    original_recipe_id = plan["meals"][0]["recipe_id"]

    response = client.post(f"/plan/meals/{meal_id}/reroll", follow_redirects=False)
    assert response.status_code == 200
    assert f'id="plan-meal-{meal_id}"' in response.text

    updated = client.get("/api/plan/current").json()
    assert updated["meals"][0]["recipe_id"] != original_recipe_id


@pytest.mark.requirement("REQ-000000026")
def test_plan_meal_reroll_redirects_when_no_current_plan(client: TestClient):
    response = client.post("/plan/meals/m1/reroll", follow_redirects=False)
    assert response.status_code == 303


@pytest.mark.requirement("REQ-000000026")
def test_plan_meal_reroll_redirects_when_finalized(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)
    client.post("/plan/generate", follow_redirects=False)
    client.post("/plan/finalize", follow_redirects=False)
    plan = client.get("/api/plan/current").json()

    response = client.post(f"/plan/meals/{plan['meals'][0]['id']}/reroll", follow_redirects=False)
    assert response.status_code == 303


@pytest.mark.requirement("REQ-000000026")
def test_plan_meal_reroll_redirects_when_meal_not_in_plan(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)
    other = {
        "name": "Other Dish",
        "cook_time_minutes": sample_recipe.cook_time_minutes,
        "classification": sample_recipe.classification.value,
        "nutrition": sample_recipe.nutrition.model_dump(exclude_none=True),
        "servings": sample_recipe.servings,
        "ingredients": [i.model_dump(exclude_none=True) for i in sample_recipe.ingredients],
        "steps": sample_recipe.steps,
    }
    client.post("/api/recipes", json=other)
    _set_preferences(client)
    client.post("/plan/generate", follow_redirects=False)

    response = client.post("/plan/meals/does-not-exist/reroll", follow_redirects=False)
    assert response.status_code == 303


@pytest.mark.requirement("REQ-000000027")
def test_plan_meal_choose_redirects_when_meal_not_in_plan(client: TestClient, sample_recipe):
    created = _create_recipe(client, sample_recipe)
    client.post("/plan/generate", follow_redirects=False)

    response = client.post(
        "/plan/meals/does-not-exist/choose", data={"recipe_id": created["id"]}, follow_redirects=False
    )
    assert response.status_code == 303


@pytest.mark.requirement("REQ-000000026")
def test_plan_meal_reroll_with_nothing_available_rerenders_plan_page(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)
    _set_preferences(client)
    client.post("/plan/generate", follow_redirects=False)
    plan = client.get("/api/plan/current").json()

    response = client.post(f"/plan/meals/{plan['meals'][0]['id']}/reroll")
    assert response.status_code == 200
    assert "This week's plan" in response.text


@pytest.mark.requirement("REQ-000000027")
def test_plan_meal_alternatives_page_lists_unused_liked_recipes(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)
    other = {
        "name": "Other Dish",
        "cook_time_minutes": sample_recipe.cook_time_minutes,
        "classification": sample_recipe.classification.value,
        "nutrition": sample_recipe.nutrition.model_dump(exclude_none=True),
        "servings": sample_recipe.servings,
        "ingredients": [i.model_dump(exclude_none=True) for i in sample_recipe.ingredients],
        "steps": sample_recipe.steps,
    }
    client.post("/api/recipes", json=other)
    _set_preferences(client)
    client.post("/plan/generate", follow_redirects=False)
    plan = client.get("/api/plan/current").json()
    meal_id = plan["meals"][0]["id"]

    response = client.get(f"/plan/meals/{meal_id}/alternatives")
    assert response.status_code == 200
    assert "Pick a replacement" in response.text


@pytest.mark.requirement("REQ-000000027")
def test_plan_meal_alternatives_redirects_when_no_current_plan(client: TestClient):
    response = client.get("/plan/meals/m1/alternatives", follow_redirects=False)
    assert response.status_code == 303


@pytest.mark.requirement("REQ-000000027")
def test_plan_meal_alternatives_redirects_when_meal_not_in_plan(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)
    client.post("/plan/generate", follow_redirects=False)
    response = client.get("/plan/meals/does-not-exist/alternatives", follow_redirects=False)
    assert response.status_code == 303


@pytest.mark.requirement("REQ-000000027")
def test_plan_meal_choose_sets_the_recipe(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)
    other = {
        "name": "Other Dish",
        "cook_time_minutes": sample_recipe.cook_time_minutes,
        "classification": sample_recipe.classification.value,
        "nutrition": sample_recipe.nutrition.model_dump(exclude_none=True),
        "servings": sample_recipe.servings,
        "ingredients": [i.model_dump(exclude_none=True) for i in sample_recipe.ingredients],
        "steps": sample_recipe.steps,
    }
    other_created = client.post("/api/recipes", json=other).json()
    _set_preferences(client)
    client.post("/plan/generate", follow_redirects=False)
    plan = client.get("/api/plan/current").json()
    meal_id = plan["meals"][0]["id"]

    response = client.post(f"/plan/meals/{meal_id}/choose", data={"recipe_id": other_created["id"]}, follow_redirects=False)
    assert response.status_code == 303

    updated = client.get("/api/plan/current").json()
    assert updated["meals"][0]["recipe_id"] == other_created["id"]


@pytest.mark.requirement("REQ-000000027")
def test_plan_meal_choose_redirects_when_no_current_plan(client: TestClient):
    response = client.post("/plan/meals/m1/choose", data={"recipe_id": "does-not-exist"}, follow_redirects=False)
    assert response.status_code == 303


@pytest.mark.requirement("REQ-000000027")
def test_plan_meal_choose_redirects_when_finalized(client: TestClient, sample_recipe):
    created = _create_recipe(client, sample_recipe)
    client.post("/plan/generate", follow_redirects=False)
    client.post("/plan/finalize", follow_redirects=False)
    plan = client.get("/api/plan/current").json()

    response = client.post(
        f"/plan/meals/{plan['meals'][0]['id']}/choose", data={"recipe_id": created["id"]}, follow_redirects=False
    )
    assert response.status_code == 303


@pytest.mark.requirement("REQ-000000027")
def test_plan_meal_choose_with_unknown_recipe_redirects(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)
    client.post("/plan/generate", follow_redirects=False)
    plan = client.get("/api/plan/current").json()

    response = client.post(
        f"/plan/meals/{plan['meals'][0]['id']}/choose", data={"recipe_id": "does-not-exist"}, follow_redirects=False
    )
    assert response.status_code == 303


@pytest.mark.requirement("REQ-000000021")
def test_plan_page_skips_meals_whose_recipe_was_since_deleted(client: TestClient, sample_recipe):
    created = _create_recipe(client, sample_recipe)
    client.post("/plan/generate", follow_redirects=False)
    client.post(f"/recipes/{created['id']}/delete")

    response = client.get("/plan")
    assert response.status_code == 200
    assert sample_recipe.name not in response.text


