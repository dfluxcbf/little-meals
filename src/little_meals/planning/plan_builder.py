from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from little_meals.llm.extraction import RecipeExtractionService
from little_meals.models import HouseholdPreferences, Preference, Recipe
from little_meals.planning.selection import select_recipes_for_plan
from little_meals.store.household_store import HouseholdPreferencesStore
from little_meals.store.plan_store import MealSpec
from little_meals.store.recipe_store import RecipeStore


@dataclass
class GeneratedMeal:
    """One meal ready to be written into a plan - see store/plan_store.py's
    MealSpec for the persisted shape this maps onto."""

    recipe: Recipe
    servings: int


def build_weekly_plan(recipes: list[Recipe], preferences: HouseholdPreferences, rng: Optional[random.Random] = None) -> list[GeneratedMeal]:
    """Fills a plan from the existing recipe library only (Milestone 3's
    selection engine), up to `recipes_per_week` - a library with fewer liked
    recipes than that yields a shorter plan rather than inventing anything."""
    rng = rng or random.Random()
    library_picks = select_recipes_for_plan(recipes, preferences.recipes_per_week, rng=rng)
    return [GeneratedMeal(recipe=r, servings=r.servings) for r in library_picks]


def build_meal_specs(
    recipe_store: RecipeStore,
    household_store: HouseholdPreferencesStore,
    extractor: RecipeExtractionService,
    rng: Optional[random.Random] = None,
) -> list[MealSpec]:
    """The shared "build a fresh plan's worth of meals" call every
    generation path uses - initial generation (`POST /plan/generate`), a
    whole-plan reroll, and the scheduled weekly generation - so there's
    exactly one place that reads preferences, lists recipes, and runs
    build_weekly_plan."""
    preferences = household_store.get()
    recipes = recipe_store.list(extractor)
    generated = build_weekly_plan(recipes, preferences, rng=rng)
    return [MealSpec(g.recipe.id, g.servings) for g in generated]


def generate_single_replacement(
    excluded_recipe_ids: set[str],
    recipes: list[Recipe],
    rng: Optional[random.Random] = None,
) -> Optional[GeneratedMeal]:
    """Single-meal reroll: pick a liked library recipe not already used
    elsewhere in the plan. Returns None if the library has nothing left to
    offer (caller leaves the slot as it was)."""
    rng = rng or random.Random()
    liked = [r for r in recipes if r.preference == Preference.LIKED]
    unused = [r for r in liked if r.id not in excluded_recipe_ids]
    if not unused:
        return None
    chosen = rng.choice(unused)
    return GeneratedMeal(recipe=chosen, servings=chosen.servings)


def list_controlled_reroll_candidates(
    excluded_recipe_ids: set[str],
    recipes: list[Recipe],
    limit: int = 10,
    rng: Optional[random.Random] = None,
) -> list[Recipe]:
    """Controlled reroll: up to `limit` liked library recipes not already
    used elsewhere in the plan, for the household to pick from directly."""
    candidates = [r for r in recipes if r.preference == Preference.LIKED and r.id not in excluded_recipe_ids]
    if len(candidates) <= limit:
        return candidates
    rng = rng or random.Random()
    return rng.sample(candidates, k=limit)
