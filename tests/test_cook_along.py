from __future__ import annotations

import pytest
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


@pytest.mark.requirement("REQ-000000033")
def test_cook_start_redirects_to_step_0_on_a_fresh_recipe(client: TestClient, sample_recipe):
    created = _create_recipe(client, sample_recipe)
    response = client.get(f"/recipes/{created['id']}/cook", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == f"/recipes/{created['id']}/cook/0"


@pytest.mark.requirement("REQ-000000033")
def test_cook_start_with_an_existing_session_shows_resume_chooser(client: TestClient, sample_recipe):
    created = _create_recipe(client, sample_recipe)
    client.get(f"/recipes/{created['id']}/cook", follow_redirects=False)
    client.get(f"/recipes/{created['id']}/cook/2")

    response = client.get(f"/recipes/{created['id']}/cook")
    assert response.status_code == 200
    assert "Continue" in response.text
    assert "Start Over" in response.text
    assert f'href="/recipes/{created["id"]}/cook/2"' in response.text


@pytest.mark.requirement("REQ-000000033")
def test_cook_start_over_resets_the_session(client: TestClient, sample_recipe, cook_along_store):
    created = _create_recipe(client, sample_recipe)
    client.get(f"/recipes/{created['id']}/cook", follow_redirects=False)
    client.get(f"/recipes/{created['id']}/cook/2")

    response = client.post(f"/recipes/{created['id']}/cook/start-over", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == f"/recipes/{created['id']}/cook/0"

    session = cook_along_store.get(created["id"])
    assert session.current_step == 0
    assert session.checked_ingredients == []


@pytest.mark.requirement("REQ-000000033")
def test_cook_step_0_shows_ingredients_checklist(client: TestClient, sample_recipe):
    created = _create_recipe(client, sample_recipe)
    response = client.get(f"/recipes/{created['id']}/cook/0")
    assert response.status_code == 200
    assert "Ingredients" in response.text
    for ingredient in sample_recipe.ingredients:
        assert ingredient.name in response.text


@pytest.mark.requirement("REQ-000000033")
def test_cook_step_shows_the_right_step_text(client: TestClient, sample_recipe):
    created = _create_recipe(client, sample_recipe)
    response = client.get(f"/recipes/{created['id']}/cook/2")
    assert response.status_code == 200
    assert sample_recipe.steps[1] in response.text
    assert "Step 2 of 3" in response.text


@pytest.mark.requirement("REQ-000000033")
def test_cook_step_has_no_shell_nav(client: TestClient, sample_recipe):
    # Immersive mode - no bottom tab bar / top bar chrome.
    created = _create_recipe(client, sample_recipe)
    response = client.get(f"/recipes/{created['id']}/cook/1")
    assert 'class="tabbar"' not in response.text


@pytest.mark.requirement("REQ-000000033")
def test_cook_step_unknown_recipe_404(client: TestClient):
    response = client.get("/recipes/does-not-exist/cook/1")
    assert response.status_code == 404


@pytest.mark.requirement("REQ-000000033")
def test_cook_step_negative_redirects_to_step_0(client: TestClient, sample_recipe):
    created = _create_recipe(client, sample_recipe)
    response = client.get(f"/recipes/{created['id']}/cook/-5", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == f"/recipes/{created['id']}/cook/0"


@pytest.mark.requirement("REQ-000000033")
def test_cook_step_past_the_last_step_with_no_active_plan_shows_fallback_actions(client: TestClient, sample_recipe):
    created = _create_recipe(client, sample_recipe)
    total_steps = len(sample_recipe.steps)

    response = client.get(f"/recipes/{created['id']}/cook/{total_steps + 1}")
    assert response.status_code == 200
    assert sample_recipe.name in response.text
    assert "Return to recipe" in response.text
    assert "Finish recipe" in response.text
    assert "Mark as cooked" not in response.text
    assert "Leave uncooked" not in response.text


@pytest.mark.requirement("REQ-000000033")
def test_cook_step_past_the_last_step_with_finalized_plan_shows_cooked_buttons(
    client: TestClient, sample_recipe, store, plan_store
):
    created = store.create(sample_recipe)
    plan = plan_store.create([MealSpec(created.id, created.servings)])
    plan_store.finalize(plan.id)
    total_steps = len(created.steps)

    response = client.get(f"/recipes/{created.id}/cook/{total_steps + 1}")
    assert response.status_code == 200
    assert "Mark as cooked" in response.text
    assert "Leave uncooked" in response.text
    # Return to recipe stays available alongside the cooked buttons.
    assert "Return to recipe" in response.text


@pytest.mark.requirement("REQ-000000033")
def test_cook_step_past_the_last_step_with_draft_plan_shows_fallback_actions(
    client: TestClient, sample_recipe, store, plan_store
):
    created = store.create(sample_recipe)
    plan_store.create([MealSpec(created.id, created.servings)])  # left as a draft, not finalized
    total_steps = len(created.steps)

    response = client.get(f"/recipes/{created.id}/cook/{total_steps + 1}")
    assert response.status_code == 200
    assert "Mark as cooked" not in response.text
    assert "Leave uncooked" not in response.text
    assert "Finish recipe" in response.text


@pytest.mark.requirement("REQ-000000033")
def test_cook_step_last_step_shows_finish_cooking_label(client: TestClient, sample_recipe):
    created = _create_recipe(client, sample_recipe)
    total_steps = len(sample_recipe.steps)

    response = client.get(f"/recipes/{created['id']}/cook/{total_steps}")
    assert "Finish cooking" in response.text


@pytest.mark.requirement("REQ-000000033")
def test_cook_step_1_prev_link_points_to_ingredients(client: TestClient, sample_recipe):
    created = _create_recipe(client, sample_recipe)
    response = client.get(f"/recipes/{created['id']}/cook/1")
    assert f'href="/recipes/{created["id"]}/cook/0"' in response.text


@pytest.mark.requirement("REQ-000000033")
def test_cook_ingredient_toggle_flips_checked_state(client: TestClient, sample_recipe, cook_along_store):
    created = _create_recipe(client, sample_recipe)

    response = client.post(f"/recipes/{created['id']}/cook/ingredients/0/checked")
    assert response.status_code == 200
    session = cook_along_store.get(created["id"])
    assert session.checked_ingredients == [0]

    response = client.post(f"/recipes/{created['id']}/cook/ingredients/0/checked")
    assert response.status_code == 200
    session = cook_along_store.get(created["id"])
    assert session.checked_ingredients == []


@pytest.mark.requirement("REQ-000000033")
def test_cook_ingredient_toggle_unknown_recipe_404(client: TestClient):
    response = client.post("/recipes/does-not-exist/cook/ingredients/0/checked")
    assert response.status_code == 404


@pytest.mark.requirement("REQ-000000033")
def test_leaving_and_returning_resumes_at_the_saved_step(client: TestClient, sample_recipe):
    created = _create_recipe(client, sample_recipe)
    client.get(f"/recipes/{created['id']}/cook", follow_redirects=False)
    client.get(f"/recipes/{created['id']}/cook/2")

    # "Leaving" is just navigating away - no explicit action deletes the session.
    client.get(f"/recipes/{created['id']}")

    response = client.get(f"/recipes/{created['id']}/cook")
    assert response.status_code == 200
    assert f'href="/recipes/{created["id"]}/cook/2"' in response.text


@pytest.mark.requirement("REQ-000000034")
def test_cook_finish_marks_cooked(client: TestClient, sample_recipe):
    created = _create_recipe(client, sample_recipe)

    response = client.post(
        f"/recipes/{created['id']}/cook/finish", data={"action": "cooked"}, follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/recipes"


@pytest.mark.requirement("REQ-000000034")
def test_cook_finish_leave_uncooked(client: TestClient, sample_recipe):
    created = _create_recipe(client, sample_recipe)

    response = client.post(
        f"/recipes/{created['id']}/cook/finish", data={"action": "uncooked"}, follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/recipes"


@pytest.mark.requirement("REQ-000000034")
def test_cook_finish_unknown_recipe_404(client: TestClient):
    response = client.post("/recipes/does-not-exist/cook/finish", data={"action": "cooked"})
    assert response.status_code == 404


@pytest.mark.requirement("REQ-000000034")
def test_cook_finish_cooked_marks_matching_plan_meal_cooked(client: TestClient, sample_recipe, store, plan_store):
    created = store.create(sample_recipe)
    plan = plan_store.create([MealSpec(created.id, created.servings)])
    plan_store.finalize(plan.id)
    assert plan.meals[0].cooked is False

    client.post(f"/recipes/{created.id}/cook/finish", data={"action": "cooked"})

    updated = plan_store.get(plan.id)
    assert updated.meals[0].cooked is True


@pytest.mark.requirement("REQ-000000034")
def test_cook_finish_cooked_is_a_no_op_when_plan_is_a_draft(client: TestClient, sample_recipe, store, plan_store):
    created = store.create(sample_recipe)
    plan = plan_store.create([MealSpec(created.id, created.servings)])  # left as a draft, not finalized

    client.post(f"/recipes/{created.id}/cook/finish", data={"action": "cooked"})

    updated = plan_store.get(plan.id)
    assert updated.meals[0].cooked is False


@pytest.mark.requirement("REQ-000000034")
def test_cook_finish_uncooked_does_not_mark_plan_meal_cooked(client: TestClient, sample_recipe, store, plan_store):
    created = store.create(sample_recipe)
    plan = plan_store.create([MealSpec(created.id, created.servings)])

    client.post(f"/recipes/{created.id}/cook/finish", data={"action": "uncooked"})

    updated = plan_store.get(plan.id)
    assert updated.meals[0].cooked is False


@pytest.mark.requirement("REQ-000000034")
def test_cook_finish_is_a_no_op_on_plan_state_when_recipe_not_in_current_plan(
    client: TestClient, sample_recipe, store, plan_store
):
    created = store.create(sample_recipe)
    other = store.create(sample_recipe.model_copy(update={"id": "", "name": "Other"}))
    plan = plan_store.create([MealSpec(other.id, other.servings)])

    client.post(f"/recipes/{created.id}/cook/finish", data={"action": "cooked"})

    updated = plan_store.get(plan.id)
    assert updated.meals[0].cooked is False


@pytest.mark.requirement("REQ-000000034")
def test_cook_finish_with_no_current_plan_does_not_error(client: TestClient, sample_recipe):
    created = _create_recipe(client, sample_recipe)
    response = client.post(
        f"/recipes/{created['id']}/cook/finish", data={"action": "cooked"}, follow_redirects=False
    )
    assert response.status_code == 303


@pytest.mark.requirement("REQ-000000034")
@pytest.mark.parametrize("action", ["cooked", "uncooked"])
def test_cook_finish_clears_the_session(client: TestClient, sample_recipe, cook_along_store, action):
    created = _create_recipe(client, sample_recipe)
    client.get(f"/recipes/{created['id']}/cook", follow_redirects=False)
    assert cook_along_store.get(created["id"]) is not None

    client.post(f"/recipes/{created['id']}/cook/finish", data={"action": action})

    assert cook_along_store.get(created["id"]) is None


@pytest.mark.requirement("REQ-000000033")
def test_recipe_detail_has_cook_along_link(client: TestClient, sample_recipe):
    created = _create_recipe(client, sample_recipe)
    response = client.get(f"/recipes/{created['id']}")
    assert f'href="/recipes/{created["id"]}/cook"' in response.text


@pytest.mark.requirement("REQ-000000033")
def test_plan_meal_card_has_cook_along_link(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)
    client.post("/plan/generate", follow_redirects=False)
    plan = client.get("/api/plan/current").json()
    recipe_id = plan["meals"][0]["recipe_id"]

    response = client.get("/plan")
    assert f'href="/recipes/{recipe_id}/cook"' in response.text
