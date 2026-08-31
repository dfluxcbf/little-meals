from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from little_meals.llm.extraction import RecipeExtractionService
from little_meals.llm.ollama_client import OllamaClient
from little_meals.models import Difficulty, Recipe
from little_meals.store.recipe_store import RecipeNotFound, RecipeStore

_NORMALIZED_PAYLOAD = {
    "name": "Rescued Recipe",
    "cook_time_minutes": 25,
    "classification": "vegetarian",
    "nutrition": {"calories_per_serving": 300},
    "servings": 3,
    "ingredients": [{"name": "carrot", "quantity": 2, "unit": "pieces"}],
    "steps": ["Chop the carrots.", "Roast until tender."],
}


def _extractor_with(handler) -> RecipeExtractionService:
    transport = httpx.MockTransport(handler)
    client = OllamaClient("http://ollama.test", "test-model", timeout_s=5.0, client=httpx.Client(transport=transport))
    return RecipeExtractionService(client)


@pytest.mark.requirement("REQ-000000001")
def test_create_then_get_round_trips(store: RecipeStore, sample_recipe: Recipe):
    created = store.create(sample_recipe)
    assert created.id == "lemon-garlic-chicken"

    fetched = store.get(created.id)
    assert fetched.name == sample_recipe.name
    assert fetched.cook_time_minutes == sample_recipe.cook_time_minutes
    assert fetched.classification == sample_recipe.classification
    assert fetched.nutrition == sample_recipe.nutrition
    assert fetched.ingredients == sample_recipe.ingredients
    assert fetched.steps == sample_recipe.steps
    assert fetched.source_text == sample_recipe.source_text


def test_list_is_sorted_by_filename(store: RecipeStore, sample_recipe: Recipe):
    store.create(sample_recipe.model_copy(update={"name": "Zucchini Bread"}))
    store.create(sample_recipe.model_copy(update={"name": "Apple Pie"}))

    names = [recipe.name for recipe in store.list()]
    assert names == ["Apple Pie", "Zucchini Bread"]


def test_create_handles_slug_collisions(store: RecipeStore, sample_recipe: Recipe):
    first = store.create(sample_recipe)
    second = store.create(sample_recipe)
    third = store.create(sample_recipe)

    assert first.id == "lemon-garlic-chicken"
    assert second.id == "lemon-garlic-chicken-2"
    assert third.id == "lemon-garlic-chicken-3"


def test_update_preserves_created_at_and_bumps_updated_at(store: RecipeStore, sample_recipe: Recipe):
    created = store.create(sample_recipe)
    updated = store.update(created.id, created.model_copy(update={"name": "New Name"}))

    assert updated.name == "New Name"
    assert updated.created_at == created.created_at
    assert updated.updated_at >= created.updated_at


def test_delete_removes_the_file(store: RecipeStore, sample_recipe: Recipe):
    created = store.create(sample_recipe)
    store.delete(created.id)
    with pytest.raises(RecipeNotFound):
        store.get(created.id)


def test_get_unknown_id_raises_not_found(store: RecipeStore):
    with pytest.raises(RecipeNotFound):
        store.get("does-not-exist")


def test_delete_unknown_id_raises_not_found(store: RecipeStore):
    with pytest.raises(RecipeNotFound):
        store.delete("does-not-exist")


def test_hand_edited_file_is_picked_up_on_next_read(store: RecipeStore, sample_recipe: Recipe, tmp_recipes_dir: Path):
    created = store.create(sample_recipe)
    path = tmp_recipes_dir / f"{created.id}.md"
    text = path.read_text(encoding="utf-8")
    text = text.replace("Lemon Garlic Chicken", "Lime Garlic Chicken")
    path.write_text(text, encoding="utf-8")

    reread = store.get(created.id)
    assert reread.name == "Lime Garlic Chicken"


@pytest.mark.requirement("REQ-000000050")
def test_create_then_get_round_trips_difficulty(store: RecipeStore, sample_recipe: Recipe):
    recipe = sample_recipe.model_copy(update={"difficulty": Difficulty.HARD})
    created = store.create(recipe)

    fetched = store.get(created.id)
    assert fetched.difficulty == Difficulty.HARD


@pytest.mark.requirement("REQ-000000050")
def test_recipe_defaults_to_undefined_difficulty(sample_recipe: Recipe):
    assert sample_recipe.difficulty == Difficulty.UNDEFINED


@pytest.mark.requirement("REQ-000000050")
def test_recipe_file_written_before_difficulty_existed_reads_as_undefined(
    store: RecipeStore, sample_recipe: Recipe, tmp_recipes_dir: Path
):
    created = store.create(sample_recipe.model_copy(update={"difficulty": Difficulty.EASY}))
    path = tmp_recipes_dir / f"{created.id}.md"
    text = path.read_text(encoding="utf-8")
    text = "\n".join(line for line in text.splitlines() if not line.startswith("difficulty:")) + "\n"
    path.write_text(text, encoding="utf-8")

    reread = store.get(created.id)
    assert reread.difficulty == Difficulty.UNDEFINED


def test_list_skips_corrupt_files_without_failing(store: RecipeStore, sample_recipe: Recipe, tmp_recipes_dir: Path):
    store.create(sample_recipe)
    corrupt_path = tmp_recipes_dir / "corrupt.md"
    corrupt_path.write_text("---\nnot: closed\n", encoding="utf-8")

    recipes = store.list()
    assert len(recipes) == 1
    assert recipes[0].name == sample_recipe.name


def test_write_leaves_no_tmp_file_behind(store: RecipeStore, sample_recipe: Recipe, tmp_recipes_dir: Path):
    store.create(sample_recipe)
    tmp_files = list(tmp_recipes_dir.glob("*.tmp"))
    assert tmp_files == []


@pytest.mark.requirement("REQ-000000040")
def test_list_normalizes_an_unparseable_file_via_extractor(
    store: RecipeStore, sample_recipe: Recipe, tmp_recipes_dir: Path
):
    store.create(sample_recipe)
    foreign_path = tmp_recipes_dir / "pasted-in.md"
    foreign_path.write_text("# Grandma's Carrot Roast\n\n2 carrots, chopped. Roast until tender.\n", encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": json.dumps(_NORMALIZED_PAYLOAD)})

    recipes = store.list(_extractor_with(handler))

    names = {r.name for r in recipes}
    assert names == {sample_recipe.name, "Rescued Recipe"}


@pytest.mark.requirement("REQ-000000040")
def test_normalized_file_is_rewritten_so_later_reads_need_no_extractor(
    store: RecipeStore, tmp_recipes_dir: Path
):
    tmp_recipes_dir.mkdir(parents=True, exist_ok=True)
    foreign_path = tmp_recipes_dir / "pasted-in.md"
    foreign_path.write_text("# Grandma's Carrot Roast\n\n2 carrots, chopped. Roast until tender.\n", encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": json.dumps(_NORMALIZED_PAYLOAD)})

    store.list(_extractor_with(handler))

    # No extractor this time - the file must now parse as canonical frontmatter.
    reread = store.get("pasted-in")
    assert reread.name == "Rescued Recipe"
    assert reread.ingredients[0].name == "carrot"


@pytest.mark.requirement("REQ-000000040")
def test_list_without_extractor_still_skips_corrupt_files(
    store: RecipeStore, sample_recipe: Recipe, tmp_recipes_dir: Path
):
    store.create(sample_recipe)
    corrupt_path = tmp_recipes_dir / "corrupt.md"
    corrupt_path.write_text("---\nnot: closed\n", encoding="utf-8")

    recipes = store.list(None)
    assert len(recipes) == 1
    assert recipes[0].name == sample_recipe.name


@pytest.mark.requirement("REQ-000000040")
def test_list_falls_back_to_skipping_when_normalization_also_fails(
    store: RecipeStore, sample_recipe: Recipe, tmp_recipes_dir: Path
):
    store.create(sample_recipe)
    corrupt_path = tmp_recipes_dir / "corrupt.md"
    corrupt_path.write_text("---\nnot: closed\n", encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": "not valid json"})

    recipes = store.list(_extractor_with(handler))
    assert len(recipes) == 1
    assert recipes[0].name == sample_recipe.name


@pytest.mark.requirement("REQ-000000040")
def test_normalize_skips_an_empty_file_without_calling_the_extractor(
    store: RecipeStore, tmp_recipes_dir: Path
):
    tmp_recipes_dir.mkdir(parents=True, exist_ok=True)
    (tmp_recipes_dir / "empty.md").write_text("   \n", encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("extractor should not be called for an empty file")

    recipes = store.list(_extractor_with(handler))
    assert recipes == []
