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


def _finalized_plan(client: TestClient, sample_recipe) -> dict:
    _create_recipe(client, sample_recipe)
    plan = client.post("/api/plan/generate").json()
    client.post(f"/api/plan/{plan['id']}/finalize")
    return client.get("/api/plan/current").json()


@pytest.mark.requirement("REQ-000000031")
def test_current_404_when_no_plan(client: TestClient):
    response = client.get("/api/shopping-list/current")
    assert response.status_code == 404
    assert response.json()["code"] == "NO_CURRENT_PLAN"


@pytest.mark.requirement("REQ-000000031")
def test_current_409_when_plan_not_finalized(client: TestClient):
    client.post("/api/plan/generate")
    response = client.get("/api/shopping-list/current")
    assert response.status_code == 409
    assert response.json()["code"] == "PLAN_NOT_FINALIZED"


@pytest.mark.requirement("REQ-000000031")
def test_current_404_when_finalized_but_not_generated(client: TestClient, sample_recipe):
    _finalized_plan(client, sample_recipe)
    response = client.get("/api/shopping-list/current")
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_GENERATED"


@pytest.mark.requirement("REQ-000000031")
def test_generate_requires_a_finalized_plan(client: TestClient):
    client.post("/api/plan/generate")
    response = client.post("/api/shopping-list/generate")
    assert response.status_code == 409


@pytest.mark.requirement("REQ-000000031")
def test_generate_creates_merged_items_from_the_plan(client: TestClient, sample_recipe):
    _finalized_plan(client, sample_recipe)

    response = client.post("/api/shopping-list/generate")
    assert response.status_code == 201
    body = response.json()
    assert len(body["items"]) == len(sample_recipe.ingredients)
    assert body["actual_cost"] is None


@pytest.mark.requirement("REQ-000000031")
def test_generate_is_idempotent(client: TestClient, sample_recipe):
    _finalized_plan(client, sample_recipe)

    first = client.post("/api/shopping-list/generate").json()
    second = client.post("/api/shopping-list/generate").json()
    assert first["id"] == second["id"]


@pytest.mark.requirement("REQ-000000031")
def test_current_returns_the_generated_list(client: TestClient, sample_recipe):
    _finalized_plan(client, sample_recipe)
    generated = client.post("/api/shopping-list/generate").json()

    response = client.get("/api/shopping-list/current")
    assert response.status_code == 200
    assert response.json()["id"] == generated["id"]


@pytest.mark.requirement("REQ-000000031")
def test_update_checked(client: TestClient, sample_recipe):
    _finalized_plan(client, sample_recipe)
    shopping_list = client.post("/api/shopping-list/generate").json()
    item_id = shopping_list["items"][0]["id"]

    response = client.patch(f"/api/shopping-list/{shopping_list['id']}/items/{item_id}/checked", json={"checked": True})
    assert response.status_code == 200
    assert response.json()["items"][0]["checked"] is True


@pytest.mark.requirement("REQ-000000031")
def test_update_checked_unknown_item_404(client: TestClient, sample_recipe):
    _finalized_plan(client, sample_recipe)
    shopping_list = client.post("/api/shopping-list/generate").json()

    response = client.patch(
        f"/api/shopping-list/{shopping_list['id']}/items/does-not-exist/checked", json={"checked": True}
    )
    assert response.status_code == 404


@pytest.mark.requirement("REQ-000000031")
def test_update_checked_unknown_list_404(client: TestClient):
    response = client.patch("/api/shopping-list/does-not-exist/items/i1/checked", json={"checked": True})
    assert response.status_code == 404


@pytest.mark.requirement("REQ-000000031")
def test_update_cost(client: TestClient, sample_recipe):
    _finalized_plan(client, sample_recipe)
    shopping_list = client.post("/api/shopping-list/generate").json()

    response = client.patch(f"/api/shopping-list/{shopping_list['id']}/cost", json={"actual_cost": 37.42})
    assert response.status_code == 200
    assert response.json()["actual_cost"] == 37.42


@pytest.mark.requirement("REQ-000000031")
def test_update_cost_unknown_list_404(client: TestClient):
    response = client.patch("/api/shopping-list/does-not-exist/cost", json={"actual_cost": 10.0})
    assert response.status_code == 404


@pytest.mark.requirement("REQ-000000031")
def test_update_cost_rejects_negative(client: TestClient, sample_recipe):
    _finalized_plan(client, sample_recipe)
    shopping_list = client.post("/api/shopping-list/generate").json()

    response = client.patch(f"/api/shopping-list/{shopping_list['id']}/cost", json={"actual_cost": -5})
    assert response.status_code == 400


@pytest.mark.requirement("REQ-000000031")
def test_get_by_id(client: TestClient, sample_recipe):
    _finalized_plan(client, sample_recipe)
    shopping_list = client.post("/api/shopping-list/generate").json()

    response = client.get(f"/api/shopping-list/{shopping_list['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == shopping_list["id"]


@pytest.mark.requirement("REQ-000000031")
def test_get_by_id_unknown_404(client: TestClient):
    response = client.get("/api/shopping-list/does-not-exist")
    assert response.status_code == 404
