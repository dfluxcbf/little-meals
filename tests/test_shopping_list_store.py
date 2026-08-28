from __future__ import annotations

import pytest

from little_meals.planning.shopping_list import MergedItem
from little_meals.store.shopping_list_store import ShoppingListItemNotFound, ShoppingListNotFound, ShoppingListStore


def test_get_for_plan_returns_none_when_none_exists(shopping_list_store: ShoppingListStore):
    assert shopping_list_store.get_for_plan("plan-1") is None


def test_create_stores_items_in_order(shopping_list_store: ShoppingListStore):
    shopping_list = shopping_list_store.create(
        "plan-1", [MergedItem("Carrot", 2.0, "pieces"), MergedItem("Salt", None, None)]
    )

    assert shopping_list.plan_id == "plan-1"
    assert shopping_list.actual_cost is None
    assert [item.id for item in shopping_list.items] == ["i1", "i2"]
    assert shopping_list.items[0].name == "Carrot"
    assert shopping_list.items[0].checked is False


def test_create_raises_when_plan_already_has_a_list(shopping_list_store: ShoppingListStore):
    shopping_list_store.create("plan-1", [])
    with pytest.raises(ValueError):
        shopping_list_store.create("plan-1", [])


def test_get_for_plan_finds_the_created_list(shopping_list_store: ShoppingListStore):
    created = shopping_list_store.create("plan-1", [MergedItem("Carrot", 2.0, "pieces")])
    found = shopping_list_store.get_for_plan("plan-1")
    assert found is not None
    assert found.id == created.id


def test_get_unknown_list_raises(shopping_list_store: ShoppingListStore):
    with pytest.raises(ShoppingListNotFound):
        shopping_list_store.get("does-not-exist")


def test_set_item_checked_updates_only_the_targeted_item(shopping_list_store: ShoppingListStore):
    shopping_list = shopping_list_store.create("plan-1", [MergedItem("A", 1.0, "g"), MergedItem("B", 2.0, "g")])

    updated = shopping_list_store.set_item_checked(shopping_list.id, "i1", True)

    assert updated.items[0].checked is True
    assert updated.items[1].checked is False


def test_set_item_checked_unknown_item_raises(shopping_list_store: ShoppingListStore):
    shopping_list = shopping_list_store.create("plan-1", [MergedItem("A", 1.0, "g")])
    with pytest.raises(ShoppingListItemNotFound):
        shopping_list_store.set_item_checked(shopping_list.id, "does-not-exist", True)


def test_set_item_checked_unknown_list_raises(shopping_list_store: ShoppingListStore):
    with pytest.raises(ShoppingListNotFound):
        shopping_list_store.set_item_checked("does-not-exist", "i1", True)


def test_set_actual_cost_persists(shopping_list_store: ShoppingListStore):
    shopping_list = shopping_list_store.create("plan-1", [])
    updated = shopping_list_store.set_actual_cost(shopping_list.id, 42.5)
    assert updated.actual_cost == 42.5
    assert shopping_list_store.get(shopping_list.id).actual_cost == 42.5


def test_set_actual_cost_unknown_list_raises(shopping_list_store: ShoppingListStore):
    with pytest.raises(ShoppingListNotFound):
        shopping_list_store.set_actual_cost("does-not-exist", 10.0)
