from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from little_meals.llm.extraction import RecipeExtractionService
from little_meals.models import HouseholdPreferences, Preference, Recipe
from little_meals.planning.selection import select_recipes_for_plan
from little_meals.planning.suggestion import SearchProvider, generate_combination_suggestion, generate_search_suggestion
from little_meals.store.household_store import HouseholdPreferencesStore
from little_meals.store.plan_store import MealSpec
from little_meals.store.recipe_store import RecipeStore


@dataclass
class GeneratedMeal:
    """One meal ready to be written into a plan - see store/plan_store.py's
    MealSpec for the persisted shape this maps onto."""

    recipe: Recipe
    servings: int
    is_suggestion: bool


def build_weekly_plan(
    recipes: list[Recipe],
    preferences: HouseholdPreferences,
    recipe_store: RecipeStore,
    extractor: RecipeExtractionService,
    search_provider: SearchProvider,
    rng: Optional[random.Random] = None,
) -> list[GeneratedMeal]:
    """M3's library selection, topped up with M4's AI suggestions: fills
    `recipes_per_week - ai_suggestions_per_plan` slots from the existing
    library (never more - the rest is reserved for suggestions), then
    generates up to `ai_suggestions_per_plan` new ones (online search first
    if a provider is configured and returns something, otherwise combining
    two stored recipes). Each accepted suggestion is written into the
    recipe library immediately, liked by default, exactly like any other
    new recipe - see planning/suggestion.py.

    A suggestion source that can't produce anything (too few liked recipes
    to combine, a search provider with nothing configured, an LLM hiccup)
    just contributes nothing to that slot rather than failing the whole
    plan - a shorter plan beats no plan.
    """
    rng = rng or random.Random()
    ai_count = max(0, preferences.ai_suggestions_per_plan)
    library_count = max(0, preferences.recipes_per_week - ai_count)

    library_picks = select_recipes_for_plan(recipes, library_count, rng=rng)
    meals = [GeneratedMeal(recipe=r, servings=r.servings, is_suggestion=False) for r in library_picks]

    liked = [r for r in recipes if r.preference == Preference.LIKED]
    query = _search_query(preferences)
    for _ in range(ai_count):
        generated = _generate_one_suggestion(liked, query, recipe_store, extractor, search_provider, rng)
        if generated is not None:
            meals.append(generated)

    return meals


def build_meal_specs(
    recipe_store: RecipeStore,
    household_store: HouseholdPreferencesStore,
    extractor: RecipeExtractionService,
    search_provider: SearchProvider,
    rng: Optional[random.Random] = None,
) -> list[MealSpec]:
    """The shared "build a fresh plan's worth of meals" call every
    generation path uses - initial generation (`POST /plan/generate`), a
    whole-plan reroll, and Milestone 7's scheduled weekly generation - so
    there's exactly one place that reads preferences, lists recipes, and
    runs build_weekly_plan."""
    preferences = household_store.get()
    recipes = recipe_store.list(extractor)
    generated = build_weekly_plan(recipes, preferences, recipe_store, extractor, search_provider, rng=rng)
    return [MealSpec(g.recipe.id, g.servings, g.is_suggestion) for g in generated]


def generate_single_replacement(
    excluded_recipe_ids: set[str],
    recipes: list[Recipe],
    recipe_store: RecipeStore,
    extractor: RecipeExtractionService,
    search_provider: SearchProvider,
    preferences: HouseholdPreferences,
    rng: Optional[random.Random] = None,
) -> Optional[GeneratedMeal]:
    """Single-meal reroll: prefer a liked library recipe not already used
    elsewhere in the plan; only generate a fresh AI suggestion if the
    library has nothing left to offer. Returns None if neither source can
    produce a replacement (caller leaves the slot as it was)."""
    rng = rng or random.Random()
    liked = [r for r in recipes if r.preference == Preference.LIKED]
    unused = [r for r in liked if r.id not in excluded_recipe_ids]
    if unused:
        chosen = rng.choice(unused)
        return GeneratedMeal(recipe=chosen, servings=chosen.servings, is_suggestion=False)

    return _generate_one_suggestion(liked, _search_query(preferences), recipe_store, extractor, search_provider, rng)


def list_controlled_reroll_candidates(
    excluded_recipe_ids: set[str],
    recipes: list[Recipe],
    limit: int = 10,
    rng: Optional[random.Random] = None,
) -> list[Recipe]:
    """Controlled reroll: up to `limit` liked library recipes not already
    used elsewhere in the plan, for the household to pick from directly.
    Drawn only from the existing library, not fresh LLM generations - see
    ui_design.md and milestones.md's M4 entry for why: generating (and
    mostly discarding) ten LLM extractions per request isn't worth the
    latency/cost for a "give me options" action."""
    candidates = [r for r in recipes if r.preference == Preference.LIKED and r.id not in excluded_recipe_ids]
    if len(candidates) <= limit:
        return candidates
    rng = rng or random.Random()
    return rng.sample(candidates, k=limit)


def _generate_one_suggestion(
    liked: list[Recipe],
    query: str,
    recipe_store: RecipeStore,
    extractor: RecipeExtractionService,
    search_provider: SearchProvider,
    rng: random.Random,
) -> Optional[GeneratedMeal]:
    extracted = generate_search_suggestion(search_provider, query, extractor)
    if extracted is None:
        extracted = generate_combination_suggestion(liked, extractor, rng=rng)
    if extracted is None:
        return None

    new_recipe = recipe_store.create(
        Recipe.from_extracted(extracted, id="", source_text=None, now=datetime.now(timezone.utc))
    )
    return GeneratedMeal(recipe=new_recipe, servings=new_recipe.servings, is_suggestion=True)


def _search_query(preferences: HouseholdPreferences) -> str:
    if preferences.food_preferences:
        return ", ".join(preferences.food_preferences)
    return "a simple weeknight dinner"
