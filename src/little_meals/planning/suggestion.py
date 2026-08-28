from __future__ import annotations

import logging
import random
import re
from typing import Optional, Protocol

import httpx

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


class SpoonacularSearchProvider:
    """Searches Spoonacular's recipe database (see architecture.md's "Online
    recipe search" decision - chosen for its household-scale free tier and
    because it returns real structured recipes rather than raw web-search
    snippets that would need scraping).

    Deliberately does NOT use Spoonacular's own classification/nutrition
    data - a hit's ingredients and steps are reformatted as free text and
    handed to the same extraction service every other suggestion source
    uses, so classification/nutrition estimation stays consistent (and
    LLM-derived) regardless of where a suggestion came from.

    Only returns the single best match (Milestone 4's generate_search_suggestion
    only ever looks at the first result anyway), so each call to `search` is
    two HTTP requests: complexSearch to find a candidate, then
    /recipes/{id}/information for its actual ingredients/instructions.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.spoonacular.com",
        timeout_s: float = 15.0,
        client: Optional[httpx.Client] = None,
    ):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=timeout_s)

    def search(self, query: str) -> list[str]:
        search_response = self._client.get(
            f"{self._base_url}/recipes/complexSearch",
            params={"query": query, "number": 1, "apiKey": self._api_key},
        )
        search_response.raise_for_status()
        results = search_response.json().get("results", [])
        if not results:
            return []

        recipe_id = results[0]["id"]
        info_response = self._client.get(
            f"{self._base_url}/recipes/{recipe_id}/information",
            params={"apiKey": self._api_key},
        )
        info_response.raise_for_status()
        return [format_spoonacular_recipe(info_response.json())]

    def search_many(self, query: Optional[str], count: int) -> list[str]:
        """Fetches up to `count` recipes in bulk - used by the standalone
        Spoonacular import command (planning/spoonacular_import.py) rather
        than the one-result-at-a-time `search` above.

        Deliberately two HTTP calls total, regardless of `count`: one
        complexSearch for candidate ids, one informationBulk for all of
        their full ingredients/instructions - N `/recipes/{id}/information`
        calls would burn through the free tier's daily quota far faster for
        no benefit (see architecture.md's "Online recipe search" row).
        """
        if count <= 0:
            return []

        params: dict[str, object] = {"number": count, "apiKey": self._api_key}
        if query:
            params["query"] = query
        search_response = self._client.get(f"{self._base_url}/recipes/complexSearch", params=params)
        search_response.raise_for_status()
        results = search_response.json().get("results", [])
        if not results:
            return []

        ids = ",".join(str(result["id"]) for result in results)
        bulk_response = self._client.get(
            f"{self._base_url}/recipes/informationBulk",
            params={"ids": ids, "apiKey": self._api_key},
        )
        bulk_response.raise_for_status()
        return [format_spoonacular_recipe(info) for info in bulk_response.json()]

    def close(self) -> None:
        if self._owns_client:
            self._client.close()


_HTML_TAG_RE = re.compile(r"<[^>]+>")


def format_spoonacular_recipe(info: dict) -> str:
    title = info.get("title") or "A recipe"
    ingredients = ", ".join(
        ingredient.get("original") or ingredient.get("name", "")
        for ingredient in info.get("extendedIngredients", [])
        if ingredient.get("original") or ingredient.get("name")
    )

    # Spoonacular's `instructions` field is free text but sometimes carries
    # HTML markup (e.g. "<ol><li>...</li></ol>") - strip tags rather than
    # rendering them into the extraction prompt as literal text.
    instructions = _HTML_TAG_RE.sub(" ", info.get("instructions") or "").strip()
    if not instructions:
        # Some recipes only populate the structured step-by-step field.
        steps = [
            step["step"]
            for block in info.get("analyzedInstructions", [])
            for step in block.get("steps", [])
            if step.get("step")
        ]
        instructions = " ".join(steps)

    return f"{title}\n\nIngredients: {ingredients}\n\nInstructions: {instructions}"


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
