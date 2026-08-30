from __future__ import annotations

import json
from typing import Callable, Optional

import httpx
import pytest
from fastapi.testclient import TestClient

from little_meals.api.app import create_app
from little_meals.config import Settings
from little_meals.llm.extraction import RecipeExtractionService
from little_meals.llm.ollama_client import OllamaClient
from little_meals.store.recipe_store import RecipeStore

VALID_EXTRACT_PAYLOAD = {
    "name": "Tomato Soup",
    "cook_time_minutes": 20,
    "classification": "vegetarian",
    "nutrition": {"calories_per_serving": 180},
    "servings": 4,
    "ingredients": [{"name": "tomato", "quantity": 4, "unit": "pieces"}],
    "steps": ["Simmer the tomatoes.", "Blend until smooth."],
}

RECIPE_CREATE_PAYLOAD = {
    "name": "Pasta Aglio e Olio",
    "cook_time_minutes": 15,
    "classification": "vegetarian",
    "nutrition": {"calories_per_serving": 500},
    "servings": 2,
    "ingredients": [{"name": "spaghetti", "quantity": 200, "unit": "g"}],
    "steps": ["Boil pasta.", "Toss with garlic and oil."],
}


def _make_client(store: RecipeStore, handler: Optional[Callable[[httpx.Request], httpx.Response]] = None) -> TestClient:
    settings = Settings(data_dir=store._dir.parent)
    if handler is None:

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"response": json.dumps(VALID_EXTRACT_PAYLOAD)})

    ollama_client = OllamaClient(
        settings.ollama_base_url, settings.ollama_model, 5.0, client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    extractor = RecipeExtractionService(ollama_client)
    app = create_app(settings=settings, store=store, extractor=extractor)
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


def test_extract_success(store: RecipeStore):
    api = _make_client(store)
    response = api.post("/api/recipes/extract", json={"text": "a nice tomato soup"})
    assert response.status_code == 201
    assert response.json()["name"] == "Tomato Soup"


def test_extract_failure_returns_422(store: RecipeStore):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": "not json at all {"})

    api = _make_client(store, handler=handler)
    response = api.post("/api/recipes/extract", json={"text": "garbled input"})
    assert response.status_code == 422
    assert response.json()["code"] == "EXTRACTION_FAILED"


def test_extract_llm_unavailable_returns_503(store: RecipeStore):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    api = _make_client(store, handler=handler)
    response = api.post("/api/recipes/extract", json={"text": "anything"})
    assert response.status_code == 503
    assert response.json()["code"] == "LLM_UNAVAILABLE"


def test_malformed_create_body_returns_400(store: RecipeStore):
    api = _make_client(store)
    response = api.post("/api/recipes", json={"name": "Missing fields"})
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_health_endpoint(store: RecipeStore):
    api = _make_client(store)
    response = api.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "ollama" in body
