from __future__ import annotations

from little_meals.models import Ingredient
from little_meals.store.ingredient_catalog_store import IngredientFlags, flags_for

_GROUP_LABELS = ("Ingredients", "Pantry items", "Others")


def categorize_ingredients(
    ingredients: list[Ingredient], catalog: dict[str, IngredientFlags]
) -> list[tuple[str, list[tuple[int, Ingredient]]]]:
    """Split a recipe's ingredient list into display groups - regular
    ingredients, pantry items, and "never buy" ones ("Others") - per the
    global ingredient catalog (see store/ingredient_catalog_store.py).
    Preserves each ingredient's original index (needed so cook-along's
    per-ingredient checked state, keyed by index, still addresses the right
    ingredient after grouping) and original within-group order. A group with
    nothing in it is omitted."""
    groups: dict[str, list[tuple[int, Ingredient]]] = {label: [] for label in _GROUP_LABELS}
    for index, ingredient in enumerate(ingredients):
        flags = flags_for(catalog, ingredient.name)
        if flags.never_buy:
            label = "Others"
        elif flags.pantry:
            label = "Pantry items"
        else:
            label = "Ingredients"
        groups[label].append((index, ingredient))

    return [(label, groups[label]) for label in _GROUP_LABELS if groups[label]]


_CATEGORY_LABELS: tuple[tuple[str, str], ...] = (
    ("regular", "Regular Ingredients"),
    ("pantry", "Pantry Ingredients"),
    ("never_buy", "Never Buy"),
)


def category_for(flags: IngredientFlags) -> str:
    """The single category key ("regular"/"pantry"/"never_buy") an ingredient
    belongs to - never_buy wins over pantry, matching categorize_ingredients."""
    if flags.never_buy:
        return "never_buy"
    if flags.pantry:
        return "pantry"
    return "regular"


def group_ingredient_names_by_category(
    names: list[str], catalog: dict[str, IngredientFlags]
) -> list[tuple[str, str, list[str]]]:
    """Split ingredient names into the 3 catalog-management lists - Regular
    Ingredients, Pantry Ingredients, Never Buy - each name in exactly one,
    alphabetically sorted within each. Unlike categorize_ingredients, ALL
    three groups are always returned (even empty) since this is the settings
    page's core structure, not a contextual per-recipe display. Returns
    (category_key, label, names) tuples in fixed order."""
    buckets: dict[str, list[str]] = {key: [] for key, _ in _CATEGORY_LABELS}
    for name in names:
        buckets[category_for(flags_for(catalog, name))].append(name)

    return [(key, label, sorted(buckets[key], key=str.lower)) for key, label in _CATEGORY_LABELS]
