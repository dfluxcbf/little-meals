from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from little_meals.api.app import create_app
from little_meals.config import Settings
from little_meals.store.recipe_store import RecipeStore

RECIPE_CREATE_PAYLOAD = {
    "name": "Pasta Aglio e Olio",
    "cook_time_minutes": 15,
    "classification": "vegetarian",
    "nutrition": {"calories_per_serving": 500},
    "servings": 2,
    "ingredients": [{"name": "spaghetti", "quantity": 200, "unit": "g"}],
    "steps": ["Boil pasta.", "Toss with garlic and oil."],
}


def _make_client(store: RecipeStore) -> TestClient:
    settings = Settings(data_dir=store._dir.parent)
    app = create_app(settings=settings, store=store)
    return TestClient(app)


@pytest.mark.requirement("REQ-000000006")
def test_create_list_get_update_delete_round_trip(store: RecipeStore):
    api = _make_client(store)

    created = api.post("/api/recipes", json=RECIPE_CREATE_PAYLOAD)
    assert created.status_code == 201
    recipe_id = created.json()["id"]

    listed = api.get("/api/recipes")
    assert listed.status_code == 200
    assert any(r["id"] == recipe_id for r in listed.json())

    fetched = api.get(f"/api/recipes/{recipe_id}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == RECIPE_CREATE_PAYLOAD["name"]

    update_payload = dict(RECIPE_CREATE_PAYLOAD, name="Pasta Aglio e Olio (updated)")
    updated = api.put(f"/api/recipes/{recipe_id}", json=update_payload)
    assert updated.status_code == 200
    assert updated.json()["name"] == "Pasta Aglio e Olio (updated)"

    deleted = api.delete(f"/api/recipes/{recipe_id}")
    assert deleted.status_code == 204

    missing = api.get(f"/api/recipes/{recipe_id}")
    assert missing.status_code == 404


def test_get_unknown_recipe_returns_error_envelope(store: RecipeStore):
    api = _make_client(store)
    response = api.get("/api/recipes/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "NOT_FOUND"
    assert "error" in body
    assert "details" in body


def test_malformed_create_body_returns_400(store: RecipeStore):
    api = _make_client(store)
    response = api.post("/api/recipes", json={"name": "Missing fields"})
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.requirement("REQ-000000050")
def test_create_recipe_with_difficulty(store: RecipeStore):
    api = _make_client(store)
    payload = dict(RECIPE_CREATE_PAYLOAD, difficulty="hard")

    response = api.post("/api/recipes", json=payload)
    assert response.status_code == 201
    assert response.json()["difficulty"] == "hard"


@pytest.mark.requirement("REQ-000000050")
def test_create_recipe_without_difficulty_defaults_to_undefined(store: RecipeStore):
    api = _make_client(store)
    response = api.post("/api/recipes", json=RECIPE_CREATE_PAYLOAD)
    assert response.status_code == 201
    assert response.json()["difficulty"] == "undefined"


@pytest.mark.requirement("REQ-000000053")
@pytest.mark.parametrize("classification", ["vegan", "ketogenic", "paleo"])
def test_create_recipe_accepts_additional_food_type_classifications(store: RecipeStore, classification: str):
    api = _make_client(store)
    payload = dict(RECIPE_CREATE_PAYLOAD, classification=classification)

    response = api.post("/api/recipes", json=payload)
    assert response.status_code == 201
    assert response.json()["classification"] == classification


def test_health_endpoint(store: RecipeStore):
    api = _make_client(store)
    response = api.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
