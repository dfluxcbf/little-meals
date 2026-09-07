from __future__ import annotations

from pathlib import Path

import pytest

from little_meals.store.ingredient_catalog_store import IngredientCatalogStore, IngredientFlags, flags_for

pytestmark = pytest.mark.requirement("REQ-000000057")


def test_get_all_is_empty_by_default(tmp_path: Path):
    store = IngredientCatalogStore(tmp_path / "catalog.db")
    assert store.get_all() == {}


def test_set_flags_upserts_and_normalizes_name(tmp_path: Path):
    store = IngredientCatalogStore(tmp_path / "catalog.db")
    store.set_flags("  Salt ", pantry=True, never_buy=False)

    catalog = store.get_all()
    assert catalog == {"salt": IngredientFlags(pantry=True, never_buy=False)}


def test_set_flags_overwrites_existing_row(tmp_path: Path):
    store = IngredientCatalogStore(tmp_path / "catalog.db")
    store.set_flags("water", pantry=False, never_buy=False)
    store.set_flags("water", pantry=False, never_buy=True)

    assert store.get_all()["water"] == IngredientFlags(pantry=False, never_buy=True)


def test_add_creates_a_default_row_without_clobbering_existing_flags(tmp_path: Path):
    store = IngredientCatalogStore(tmp_path / "catalog.db")
    store.set_flags("water", pantry=False, never_buy=True)

    store.add("water")
    store.add("pepper")

    catalog = store.get_all()
    assert catalog["water"] == IngredientFlags(pantry=False, never_buy=True)
    assert catalog["pepper"] == IngredientFlags()


def test_flags_for_defaults_to_no_flags_for_unknown_name():
    assert flags_for({}, "mystery ingredient") == IngredientFlags()


def test_flags_for_normalizes_lookup_name():
    catalog = {"salt": IngredientFlags(pantry=True)}
    assert flags_for(catalog, "  Salt  ") == IngredientFlags(pantry=True)
