from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from little_meals.models import MealPlan, ShoppingListItem
from little_meals.store.ingredient_catalog_store import IngredientFlags, flags_for
from little_meals.store.recipe_store import RecipeNotFound, RecipeStore


@dataclass
class MergedItem:
    """One shopping-list line, before it's persisted - see
    store/shopping_list_store.py's ShoppingListItem for the stored shape."""

    name: str
    quantity: Optional[float]
    unit: Optional[str]
    pantry: bool = False


def build_shopping_list_items(
    plan: MealPlan, recipe_store: RecipeStore, catalog: dict[str, IngredientFlags]
) -> list[MergedItem]:
    """Merge ingredients across every meal in a plan into one flat,
    deduplicated list (see design.md's updated Shopping list concept - no
    grocery-aisle categorization), scaling each recipe's ingredient
    quantities to that meal's servings count (which may have been
    overridden away from the recipe's own default - see PlanMeal).

    Two ingredients merge into one line only when their name AND unit both
    match (case-insensitively) - different units for the same ingredient
    name (e.g. a recipe calling for "2 cups flour" and another for "500 g
    flour") are listed as separate lines rather than silently added
    together, since that would require unit conversion this doesn't attempt.
    An ingredient with no quantity (e.g. "a pinch of salt") is deduplicated
    by name/unit alone and just listed once, without quantity math.

    An ingredient flagged "never buy" in the catalog (see
    store/ingredient_catalog_store.py - e.g. water) is dropped entirely,
    never reaching the list; one flagged "pantry" is still merged/listed as
    normal, just tagged so the shopping list UI can group it separately.

    A meal whose recipe has since been deleted is skipped, same as the
    plan review page already does.
    """
    merged: dict[tuple[str, Optional[str]], MergedItem] = {}
    order: list[tuple[str, Optional[str]]] = []

    for meal in plan.meals:
        try:
            recipe = recipe_store.get(meal.recipe_id)
        except RecipeNotFound:
            continue

        scale = meal.servings / recipe.servings if recipe.servings else 1.0

        for ingredient in recipe.ingredients:
            flags = flags_for(catalog, ingredient.name)
            if flags.never_buy:
                continue

            unit_key = (ingredient.unit or "").strip().lower() or None
            key = (ingredient.name.strip().lower(), unit_key)
            scaled_quantity = round(ingredient.quantity * scale, 2) if ingredient.quantity is not None else None

            existing = merged.get(key)
            if existing is None:
                merged[key] = MergedItem(
                    name=ingredient.name.strip(), quantity=scaled_quantity, unit=ingredient.unit, pantry=flags.pantry
                )
                order.append(key)
            elif scaled_quantity is not None and existing.quantity is not None:
                merged[key] = MergedItem(
                    name=existing.name,
                    quantity=round(existing.quantity + scaled_quantity, 2),
                    unit=existing.unit,
                    pantry=existing.pantry,
                )
            # else: one side has no quantity to add to - keep the existing line as-is.

    return [merged[key] for key in order]


_SHOPPING_SECTIONS: tuple[tuple[str, str], ...] = (
    ("to_buy", "To buy"),
    ("pantry", "Pantry"),
    ("checked", "Checked"),
    ("checked_pantry", "Checked (pantry)"),
)


def group_shopping_list_items(items: list[ShoppingListItem]) -> list[tuple[str, list[ShoppingListItem]]]:
    """Group a shopping list's items into display sections - unchecked
    (non-pantry), unchecked pantry, checked (non-pantry), checked pantry, in
    that order - alphabetically sorted within each section. Empty sections
    are omitted rather than shown blank."""
    buckets: dict[str, list[ShoppingListItem]] = {key: [] for key, _ in _SHOPPING_SECTIONS}
    for item in items:
        if item.checked and not item.pantry:
            key = "checked"
        elif item.checked and item.pantry:
            key = "checked_pantry"
        elif not item.checked and item.pantry:
            key = "pantry"
        else:
            key = "to_buy"
        buckets[key].append(item)

    sections = []
    for key, label in _SHOPPING_SECTIONS:
        bucket = sorted(buckets[key], key=lambda i: i.name.strip().lower())
        if bucket:
            sections.append((label, bucket))
    return sections
