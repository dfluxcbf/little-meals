from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from little_meals.api.app import create_app
from little_meals.config import Settings
from little_meals.models import Classification, Difficulty, Nutrition
from little_meals.store.recipe_store import RecipeStore


def _make_client(store: RecipeStore) -> TestClient:
    settings = Settings(data_dir=store._dir.parent)
    app = create_app(settings=settings, store=store)
    return TestClient(app)


def test_manifest_defaults_to_the_brand_orange_theme_color(store):
    ui = _make_client(store)

    response = ui.get("/manifest.webmanifest")

    assert response.status_code == 200
    assert response.json()["theme_color"] == "#c55123"


def test_manifest_theme_color_follows_the_accent_cookie(store):
    ui = _make_client(store)
    ui.cookies.set("lm_accent", "teal")

    response = ui.get("/manifest.webmanifest")

    assert response.json()["theme_color"] == "#2c7e8b"


def test_manifest_ignores_an_unrecognized_accent_cookie(store):
    ui = _make_client(store)
    ui.cookies.set("lm_accent", "not-a-real-color")

    response = ui.get("/manifest.webmanifest")

    assert response.json()["theme_color"] == "#c55123"


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


@pytest.mark.requirement("REQ-000000051")
def test_new_recipe_form_difficulty_pills_are_positioned_above_classification_below_servings(store):
    ui = _make_client(store)
    response = ui.get("/recipes/new")
    assert response.status_code == 200
    text = response.text

    servings_index = text.index('id="servings"')
    difficulty_index = text.index('id="difficulty-group"')
    classification_index = text.index("<label>Classification</label>")
    assert servings_index < difficulty_index < classification_index


@pytest.mark.requirement("REQ-000000051")
def test_new_recipe_form_submit_with_difficulty_creates_recipe_with_that_difficulty(store):
    ui = _make_client(store)
    data = dict(NEW_RECIPE_FORM_DATA, difficulty="hard")

    response = ui.post("/recipes/new", data=data, follow_redirects=False)
    assert response.status_code == 303

    recipes = store.list()
    assert len(recipes) == 1
    assert recipes[0].difficulty.value == "hard"


@pytest.mark.requirement("REQ-000000051")
def test_new_recipe_form_submit_without_difficulty_defaults_to_undefined(store):
    ui = _make_client(store)

    response = ui.post("/recipes/new", data=NEW_RECIPE_FORM_DATA, follow_redirects=False)
    assert response.status_code == 303

    recipes = store.list()
    assert len(recipes) == 1
    assert recipes[0].difficulty.value == "undefined"


@pytest.mark.requirement("REQ-000000052")
def test_recipes_list_shows_difficulty_badge_below_classification_badge(store, sample_recipe):
    created = store.create(sample_recipe.model_copy(update={"difficulty": Difficulty.MEDIUM}))
    ui = _make_client(store)

    response = ui.get("/recipes")
    assert response.status_code == 200
    text = response.text

    classification_index = text.index(f"badge-{created.classification.value}")
    difficulty_index = text.index("badge-medium")
    assert classification_index < difficulty_index


@pytest.mark.requirement("REQ-000000052")
def test_recipe_detail_shows_difficulty_badge_after_classification_badge(store, sample_recipe):
    created = store.create(sample_recipe.model_copy(update={"difficulty": Difficulty.EASY}))
    ui = _make_client(store)

    response = ui.get(f"/recipes/{created.id}")
    assert response.status_code == 200
    text = response.text

    classification_index = text.index(f"badge-{created.classification.value}")
    difficulty_index = text.index("badge-easy")
    assert classification_index < difficulty_index


@pytest.mark.requirement("REQ-000000053")
@pytest.mark.parametrize("classification", ["vegan", "ketogenic", "paleo"])
def test_new_recipe_form_offers_additional_food_type_classifications(store, classification: str):
    ui = _make_client(store)
    response = ui.get("/recipes/new")
    assert response.status_code == 200
    assert f'id="classification-{classification}"' in response.text


@pytest.mark.requirement("REQ-000000053")
@pytest.mark.parametrize("classification", ["vegan", "ketogenic", "paleo"])
def test_new_recipe_form_submit_accepts_additional_food_type_classifications(store, classification: str):
    ui = _make_client(store)
    data = dict(NEW_RECIPE_FORM_DATA, classification=classification)

    response = ui.post("/recipes/new", data=data, follow_redirects=False)
    assert response.status_code == 303

    recipes = store.list()
    assert len(recipes) == 1
    assert recipes[0].classification.value == classification


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


@pytest.mark.requirement("REQ-000000055")
def test_recipes_list_min_calories_filter_narrows_results(store, sample_recipe):
    store.create(sample_recipe.model_copy(update={"name": "Low Cal", "nutrition": Nutrition(calories_per_serving=100)}))
    store.create(sample_recipe.model_copy(update={"name": "High Cal", "nutrition": Nutrition(calories_per_serving=800)}))
    ui = _make_client(store)

    response = ui.get("/recipes", params={"min_calories": 300})

    assert "High Cal" in response.text
    assert "Low Cal" not in response.text


@pytest.mark.requirement("REQ-000000055")
def test_recipes_list_classification_filter_narrows_results(store, sample_recipe):
    store.create(sample_recipe.model_copy(update={"name": "Veg", "classification": Classification.VEGETARIAN}))
    store.create(sample_recipe.model_copy(update={"name": "Meaty Dish", "classification": Classification.OTHER}))
    ui = _make_client(store)

    response = ui.get("/recipes", params={"classification": "vegetarian"})

    assert "Veg" in response.text
    assert "Meaty Dish" not in response.text


@pytest.mark.requirement("REQ-000000055")
def test_recipes_list_difficulty_filter_narrows_results(store, sample_recipe):
    store.create(sample_recipe.model_copy(update={"name": "Easy One", "difficulty": Difficulty.EASY}))
    store.create(sample_recipe.model_copy(update={"name": "Hard One", "difficulty": Difficulty.HARD}))
    ui = _make_client(store)

    response = ui.get("/recipes", params={"difficulty": "easy"})

    assert "Easy One" in response.text
    assert "Hard One" not in response.text


@pytest.mark.requirement("REQ-000000055")
def test_recipes_list_sort_by_cook_time_descending(store, sample_recipe):
    store.create(sample_recipe.model_copy(update={"name": "Fast", "cook_time_minutes": 10}))
    store.create(sample_recipe.model_copy(update={"name": "Slow", "cook_time_minutes": 90}))
    ui = _make_client(store)

    response = ui.get("/recipes", params={"sort_by": "cook_time", "sort_dir": "desc"})

    assert response.text.index("Slow") < response.text.index("Fast")


@pytest.mark.requirement("REQ-000000055")
def test_recipes_list_filter_bar_shows_active_filter_count(store, sample_recipe):
    store.create(sample_recipe)
    ui = _make_client(store)

    response = ui.get("/recipes", params={"min_calories": 100, "classification": "other"})

    assert "Filters (2)" in response.text


@pytest.mark.requirement("REQ-000000055")
def test_recipes_list_invalid_classification_value_is_ignored_not_a_400(store, sample_recipe):
    store.create(sample_recipe)
    ui = _make_client(store)

    response = ui.get("/recipes", params={"classification": "not-a-real-type"})

    assert response.status_code == 200
    assert sample_recipe.name in response.text


@pytest.mark.requirement("REQ-000000056")
def test_add_to_plan_creates_a_draft_plan_when_none_exists(store, sample_recipe):
    created = store.create(sample_recipe)
    ui = _make_client(store)

    response = ui.post(f"/recipes/{created.id}/add-to-plan")

    assert response.status_code == 200
    assert "Added to plan" in response.text
    plan = ui.get("/api/plan/current").json()
    assert [m["recipe_id"] for m in plan["meals"]] == [created.id]
    assert plan["finalized"] is False


@pytest.mark.requirement("REQ-000000056")
def test_add_to_plan_appends_to_an_existing_draft_plan(store, sample_recipe):
    first = store.create(sample_recipe.model_copy(update={"name": "First"}))
    second = store.create(sample_recipe.model_copy(update={"name": "Second"}))
    ui = _make_client(store)
    ui.post(f"/recipes/{first.id}/add-to-plan")

    ui.post(f"/recipes/{second.id}/add-to-plan")

    plan = ui.get("/api/plan/current").json()
    assert {m["recipe_id"] for m in plan["meals"]} == {first.id, second.id}


@pytest.mark.requirement("REQ-000000056")
def test_add_to_plan_is_a_no_op_when_recipe_already_in_plan(store, sample_recipe):
    created = store.create(sample_recipe)
    ui = _make_client(store)
    ui.post(f"/recipes/{created.id}/add-to-plan")

    response = ui.post(f"/recipes/{created.id}/add-to-plan")

    assert response.status_code == 200
    assert "Added to plan" in response.text
    plan = ui.get("/api/plan/current").json()
    assert [m["recipe_id"] for m in plan["meals"]] == [created.id]


@pytest.mark.requirement("REQ-000000056")
def test_add_to_plan_is_blocked_when_plan_is_finalized(store, sample_recipe):
    first = store.create(sample_recipe.model_copy(update={"name": "First"}))
    second = store.create(sample_recipe.model_copy(update={"name": "Second"}))
    ui = _make_client(store)
    ui.post(f"/recipes/{first.id}/add-to-plan")
    plan_id = ui.get("/api/plan/current").json()["id"]
    ui.post(f"/api/plan/{plan_id}/finalize")

    response = ui.post(f"/recipes/{second.id}/add-to-plan")

    assert response.status_code == 409


@pytest.mark.requirement("REQ-000000056")
def test_recipes_list_shows_added_to_plan_badge_for_recipe_in_current_plan(store, sample_recipe):
    in_plan = store.create(sample_recipe.model_copy(update={"name": "In Plan"}))
    not_in_plan = store.create(sample_recipe.model_copy(update={"name": "Not In Plan"}))
    ui = _make_client(store)
    ui.post(f"/recipes/{in_plan.id}/add-to-plan")

    response = ui.get("/recipes")

    body = response.text
    in_plan_card = body[body.index(f'id="recipe-row-{in_plan.id}"') : body.index(f'id="recipe-row-{not_in_plan.id}"')]
    not_in_plan_card = body[body.index(f'id="recipe-row-{not_in_plan.id}"') :]
    assert "Added to plan" in in_plan_card
    assert "Added to plan" not in not_in_plan_card


@pytest.mark.requirement("REQ-000000056")
def test_remove_from_plan_removes_the_meal(store, sample_recipe):
    created = store.create(sample_recipe)
    ui = _make_client(store)
    ui.post(f"/recipes/{created.id}/add-to-plan")

    response = ui.post(f"/recipes/{created.id}/remove-from-plan")

    assert response.status_code == 200
    assert "Added to plan" not in response.text
    plan = ui.get("/api/plan/current").json()
    assert plan["meals"] == []


@pytest.mark.requirement("REQ-000000056")
def test_remove_from_plan_is_a_no_op_when_recipe_not_in_plan(store, sample_recipe):
    created = store.create(sample_recipe)
    ui = _make_client(store)

    response = ui.post(f"/recipes/{created.id}/remove-from-plan")

    assert response.status_code == 200
    assert "Added to plan" not in response.text


@pytest.mark.requirement("REQ-000000056")
def test_remove_from_plan_is_blocked_when_plan_is_finalized(store, sample_recipe):
    created = store.create(sample_recipe)
    ui = _make_client(store)
    ui.post(f"/recipes/{created.id}/add-to-plan")
    plan_id = ui.get("/api/plan/current").json()["id"]
    ui.post(f"/api/plan/{plan_id}/finalize")

    response = ui.post(f"/recipes/{created.id}/remove-from-plan")

    assert response.status_code == 409
    assert "finalized" in response.text.lower()
    plan = ui.get("/api/plan/current").json()
    assert [m["recipe_id"] for m in plan["meals"]] == [created.id]
