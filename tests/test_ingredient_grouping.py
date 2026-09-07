from __future__ import annotations

import pytest

from little_meals.planning.ingredient_grouping import category_for, group_ingredient_names_by_category
from little_meals.store.ingredient_catalog_store import IngredientFlags

pytestmark = pytest.mark.requirement("REQ-000000057")


def test_category_for_regular_by_default():
    assert category_for(IngredientFlags()) == "regular"


def test_category_for_pantry():
    assert category_for(IngredientFlags(pantry=True)) == "pantry"


def test_category_for_never_buy():
    assert category_for(IngredientFlags(never_buy=True)) == "never_buy"


def test_category_for_never_buy_wins_over_pantry():
    assert category_for(IngredientFlags(pantry=True, never_buy=True)) == "never_buy"


def test_group_always_returns_three_groups_in_order():
    groups = group_ingredient_names_by_category(["salt"], {"salt": IngredientFlags(pantry=True)})
    assert [key for key, _, _ in groups] == ["regular", "pantry", "never_buy"]
    assert [label for _, label, _ in groups] == ["Regular Ingredients", "Pantry Ingredients", "Never Buy"]


def test_group_includes_empty_categories():
    groups = group_ingredient_names_by_category(["carrot"], {})
    by_key = {key: names for key, _, names in groups}
    assert by_key["regular"] == ["carrot"]
    assert by_key["pantry"] == []
    assert by_key["never_buy"] == []


def test_group_sorts_alphabetically_case_insensitive():
    groups = group_ingredient_names_by_category(["Zucchini", "apple", "Banana"], {})
    by_key = {key: names for key, _, names in groups}
    assert by_key["regular"] == ["apple", "Banana", "Zucchini"]


def test_group_places_each_name_by_its_catalog_flags():
    catalog = {"salt": IngredientFlags(pantry=True), "water": IngredientFlags(never_buy=True)}
    groups = group_ingredient_names_by_category(["salt", "water", "carrot"], catalog)
    by_key = {key: names for key, _, names in groups}
    assert by_key["regular"] == ["carrot"]
    assert by_key["pantry"] == ["salt"]
    assert by_key["never_buy"] == ["water"]
