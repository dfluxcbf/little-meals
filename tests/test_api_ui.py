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


@pytest.mark.requirement("REQ-000000016")
def test_recipe_detail_renders_ingredients_then_steps_in_order(store, sample_recipe):
    # Ingredients are shown first, open by default behind the fridge-door
    # toggle, with steps below them - see docs/ui_design.md's recipe detail
    # screen.
    created = store.create(sample_recipe)
    ui = _make_client(store)

    response = ui.get(f"/recipes/{created.id}")
    assert response.status_code == 200
    text = response.text

    # Search from the previous match onward, not from the start of the page,
    # since an ingredient name (e.g. "garlic") can also appear inside the
    # recipe title higher up the page.
    last_index = -1
    for ingredient in created.ingredients:
        index = text.find(ingredient.name, last_index + 1)
        assert index != -1
        assert index > last_index
        last_index = index

    for step in created.steps:
        index = text.find(step, last_index + 1)
        assert index != -1
        assert index > last_index
        last_index = index


@pytest.mark.requirement("REQ-000000016")
def test_recipe_detail_ingredients_are_behind_a_fridge_toggle(store, sample_recipe):
    created = store.create(sample_recipe)
    ui = _make_client(store)

    response = ui.get(f"/recipes/{created.id}")
    assert response.status_code == 200
    assert '<details class="fridge">' in response.text


def test_recipe_detail_unknown_id_returns_404(store):
    ui = _make_client(store)
    response = ui.get("/recipes/does-not-exist")
    assert response.status_code == 404


NEW_RECIPE_FORM_DATA = {
    "name": "Tomato Soup",
    "cook_time_minutes": "20",
    "classification": "vegetarian",
    "servings": "4",
    "calories_per_serving": "180",
    "ingredient_name": ["tomato"],
    "ingredient_quantity": ["4 pieces"],
    "step": ["Simmer the tomatoes.", "Blend until smooth."],
}


@pytest.mark.requirement("REQ-000000045")
def test_new_recipe_form_submit_creates_recipe_and_redirects(store):
    ui = _make_client(store)
    response = ui.post("/recipes/new", data=NEW_RECIPE_FORM_DATA, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"].startswith("/recipes/")

    recipes = store.list()
    assert len(recipes) == 1
    assert recipes[0].name == "Tomato Soup"
    assert recipes[0].ingredients[0].name == "tomato"


@pytest.mark.requirement("REQ-000000045")
def test_new_recipe_form_submit_without_nutrition_creates_recipe(store):
    ui = _make_client(store)
    data = dict(NEW_RECIPE_FORM_DATA)
    del data["calories_per_serving"]
    response = ui.post("/recipes/new", data=data, follow_redirects=False)

    assert response.status_code == 303
    recipes = store.list()
    assert len(recipes) == 1
    assert recipes[0].nutrition.calories_per_serving is None
    assert recipes[0].nutrition.protein_g is None
    assert recipes[0].nutrition.fiber_g is None


@pytest.mark.requirement("REQ-000000045")
def test_new_recipe_form_submit_missing_name_reshows_form_with_error(store):
    ui = _make_client(store)
    data = dict(NEW_RECIPE_FORM_DATA)
    data["name"] = ""
    response = ui.post("/recipes/new", data=data)

    assert response.status_code == 422
    assert "Could not save recipe" in response.text
    assert store.list() == []


@pytest.mark.requirement("REQ-000000045")
def test_edit_recipe_form_prefills_existing_values(store, sample_recipe):
    created = store.create(sample_recipe)
    ui = _make_client(store)

    response = ui.get(f"/recipes/{created.id}/edit")
    assert response.status_code == 200
    assert created.name in response.text


@pytest.mark.requirement("REQ-000000045")
def test_edit_recipe_form_submit_updates_recipe_and_redirects(store, sample_recipe):
    created = store.create(sample_recipe)
    ui = _make_client(store)

    data = dict(NEW_RECIPE_FORM_DATA)
    data["name"] = "Updated Soup"
    response = ui.post(f"/recipes/{created.id}/edit", data=data, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == f"/recipes/{created.id}"

    updated = store.get(created.id)
    assert updated.name == "Updated Soup"
    assert updated.created_at == created.created_at


@pytest.mark.requirement("REQ-000000045")
def test_duplicate_recipe_creates_copy_and_redirects_to_its_edit_page(store, sample_recipe):
    created = store.create(sample_recipe)
    ui = _make_client(store)

    response = ui.post(f"/recipes/{created.id}/duplicate", follow_redirects=False)

    assert response.status_code == 303
    location = response.headers["location"]
    assert location.startswith("/recipes/")
    assert location.endswith("/edit")

    recipes = {recipe.id: recipe for recipe in store.list()}
    assert len(recipes) == 2
    duplicate_id = location.removeprefix("/recipes/").removesuffix("/edit")
    duplicate = recipes[duplicate_id]
    assert duplicate.id != created.id
    assert duplicate.name == f"{created.name} (copy)"
    assert duplicate.ingredients == created.ingredients
    assert duplicate.steps == created.steps


@pytest.mark.requirement("REQ-000000045")
def test_duplicate_recipe_unknown_id_redirects_to_library(store):
    ui = _make_client(store)
    response = ui.post("/recipes/does-not-exist/duplicate", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/recipes"


@pytest.mark.requirement("REQ-000000045")
def test_edit_recipe_form_unknown_id_returns_404(store):
    ui = _make_client(store)
    response = ui.get("/recipes/does-not-exist/edit")
    assert response.status_code == 404


def test_static_htmx_is_served(store):
    ui = _make_client(store)
    response = ui.get("/static/vendor/htmx.min.js")
    assert response.status_code == 200


@pytest.mark.requirement("REQ-000000013")
def test_static_fonts_are_served_locally_not_from_a_cdn(store):
    # docs/ui_design.md: fonts are vendored, no Google Fonts <link> in the
    # real app - see static/vendor/README.md.
    ui = _make_client(store)

    css = ui.get("/static/fonts.css")
    assert css.status_code == 200
    assert "fonts.googleapis.com" not in css.text
    assert "fonts.gstatic.com" not in css.text

    assert ui.get("/static/vendor/fonts/fraunces-variable-latin.woff2").status_code == 200
    assert ui.get("/static/vendor/fonts/inter-variable-latin.woff2").status_code == 200


@pytest.mark.requirement("REQ-000000015")
def test_recipes_list_card_has_stable_id_for_htmx_swap(store, sample_recipe):
    created = store.create(sample_recipe)
    ui = _make_client(store)

    response = ui.get("/recipes")
    assert response.status_code == 200
    assert f'id="recipe-row-{created.id}"' in response.text


@pytest.mark.requirement("REQ-000000014")
def test_recipes_list_highlights_cookbook_tab(store):
    ui = _make_client(store)
    response = ui.get("/recipes")
    assert 'class="tab tab-active"' in response.text


@pytest.mark.requirement("REQ-000000014")
def test_settings_highlights_settings_tab(client: TestClient):
    response = client.get("/settings")
    assert 'class="tab tab-active"' in response.text
