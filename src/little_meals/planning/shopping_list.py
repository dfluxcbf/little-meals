from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from little_meals.models import MealPlan
from little_meals.store.recipe_store import RecipeNotFound, RecipeStore


@dataclass
class MergedItem:
    """One shopping-list line, before it's persisted - see
    store/shopping_list_store.py's ShoppingListItem for the stored shape."""

    name: str
    quantity: Optional[float]
    unit: Optional[str]


def build_shopping_list_items(plan: MealPlan, recipe_store: RecipeStore) -> list[MergedItem]:
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
            unit_key = (ingredient.unit or "").strip().lower() or None
            key = (ingredient.name.strip().lower(), unit_key)
            scaled_quantity = round(ingredient.quantity * scale, 2) if ingredient.quantity is not None else None

            existing = merged.get(key)
            if existing is None:
                merged[key] = MergedItem(name=ingredient.name.strip(), quantity=scaled_quantity, unit=ingredient.unit)
                order.append(key)
            elif scaled_quantity is not None and existing.quantity is not None:
                merged[key] = MergedItem(
                    name=existing.name, quantity=round(existing.quantity + scaled_quantity, 2), unit=existing.unit
                )
            # else: one side has no quantity to add to - keep the existing line as-is.

    return [merged[key] for key in order]
