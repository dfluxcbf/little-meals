from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_current_plan_404_when_none_generated(client: TestClient):
    response = client.get("/api/plan/current")
    assert response.status_code == 404
    assert response.json()["code"] == "NO_CURRENT_PLAN"


def test_generate_creates_a_plan_from_liked_library_recipes(client: TestClient, sample_recipe):
    created = client.post("/api/recipes", json=_recipe_create_payload(sample_recipe)).json()
    client.put(
        "/api/household-preferences",
        json={
            "recipes_per_week": 5,
            "recommendation_day": "sunday",
            "recommendation_time": "09:00",
            "food_preferences": [],
            "ai_suggestions_per_plan": 0,
            "default_servings": "2 adults",
        },
    )

    response = client.post("/api/plan/generate")
    assert response.status_code == 201
    body = response.json()
    assert body["finalized"] is False
    assert len(body["meals"]) == 1
    assert body["meals"][0]["recipe_id"] == created["id"]
    assert body["meals"][0]["cooked"] is False


def test_generate_excludes_disliked_recipes(client: TestClient, sample_recipe):
    created = client.post("/api/recipes", json=_recipe_create_payload(sample_recipe)).json()
    client.patch(f"/api/recipes/{created['id']}/preference", json={"preference": "disliked"})

    response = client.post("/api/plan/generate")
    assert response.status_code == 201
    assert response.json()["meals"] == []


def test_current_plan_returns_the_generated_plan(client: TestClient):
    generated = client.post("/api/plan/generate").json()

    response = client.get("/api/plan/current")
    assert response.status_code == 200
    assert response.json()["id"] == generated["id"]


def test_update_servings(client: TestClient, sample_recipe):
    client.post("/api/recipes", json=_recipe_create_payload(sample_recipe))
    plan = client.post("/api/plan/generate").json()
    meal_id = plan["meals"][0]["id"]

    response = client.patch(f"/api/plan/{plan['id']}/meals/{meal_id}/servings", json={"servings": 6})
    assert response.status_code == 200
    assert response.json()["meals"][0]["servings"] == 6


def test_update_servings_unknown_meal_404(client: TestClient):
    plan = client.post("/api/plan/generate").json()
    response = client.patch(f"/api/plan/{plan['id']}/meals/does-not-exist/servings", json={"servings": 6})
    assert response.status_code == 404


def test_update_cooked(client: TestClient, sample_recipe):
    client.post("/api/recipes", json=_recipe_create_payload(sample_recipe))
    plan = client.post("/api/plan/generate").json()
    meal_id = plan["meals"][0]["id"]

    response = client.patch(f"/api/plan/{plan['id']}/meals/{meal_id}/cooked", json={"cooked": True})
    assert response.status_code == 200
    assert response.json()["meals"][0]["cooked"] is True


def test_finalize_marks_plan_finalized(client: TestClient):
    plan = client.post("/api/plan/generate").json()

    response = client.post(f"/api/plan/{plan['id']}/finalize")
    assert response.status_code == 200
    assert response.json()["finalized"] is True


def test_finalize_unknown_plan_404(client: TestClient):
    response = client.post("/api/plan/does-not-exist/finalize")
    assert response.status_code == 404


def test_get_plan_by_id(client: TestClient):
    plan = client.post("/api/plan/generate").json()
    response = client.get(f"/api/plan/{plan['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == plan["id"]


def test_get_plan_by_id_unknown_404(client: TestClient):
    response = client.get("/api/plan/does-not-exist")
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_update_cooked_unknown_meal_404(client: TestClient):
    plan = client.post("/api/plan/generate").json()
    response = client.patch(f"/api/plan/{plan['id']}/meals/does-not-exist/cooked", json={"cooked": True})
    assert response.status_code == 404


def _recipe_create_payload(recipe) -> dict:
    return {
        "name": recipe.name,
        "cook_time_minutes": recipe.cook_time_minutes,
        "classification": recipe.classification.value,
        "nutrition": recipe.nutrition.model_dump(exclude_none=True),
        "servings": recipe.servings,
        "ingredients": [ingredient.model_dump(exclude_none=True) for ingredient in recipe.ingredients],
        "steps": recipe.steps,
    }
