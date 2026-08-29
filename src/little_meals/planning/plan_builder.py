from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from little_meals.llm.extraction import RecipeExtractionService
from little_meals.models import HouseholdPreferences, Preference, Recipe
from little_meals.planning.selection import select_recipes_for_plan
from little_meals.planning.suggestion import SearchProvider, generate_combination_suggestion, generate_search_candidates
from little_meals.store.household_store import HouseholdPreferencesStore
from little_meals.store.plan_store import MealSpec
from little_meals.store.recipe_store import RecipeStore

_CANDIDATES_PER_SUGGESTION = 3


@dataclass
class GeneratedMeal:
    """One meal ready to be written into a plan - see store/plan_store.py's
    MealSpec for the persisted shape this maps onto."""

    recipe: Recipe
    servings: int
    is_suggestion: bool
    candidate_recipe_ids: list[str] = field(default_factory=list)
    """Sibling recipe ids fetched alongside this one from the same
    Spoonacular batch (including this meal's own id) - empty for library
    picks and combination-suggestion fallbacks. Lets the plan-review UI
    show "the same N already-normalized dishes" for this slot without a
    new fetch - see plan_store.py's plan_meal_candidates table."""


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
    filter_ = _search_filter(preferences)
    for _ in range(ai_count):
        generated = _generate_suggestion_meal(liked, filter_, recipe_store, extractor, search_provider, rng)
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
    return [MealSpec(g.recipe.id, g.servings, g.is_suggestion, tuple(g.candidate_recipe_ids)) for g in generated]


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

    return _generate_suggestion_meal(liked, _search_filter(preferences), recipe_store, extractor, search_provider, rng)


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


def _generate_suggestion_meal(
    liked: list[Recipe],
    filter_: dict,
    recipe_store: RecipeStore,
    extractor: RecipeExtractionService,
    search_provider: SearchProvider,
    rng: random.Random,
) -> Optional[GeneratedMeal]:
    """Fetches up to `_CANDIDATES_PER_SUGGESTION` Spoonacular candidates for
    one suggestion slot (falling back to a single combination suggestion if
    the search provider has nothing), commits every extracted candidate to
    the library immediately - same as any other suggestion, per
    architecture.md's "a suggestion is a normal recipe from the moment it's
    generated" rule - and picks one at random to fill the slot. The other
    committed candidates ride along as `candidate_recipe_ids` so the plan
    review UI can offer them later without a second fetch."""
    candidates = generate_search_candidates(search_provider, filter_, extractor, _CANDIDATES_PER_SUGGESTION)
    if not candidates:
        combo = generate_combination_suggestion(liked, extractor, rng=rng)
        candidates = [combo] if combo is not None else []
    if not candidates:
        return None

    committed = [
        recipe_store.create(Recipe.from_extracted(c, id="", source_text=None, now=datetime.now(timezone.utc)))
        for c in candidates
    ]
    chosen = rng.choice(committed)
    return GeneratedMeal(
        recipe=chosen,
        servings=chosen.servings,
        is_suggestion=True,
        candidate_recipe_ids=[r.id for r in committed],
    )


def _search_filter(preferences: HouseholdPreferences) -> dict:
    if preferences.food_filter is not None:
        return preferences.food_filter
    return {"query": "a simple weeknight dinner"}
