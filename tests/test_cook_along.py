from __future__ import annotations

from fastapi.testclient import TestClient

from little_meals.store.plan_store import MealSpec


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


def test_cook_start_redirects_to_step_1(client: TestClient, sample_recipe):
    created = _create_recipe(client, sample_recipe)
    response = client.get(f"/recipes/{created['id']}/cook", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == f"/recipes/{created['id']}/cook/1"


def test_cook_step_shows_the_right_step_text(client: TestClient, sample_recipe):
    created = _create_recipe(client, sample_recipe)
    response = client.get(f"/recipes/{created['id']}/cook/2")
    assert response.status_code == 200
    assert sample_recipe.steps[1] in response.text
    assert "Step 2 of 3" in response.text


def test_cook_step_has_no_shell_nav(client: TestClient, sample_recipe):
    # Immersive mode - no bottom tab bar / top bar chrome.
    created = _create_recipe(client, sample_recipe)
    response = client.get(f"/recipes/{created['id']}/cook/1")
    assert 'class="tabbar"' not in response.text


def test_cook_step_unknown_recipe_404(client: TestClient):
    response = client.get("/recipes/does-not-exist/cook/1")
    assert response.status_code == 404


def test_cook_step_zero_or_negative_redirects_to_step_1(client: TestClient, sample_recipe):
    created = _create_recipe(client, sample_recipe)
    response = client.get(f"/recipes/{created['id']}/cook/0", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == f"/recipes/{created['id']}/cook/1"

    response = client.get(f"/recipes/{created['id']}/cook/-5", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == f"/recipes/{created['id']}/cook/1"


def test_cook_step_past_the_last_step_shows_finish_prompt(client: TestClient, sample_recipe):
    created = _create_recipe(client, sample_recipe)
    total_steps = len(sample_recipe.steps)

    response = client.get(f"/recipes/{created['id']}/cook/{total_steps + 1}")
    assert response.status_code == 200
    assert "Nicely done!" in response.text
    assert "Loved it" in response.text
    assert "Not for us" in response.text


def test_cook_step_last_step_shows_finish_cooking_label(client: TestClient, sample_recipe):
    created = _create_recipe(client, sample_recipe)
    total_steps = len(sample_recipe.steps)

    response = client.get(f"/recipes/{created['id']}/cook/{total_steps}")
    assert "Finish cooking" in response.text


def test_cook_finish_sets_preference_liked(client: TestClient, sample_recipe):
    created = _create_recipe(client, sample_recipe)

    response = client.post(f"/recipes/{created['id']}/cook/finish", data={"preference": "liked"})
    assert response.status_code == 200
    assert "Got it" in response.text
    assert "Saved as a favorite" in response.text

    recipe = client.get(f"/api/recipes/{created['id']}").json()
    assert recipe["preference"] == "liked"


def test_cook_finish_sets_preference_disliked(client: TestClient, sample_recipe):
    created = _create_recipe(client, sample_recipe)

    response = client.post(f"/recipes/{created['id']}/cook/finish", data={"preference": "disliked"})
    assert response.status_code == 200
    assert "suggest this one again" in response.text

    recipe = client.get(f"/api/recipes/{created['id']}").json()
    assert recipe["preference"] == "disliked"


def test_cook_finish_unknown_recipe_404(client: TestClient):
    response = client.post("/recipes/does-not-exist/cook/finish", data={"preference": "liked"})
    assert response.status_code == 404


def test_cook_finish_marks_matching_plan_meal_cooked(client: TestClient, sample_recipe, store, plan_store):
    created = store.create(sample_recipe)
    plan = plan_store.create([MealSpec(created.id, created.servings)])
    assert plan.meals[0].cooked is False

    client.post(f"/recipes/{created.id}/cook/finish", data={"preference": "liked"})

    updated = plan_store.get(plan.id)
    assert updated.meals[0].cooked is True


def test_cook_finish_is_a_no_op_on_plan_state_when_recipe_not_in_current_plan(
    client: TestClient, sample_recipe, store, plan_store
):
    created = store.create(sample_recipe)
    other = store.create(sample_recipe.model_copy(update={"id": "", "name": "Other"}))
    plan = plan_store.create([MealSpec(other.id, other.servings)])

    client.post(f"/recipes/{created.id}/cook/finish", data={"preference": "liked"})

    updated = plan_store.get(plan.id)
    assert updated.meals[0].cooked is False


def test_cook_finish_with_no_current_plan_does_not_error(client: TestClient, sample_recipe):
    created = _create_recipe(client, sample_recipe)
    response = client.post(f"/recipes/{created['id']}/cook/finish", data={"preference": "liked"})
    assert response.status_code == 200


def test_recipe_detail_has_cook_along_link(client: TestClient, sample_recipe):
    created = _create_recipe(client, sample_recipe)
    response = client.get(f"/recipes/{created['id']}")
    assert f'href="/recipes/{created["id"]}/cook"' in response.text


def test_plan_meal_card_has_cook_along_link(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)
    client.post("/plan/generate", follow_redirects=False)
    plan = client.get("/api/plan/current").json()
    recipe_id = plan["meals"][0]["recipe_id"]

    response = client.get("/plan")
    assert f'href="/recipes/{recipe_id}/cook"' in response.text
