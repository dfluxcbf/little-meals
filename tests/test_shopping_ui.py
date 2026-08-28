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


@pytest.mark.requirement("REQ-000000032")
def test_shopping_page_prompts_for_a_plan_when_none_exists(client: TestClient):
    response = client.get("/shopping")
    assert response.status_code == 200
    assert "generate this week's plan" in response.text


@pytest.mark.requirement("REQ-000000032")
def test_shopping_page_prompts_to_finalize_when_plan_is_a_draft(client: TestClient):
    client.post("/plan/generate", follow_redirects=False)
    response = client.get("/shopping")
    assert "Finalize this week's plan" in response.text


@pytest.mark.requirement("REQ-000000032")
def test_shopping_page_highlights_shopping_tab(client: TestClient):
    response = client.get("/shopping")
    assert 'class="tab tab-active"' in response.text


@pytest.mark.requirement("REQ-000000032")
def test_shopping_page_offers_generate_once_finalized(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)
    client.post("/plan/generate", follow_redirects=False)
    client.post("/plan/finalize", follow_redirects=False)

    response = client.get("/shopping")
    assert "Generate shopping list" in response.text


@pytest.mark.requirement("REQ-000000032")
def test_shopping_generate_then_view_shows_items(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)
    client.post("/plan/generate", follow_redirects=False)
    client.post("/plan/finalize", follow_redirects=False)

    generate_response = client.post("/shopping/generate", follow_redirects=False)
    assert generate_response.status_code == 303

    response = client.get("/shopping")
    assert response.status_code == 200
    assert sample_recipe.ingredients[0].name in response.text


@pytest.mark.requirement("REQ-000000032")
def test_shopping_generate_is_a_no_op_when_plan_not_finalized(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)
    client.post("/plan/generate", follow_redirects=False)

    response = client.post("/shopping/generate", follow_redirects=False)
    assert response.status_code == 303
    assert client.get("/api/shopping-list/current").status_code != 200


@pytest.mark.requirement("REQ-000000032")
def test_shopping_item_checked_returns_fragment_and_persists(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)
    client.post("/plan/generate", follow_redirects=False)
    client.post("/plan/finalize", follow_redirects=False)
    client.post("/shopping/generate", follow_redirects=False)
    shopping_list = client.get("/api/shopping-list/current").json()
    item_id = shopping_list["items"][0]["id"]

    response = client.post(f"/shopping/items/{item_id}/checked", data={"checked": "true"})
    assert response.status_code == 200
    assert "<html" not in response.text.lower()
    assert f'id="shopping-item-{item_id}"' in response.text
    assert "shopping-item-checked" in response.text

    refreshed = client.get("/api/shopping-list/current").json()
    assert refreshed["items"][0]["checked"] is True


@pytest.mark.requirement("REQ-000000032")
def test_shopping_item_checked_redirects_when_no_plan(client: TestClient):
    response = client.post("/shopping/items/i1/checked", data={"checked": "true"}, follow_redirects=False)
    assert response.status_code == 303


@pytest.mark.requirement("REQ-000000032")
def test_shopping_item_checked_redirects_when_no_list_generated(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)
    client.post("/plan/generate", follow_redirects=False)
    client.post("/plan/finalize", follow_redirects=False)

    response = client.post("/shopping/items/i1/checked", data={"checked": "true"}, follow_redirects=False)
    assert response.status_code == 303


@pytest.mark.requirement("REQ-000000032")
def test_shopping_item_checked_redirects_when_item_unknown(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)
    client.post("/plan/generate", follow_redirects=False)
    client.post("/plan/finalize", follow_redirects=False)
    client.post("/shopping/generate", follow_redirects=False)

    response = client.post("/shopping/items/does-not-exist/checked", data={"checked": "true"}, follow_redirects=False)
    assert response.status_code == 303


@pytest.mark.requirement("REQ-000000032")
def test_shopping_cost_form_saves(client: TestClient, sample_recipe):
    _create_recipe(client, sample_recipe)
    client.post("/plan/generate", follow_redirects=False)
    client.post("/plan/finalize", follow_redirects=False)
    client.post("/shopping/generate", follow_redirects=False)

    response = client.post("/shopping/cost", data={"actual_cost": "28.75"}, follow_redirects=False)
    assert response.status_code == 303

    shopping_list = client.get("/api/shopping-list/current").json()
    assert shopping_list["actual_cost"] == 28.75

    page = client.get("/shopping")
    assert 'value="28.75"' in page.text


@pytest.mark.requirement("REQ-000000032")
def test_shopping_cost_form_is_a_no_op_with_no_list(client: TestClient):
    response = client.post("/shopping/cost", data={"actual_cost": "10.00"}, follow_redirects=False)
    assert response.status_code == 303


@pytest.mark.requirement("REQ-000000032")
def test_shopping_nav_link_present_on_recipes_page(client: TestClient):
    response = client.get("/recipes")
    assert 'href="/shopping"' in response.text
