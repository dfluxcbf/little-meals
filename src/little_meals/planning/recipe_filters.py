from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from little_meals.models import Classification, Difficulty, Recipe
from little_meals.planning.glob_match import matches_glob


class GlobScope(str, Enum):
    NAME = "name"
    INGREDIENTS = "ingredients"
    STEPS = "steps"
    ALL = "all"


@dataclass(frozen=True)
class RecipeFilter:
    """Cookbook filter criteria. A field left at its default (`None` for a
    min/max bound, empty for a tag set) imposes no constraint - an
    all-default `RecipeFilter()` passes every recipe through unchanged."""

    min_calories: Optional[int] = None
    max_calories: Optional[int] = None
    min_protein: Optional[float] = None
    max_protein: Optional[float] = None
    min_fiber: Optional[float] = None
    max_fiber: Optional[float] = None
    min_cook_time: Optional[int] = None
    max_cook_time: Optional[int] = None
    classifications: frozenset[Classification] = field(default_factory=frozenset)
    difficulties: frozenset[Difficulty] = field(default_factory=frozenset)
    glob_pattern: Optional[str] = None
    glob_scope: GlobScope = GlobScope.ALL


class SortField(str, Enum):
    NAME = "name"
    CALORIES = "calories"
    PROTEIN = "protein"
    FIBER = "fiber"
    COOK_TIME = "cook_time"


class SortDirection(str, Enum):
    ASC = "asc"
    DESC = "desc"


def _in_bounds(value: Optional[float], minimum: Optional[float], maximum: Optional[float]) -> bool:
    if minimum is None and maximum is None:
        return True
    # A bound is set but the recipe's value is unknown - can't confirm it
    # satisfies a constraint that's actually active, so it's excluded.
    if value is None:
        return False
    if minimum is not None and value < minimum:
        return False
    if maximum is not None and value > maximum:
        return False
    return True


def filter_recipes(recipes: list[Recipe], criteria: RecipeFilter) -> list[Recipe]:
    """Pure function over an in-memory recipe list - no I/O, mirrors
    `planning/selection.py`'s style."""
    return [r for r in recipes if _matches(r, criteria)]


def _matches(recipe: Recipe, criteria: RecipeFilter) -> bool:
    if not _in_bounds(recipe.nutrition.calories_per_serving, criteria.min_calories, criteria.max_calories):
        return False
    if not _in_bounds(recipe.nutrition.protein_g, criteria.min_protein, criteria.max_protein):
        return False
    if not _in_bounds(recipe.nutrition.fiber_g, criteria.min_fiber, criteria.max_fiber):
        return False
    if not _in_bounds(recipe.cook_time_minutes, criteria.min_cook_time, criteria.max_cook_time):
        return False
    if criteria.classifications and recipe.classification not in criteria.classifications:
        return False
    if criteria.difficulties and recipe.difficulty not in criteria.difficulties:
        return False
    if not _matches_glob_scope(recipe, criteria.glob_pattern, criteria.glob_scope):
        return False
    return True


def _matches_glob_scope(recipe: Recipe, pattern: Optional[str], scope: GlobScope) -> bool:
    if pattern is None or not pattern.strip():
        return True
    if scope in (GlobScope.NAME, GlobScope.ALL) and matches_glob(recipe.name, pattern):
        return True
    if scope in (GlobScope.INGREDIENTS, GlobScope.ALL) and any(
        matches_glob(ingredient.name, pattern) for ingredient in recipe.ingredients
    ):
        return True
    if scope in (GlobScope.STEPS, GlobScope.ALL) and any(matches_glob(step, pattern) for step in recipe.steps):
        return True
    return False


_SORT_KEY_FNS = {
    SortField.NAME: lambda r: r.name.lower(),
    SortField.CALORIES: lambda r: r.nutrition.calories_per_serving,
    SortField.PROTEIN: lambda r: r.nutrition.protein_g,
    SortField.FIBER: lambda r: r.nutrition.fiber_g,
    SortField.COOK_TIME: lambda r: r.cook_time_minutes,
}


def sort_recipes(recipes: list[Recipe], field_: SortField, direction: SortDirection) -> list[Recipe]:
    """Pure function; `None` values (unknown nutrition fields) always sort
    last, regardless of direction, so unknowns don't jump to the top on a
    descending sort. Known/missing are split and sorted separately rather
    than folded into one comparison key, since `None` can't be compared to
    a number or string in Python."""
    key_fn = _SORT_KEY_FNS[field_]
    known = [r for r in recipes if key_fn(r) is not None]
    missing = [r for r in recipes if key_fn(r) is None]
    known.sort(key=key_fn, reverse=(direction == SortDirection.DESC))
    return known + missing
