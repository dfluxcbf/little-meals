from __future__ import annotations

import logging
import random
from typing import Optional, Protocol

from little_meals.llm.extraction import ExtractionError, RecipeExtractionService
from little_meals.llm.ollama_client import OllamaUnavailable
from little_meals.models import ExtractedRecipe, Recipe

logger = logging.getLogger(__name__)


class SearchProvider(Protocol):
    """Seam for the online recipe search architecture.md defers ("Online
    recipe search | Provider TBD"). A provider turns a query into zero or
    more free-text recipe blurbs, each of which gets run through the same
    extraction service as a manual submission - see `generate_search_suggestion`.
    """

    def search(self, query: str) -> list[str]: ...


class NullSearchProvider:
    """The default until a real provider is chosen and configured: always
    returns no results, so suggestion generation falls back to combining
    stored recipes instead of silently failing or fabricating results."""

    def search(self, query: str) -> list[str]:
        return []


def build_combination_text(recipe_a: Recipe, recipe_b: Recipe) -> str:
    """Free text blending two stored recipes into one new-dish brief, fed
    to the same extraction prompt a manual submission would use. The LLM
    does the actual creative synthesis; this just hands it the raw material."""
    ingredients_a = ", ".join(_describe_ingredient(i) for i in recipe_a.ingredients)
    ingredients_b = ", ".join(_describe_ingredient(i) for i in recipe_b.ingredients)
    steps_a = " ".join(recipe_a.steps)
    steps_b = " ".join(recipe_b.steps)
    return (
        f"Invent one new dish that fuses these two recipes into something that actually makes sense "
        f"to cook together - don't just list both separately.\n\n"
        f"Recipe A - {recipe_a.name}: ingredients: {ingredients_a}. steps: {steps_a}\n\n"
        f"Recipe B - {recipe_b.name}: ingredients: {ingredients_b}. steps: {steps_b}"
    )


def _describe_ingredient(ingredient) -> str:
    parts = [str(ingredient.quantity)] if ingredient.quantity is not None else []
    if ingredient.unit:
        parts.append(ingredient.unit)
    parts.append(ingredient.name)
    return " ".join(parts)


def generate_combination_suggestion(
    liked_recipes: list[Recipe],
    extractor: RecipeExtractionService,
    rng: Optional[random.Random] = None,
) -> Optional[ExtractedRecipe]:
    """Combine two distinct, randomly-picked liked recipes into a new
    suggestion. Returns None (rather than raising) when there aren't at
    least two liked recipes to combine, or when the extraction service
    can't produce a usable result - a suggestion source failing shouldn't
    break the rest of plan generation, it should just contribute nothing."""
    if len(liked_recipes) < 2:
        return None

    rng = rng or random.Random()
    recipe_a, recipe_b = rng.sample(liked_recipes, k=2)
    text = build_combination_text(recipe_a, recipe_b)

    try:
        return extractor.extract(text)
    except (ExtractionError, OllamaUnavailable) as exc:
        logger.warning("Combination suggestion failed, skipping: %s", exc)
        return None


def generate_search_suggestion(
    provider: SearchProvider,
    query: str,
    extractor: RecipeExtractionService,
) -> Optional[ExtractedRecipe]:
    """Search-based suggestion: ask the provider for candidate text, extract
    the first result. Returns None if the provider has nothing (including
    the NullSearchProvider default) or extraction fails."""
    try:
        results = provider.search(query)
    except Exception as exc:  # noqa: BLE001 - a third-party search backend can fail in unpredictable ways
        logger.warning("Search provider %s failed, skipping: %s", type(provider).__name__, exc)
        return None
    if not results:
        return None

    try:
        return extractor.extract(results[0])
    except (ExtractionError, OllamaUnavailable) as exc:
        logger.warning("Search-based suggestion failed, skipping: %s", exc)
        return None
