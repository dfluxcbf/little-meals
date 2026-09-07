from __future__ import annotations

from pathlib import Path

import pytest

from little_meals.models import Difficulty, Recipe
from little_meals.store.recipe_store import RecipeNotFound, RecipeStore


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


@pytest.mark.requirement("REQ-000000058")
def test_legacy_combined_quantity_unit_is_split_on_read(store: RecipeStore, tmp_recipes_dir: Path):
    tmp_recipes_dir.mkdir(parents=True, exist_ok=True)
    (tmp_recipes_dir / "legacy.md").write_text(
        """---
name: Legacy Recipe
cook_time_minutes: 10
classification: other
nutrition: {}
servings: 2
ingredients:
- name: garlic clove
  unit: 2 piece
- name: salt
  unit: a pinch
created_at: '2026-01-01T00:00:00+00:00'
updated_at: '2026-01-01T00:00:00+00:00'
---
1. Cook it.
""",
        encoding="utf-8",
    )

    recipe = store.get("legacy")

    assert recipe.ingredients[0].name == "garlic clove"
    assert recipe.ingredients[0].quantity == 2.0
    assert recipe.ingredients[0].unit == "piece"
    # No leading number to split out - left untouched.
    assert recipe.ingredients[1].quantity is None
    assert recipe.ingredients[1].unit == "a pinch"


@pytest.mark.requirement("REQ-000000058")
def test_already_split_quantity_unit_is_left_unchanged(store: RecipeStore, sample_recipe: Recipe):
    created = store.create(sample_recipe)
    reread = store.get(created.id)
    assert reread.ingredients == sample_recipe.ingredients
