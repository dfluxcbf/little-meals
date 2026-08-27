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


@pytest.mark.requirement("REQ-000000007")
def test_recipes_list_contains_stored_recipe_name(store, sample_recipe):
    store.create(sample_recipe)
    ui = _make_client(store)

    response = ui.get("/recipes")
    assert response.status_code == 200
    assert sample_recipe.name in response.text


def test_recipe_detail_renders_ingredients_and_steps_in_order(store, sample_recipe):
    created = store.create(sample_recipe)
    ui = _make_client(store)

    response = ui.get(f"/recipes/{created.id}")
    assert response.status_code == 200
    text = response.text

    last_index = -1
    for ingredient in created.ingredients:
        index = text.find(ingredient.name)
        assert index != -1
        last_index = index

    for step in created.steps:
        index = text.find(step)
        assert index != -1
        assert index > last_index
        last_index = index


def test_recipe_detail_unknown_id_returns_404(store):
    ui = _make_client(store)
    response = ui.get("/recipes/does-not-exist")
    assert response.status_code == 404


def test_new_recipe_form_submit_creates_recipe_and_redirects(store):
    ui = _make_client(store)
    response = ui.post("/recipes", data={"text": "a nice tomato soup"}, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"].startswith("/recipes/")

    recipes = store.list()
    assert len(recipes) == 1
    assert recipes[0].name == "Tomato Soup"


def test_preference_toggle_returns_row_fragment_not_full_page(store, sample_recipe):
    created = store.create(sample_recipe)
    ui = _make_client(store)

    response = ui.post(f"/recipes/{created.id}/preference", data={"preference": "disliked"})
    assert response.status_code == 200
    assert "<html" not in response.text.lower()
    assert f'id="recipe-row-{created.id}"' in response.text

    assert store.get(created.id).preference.value == "disliked"


def test_static_htmx_is_served(store):
    ui = _make_client(store)
    response = ui.get("/static/vendor/htmx.min.js")
    assert response.status_code == 200
