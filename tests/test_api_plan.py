from __future__ import annotations

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from little_meals.api.app import create_app
from little_meals.config import Settings
from little_meals.llm.extraction import RecipeExtractionService
from little_meals.llm.ollama_client import OllamaClient
from little_meals.store.household_store import HouseholdPreferencesStore
from little_meals.store.notification_store import NotificationStore
from little_meals.store.plan_store import MealPlanStore
from little_meals.store.recipe_store import RecipeStore
from little_meals.store.shopping_list_store import ShoppingListStore

VALID_EXTRACTED = {
    "name": "Fusion Bowl",
    "cook_time_minutes": 25,
    "classification": "vegetarian",
    "nutrition": {"calories_per_serving": 420},
    "servings": 2,
    "ingredients": [{"name": "rice", "quantity": 1, "unit": "cup"}],
    "steps": ["Cook it."],
}


class _FakeSearchProvider:
    """Always returns 3 candidates, regardless of the filter - for exercising
    the suggestion-candidate endpoints, which the default NullSearchProvider-
    backed `client` fixture can never produce a suggestion meal to test."""

    def search_many(self, food_filter, count: int) -> list[str]:
        return [f"candidate {i}" for i in range(count)]

    def get_substitutes(self, ingredient_name: str):
        return None


def _client_with_suggestions(tmp_path) -> TestClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": json.dumps(VALID_EXTRACTED)})

    ollama_client = OllamaClient(
        "http://ollama.test", "test-model", 5.0, client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    settings = Settings(data_dir=tmp_path)
    app = create_app(
        settings=settings,
        store=RecipeStore(tmp_path / "recipes"),
        extractor=RecipeExtractionService(ollama_client),
        household_store=HouseholdPreferencesStore(tmp_path / "household.db"),
        plan_store=MealPlanStore(tmp_path / "plan.db"),
        search_provider=_FakeSearchProvider(),
        shopping_list_store=ShoppingListStore(tmp_path / "shopping_list.db"),
        notification_store=NotificationStore(tmp_path / "notification.db"),
    )
    return TestClient(app)


def _generate_one_suggestion_plan(client: TestClient) -> dict:
    client.put(
        "/api/household-preferences",
        json={
            "recipes_per_week": 1,
            "recommendation_day": "sunday",
            "recommendation_time": "09:00",
            "ai_suggestions_per_plan": 1,
            "default_servings": "2 adults",
        },
    )
    return client.post("/api/plan/generate").json()


@pytest.mark.requirement("REQ-000000020")
def test_current_plan_404_when_none_generated(client: TestClient):
    response = client.get("/api/plan/current")
    assert response.status_code == 404
    assert response.json()["code"] == "NO_CURRENT_PLAN"


@pytest.mark.requirement("REQ-000000020")
def test_generate_creates_a_plan_from_liked_library_recipes(client: TestClient, sample_recipe):
    created = client.post("/api/recipes", json=_recipe_create_payload(sample_recipe)).json()
    client.put(
        "/api/household-preferences",
        json={
            "recipes_per_week": 5,
            "recommendation_day": "sunday",
            "recommendation_time": "09:00",
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


@pytest.mark.requirement("REQ-000000020")
def test_generate_excludes_disliked_recipes(client: TestClient, sample_recipe):
    created = client.post("/api/recipes", json=_recipe_create_payload(sample_recipe)).json()
    client.patch(f"/api/recipes/{created['id']}/preference", json={"preference": "disliked"})

    response = client.post("/api/plan/generate")
    assert response.status_code == 201
    assert response.json()["meals"] == []


@pytest.mark.requirement("REQ-000000020")
def test_current_plan_returns_the_generated_plan(client: TestClient):
    generated = client.post("/api/plan/generate").json()

    response = client.get("/api/plan/current")
    assert response.status_code == 200
    assert response.json()["id"] == generated["id"]


@pytest.mark.requirement("REQ-000000020")
def test_update_servings(client: TestClient, sample_recipe):
    client.post("/api/recipes", json=_recipe_create_payload(sample_recipe))
    plan = client.post("/api/plan/generate").json()
    meal_id = plan["meals"][0]["id"]

    response = client.patch(f"/api/plan/{plan['id']}/meals/{meal_id}/servings", json={"servings": 6})
    assert response.status_code == 200
    assert response.json()["meals"][0]["servings"] == 6


@pytest.mark.requirement("REQ-000000020")
def test_update_servings_unknown_meal_404(client: TestClient):
    plan = client.post("/api/plan/generate").json()
    response = client.patch(f"/api/plan/{plan['id']}/meals/does-not-exist/servings", json={"servings": 6})
    assert response.status_code == 404


@pytest.mark.requirement("REQ-000000020")
def test_update_cooked(client: TestClient, sample_recipe):
    client.post("/api/recipes", json=_recipe_create_payload(sample_recipe))
    plan = client.post("/api/plan/generate").json()
    meal_id = plan["meals"][0]["id"]

    response = client.patch(f"/api/plan/{plan['id']}/meals/{meal_id}/cooked", json={"cooked": True})
    assert response.status_code == 200
    assert response.json()["meals"][0]["cooked"] is True


@pytest.mark.requirement("REQ-000000020")
def test_finalize_marks_plan_finalized(client: TestClient):
    plan = client.post("/api/plan/generate").json()

    response = client.post(f"/api/plan/{plan['id']}/finalize")
    assert response.status_code == 200
    assert response.json()["finalized"] is True


@pytest.mark.requirement("REQ-000000020")
def test_finalize_unknown_plan_404(client: TestClient):
    response = client.post("/api/plan/does-not-exist/finalize")
    assert response.status_code == 404


@pytest.mark.requirement("REQ-000000020")
def test_get_plan_by_id(client: TestClient):
    plan = client.post("/api/plan/generate").json()
    response = client.get(f"/api/plan/{plan['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == plan["id"]


@pytest.mark.requirement("REQ-000000020")
def test_get_plan_by_id_unknown_404(client: TestClient):
    response = client.get("/api/plan/does-not-exist")
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


@pytest.mark.requirement("REQ-000000020")
def test_update_cooked_unknown_meal_404(client: TestClient):
    plan = client.post("/api/plan/generate").json()
    response = client.patch(f"/api/plan/{plan['id']}/meals/does-not-exist/cooked", json={"cooked": True})
    assert response.status_code == 404


@pytest.mark.requirement("REQ-000000025")
def test_reroll_whole_plan_replaces_meals_but_keeps_plan_id(client: TestClient, sample_recipe):
    created = client.post("/api/recipes", json=_recipe_create_payload(sample_recipe)).json()
    plan = client.post("/api/plan/generate").json()

    response = client.post(f"/api/plan/{plan['id']}/reroll")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == plan["id"]
    assert body["meals"][0]["recipe_id"] == created["id"]


@pytest.mark.requirement("REQ-000000025")
def test_reroll_whole_plan_on_finalized_plan_409(client: TestClient):
    plan = client.post("/api/plan/generate").json()
    client.post(f"/api/plan/{plan['id']}/finalize")

    response = client.post(f"/api/plan/{plan['id']}/reroll")
    assert response.status_code == 409
    assert response.json()["code"] == "PLAN_FINALIZED"


@pytest.mark.requirement("REQ-000000026")
def test_reroll_single_meal_swaps_in_an_unused_library_recipe(client: TestClient, sample_recipe):
    created = client.post("/api/recipes", json=_recipe_create_payload(sample_recipe)).json()
    other = {**_recipe_create_payload(sample_recipe), "name": "Other Dish"}
    other_created = client.post("/api/recipes", json=other).json()
    both_ids = {created["id"], other_created["id"]}

    client.put(
        "/api/household-preferences",
        json={
            "recipes_per_week": 1,
            "recommendation_day": "sunday",
            "recommendation_time": "09:00",
            "ai_suggestions_per_plan": 0,
            "default_servings": "2 adults",
        },
    )
    plan = client.post("/api/plan/generate").json()
    meal_id = plan["meals"][0]["id"]
    original_recipe_id = plan["meals"][0]["recipe_id"]

    response = client.post(f"/api/plan/{plan['id']}/meals/{meal_id}/reroll")
    assert response.status_code == 200
    new_recipe_id = response.json()["meals"][0]["recipe_id"]
    assert new_recipe_id != original_recipe_id
    assert new_recipe_id in both_ids


@pytest.mark.requirement("REQ-000000026")
def test_reroll_single_meal_422_when_nothing_available(client: TestClient, sample_recipe):
    client.post("/api/recipes", json=_recipe_create_payload(sample_recipe))
    client.put(
        "/api/household-preferences",
        json={
            "recipes_per_week": 1,
            "recommendation_day": "sunday",
            "recommendation_time": "09:00",
            "ai_suggestions_per_plan": 0,
            "default_servings": "2 adults",
        },
    )
    plan = client.post("/api/plan/generate").json()
    meal_id = plan["meals"][0]["id"]

    response = client.post(f"/api/plan/{plan['id']}/meals/{meal_id}/reroll")
    assert response.status_code == 422
    assert response.json()["code"] == "NO_REPLACEMENT_AVAILABLE"


@pytest.mark.requirement("REQ-000000026")
def test_reroll_single_meal_on_finalized_plan_409(client: TestClient, sample_recipe):
    client.post("/api/recipes", json=_recipe_create_payload(sample_recipe))
    plan = client.post("/api/plan/generate").json()
    client.post(f"/api/plan/{plan['id']}/finalize")

    response = client.post(f"/api/plan/{plan['id']}/meals/{plan['meals'][0]['id']}/reroll")
    assert response.status_code == 409


@pytest.mark.requirement("REQ-000000027")
def test_controlled_reroll_alternatives_excludes_meals_already_in_plan(client: TestClient, sample_recipe):
    created = client.post("/api/recipes", json=_recipe_create_payload(sample_recipe)).json()
    other = {**_recipe_create_payload(sample_recipe), "name": "Other Dish"}
    other_created = client.post("/api/recipes", json=other).json()
    both_ids = {created["id"], other_created["id"]}
    client.put(
        "/api/household-preferences",
        json={
            "recipes_per_week": 1,
            "recommendation_day": "sunday",
            "recommendation_time": "09:00",
            "ai_suggestions_per_plan": 0,
            "default_servings": "2 adults",
        },
    )
    plan = client.post("/api/plan/generate").json()
    meal_id = plan["meals"][0]["id"]

    response = client.get(f"/api/plan/{plan['id']}/meals/{meal_id}/alternatives")
    assert response.status_code == 200
    ids = [r["id"] for r in response.json()]
    # Whichever of the two liked recipes ISN'T already in the plan (selection
    # is randomized) should show up as the one available alternative.
    assert ids == list(both_ids - {plan["meals"][0]["recipe_id"]})
    assert plan["meals"][0]["recipe_id"] not in ids


@pytest.mark.requirement("REQ-000000027")
def test_controlled_reroll_alternatives_unknown_meal_404(client: TestClient):
    plan = client.post("/api/plan/generate").json()
    response = client.get(f"/api/plan/{plan['id']}/meals/does-not-exist/alternatives")
    assert response.status_code == 404


@pytest.mark.requirement("REQ-000000027")
def test_choose_alternative_sets_the_recipe(client: TestClient, sample_recipe):
    client.post("/api/recipes", json=_recipe_create_payload(sample_recipe))
    other = {**_recipe_create_payload(sample_recipe), "name": "Other Dish"}
    other_created = client.post("/api/recipes", json=other).json()
    client.put(
        "/api/household-preferences",
        json={
            "recipes_per_week": 1,
            "recommendation_day": "sunday",
            "recommendation_time": "09:00",
            "ai_suggestions_per_plan": 0,
            "default_servings": "2 adults",
        },
    )
    plan = client.post("/api/plan/generate").json()
    meal_id = plan["meals"][0]["id"]

    response = client.post(f"/api/plan/{plan['id']}/meals/{meal_id}/choose", json={"recipe_id": other_created["id"]})
    assert response.status_code == 200
    assert response.json()["meals"][0]["recipe_id"] == other_created["id"]


@pytest.mark.requirement("REQ-000000027")
def test_choose_alternative_unknown_recipe_404(client: TestClient):
    plan = client.post("/api/plan/generate").json()
    response = client.post(
        f"/api/plan/{plan['id']}/meals/does-not-exist/choose", json={"recipe_id": "does-not-exist"}
    )
    assert response.status_code == 404


@pytest.mark.requirement("REQ-000000027")
def test_choose_alternative_on_finalized_plan_409(client: TestClient, sample_recipe):
    created = client.post("/api/recipes", json=_recipe_create_payload(sample_recipe)).json()
    plan = client.post("/api/plan/generate").json()
    client.post(f"/api/plan/{plan['id']}/finalize")

    response = client.post(
        f"/api/plan/{plan['id']}/meals/m1/choose", json={"recipe_id": created["id"]}
    )
    assert response.status_code == 409


def test_suggestion_candidates_lists_the_other_fetched_recipes(tmp_path):
    client = _client_with_suggestions(tmp_path)
    plan = _generate_one_suggestion_plan(client)
    meal = plan["meals"][0]
    assert meal["is_suggestion"] is True

    response = client.get(f"/api/plan/{plan['id']}/meals/{meal['id']}/suggestions")
    assert response.status_code == 200
    others = response.json()
    assert len(others) == 2
    assert meal["recipe_id"] not in {r["id"] for r in others}


def test_suggestion_candidates_unknown_meal_404(tmp_path):
    client = _client_with_suggestions(tmp_path)
    plan = _generate_one_suggestion_plan(client)
    response = client.get(f"/api/plan/{plan['id']}/meals/does-not-exist/suggestions")
    assert response.status_code == 404


def test_choose_suggestion_swaps_in_a_sibling_candidate(tmp_path):
    client = _client_with_suggestions(tmp_path)
    plan = _generate_one_suggestion_plan(client)
    meal = plan["meals"][0]
    other = client.get(f"/api/plan/{plan['id']}/meals/{meal['id']}/suggestions").json()[0]

    response = client.post(f"/api/plan/{plan['id']}/meals/{meal['id']}/choose-suggestion", json={"recipe_id": other["id"]})
    assert response.status_code == 200
    updated_meal = response.json()["meals"][0]
    assert updated_meal["recipe_id"] == other["id"]
    assert updated_meal["is_suggestion"] is True

    # The full candidate set survives the swap - the household can toggle
    # back to the other options without a new fetch.
    still_offered = client.get(f"/api/plan/{plan['id']}/meals/{meal['id']}/suggestions").json()
    assert meal["recipe_id"] in {r["id"] for r in still_offered}


def test_choose_suggestion_rejects_a_non_candidate_recipe(tmp_path):
    client = _client_with_suggestions(tmp_path)
    plan = _generate_one_suggestion_plan(client)
    meal = plan["meals"][0]

    response = client.post(
        f"/api/plan/{plan['id']}/meals/{meal['id']}/choose-suggestion", json={"recipe_id": "not-a-candidate"}
    )
    assert response.status_code == 422
    assert response.json()["code"] == "NOT_A_CANDIDATE"


def test_choose_suggestion_on_finalized_plan_409(tmp_path):
    client = _client_with_suggestions(tmp_path)
    plan = _generate_one_suggestion_plan(client)
    meal = plan["meals"][0]
    client.post(f"/api/plan/{plan['id']}/finalize")

    response = client.post(
        f"/api/plan/{plan['id']}/meals/{meal['id']}/choose-suggestion", json={"recipe_id": meal["recipe_id"]}
    )
    assert response.status_code == 409


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
