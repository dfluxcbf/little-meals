from __future__ import annotations

import logging
import random
import re
from typing import Optional, Protocol

import httpx

from little_meals.llm.extraction import ExtractionError, RecipeExtractionService
from little_meals.llm.ollama_client import OllamaUnavailable
from little_meals.models import ExtractedRecipe, IngredientSubstitutes, Recipe

logger = logging.getLogger(__name__)


class SearchProvider(Protocol):
    """Seam for the online recipe search architecture.md defers ("Online
    recipe search | Provider TBD"). A provider turns a filter into zero or
    more free-text recipe blurbs, each of which gets run through the same
    extraction service as a manual submission - see `generate_search_candidates`.
    """

    def search_many(self, food_filter: Optional[dict], count: int) -> list[str]: ...

    def get_substitutes(self, ingredient_name: str) -> Optional[IngredientSubstitutes]: ...


class NullSearchProvider:
    """The default until a real provider is chosen and configured: always
    returns no results, so suggestion generation falls back to combining
    stored recipes instead of silently failing or fabricating results."""

    def search_many(self, food_filter: Optional[dict], count: int) -> list[str]:
        return []

    def get_substitutes(self, ingredient_name: str) -> Optional[IngredientSubstitutes]:
        return None


#: complexSearch parameters every request sets regardless of the household's
#: filter, overriding anything the household's own pasted-in JSON says for
#: these specific keys - see docs/spoonacular_plan.md: results must be full
#: meals (never a side dish/dessert/etc.), never a dish-name-specific search
#: (only a style/ingredient `query`), never the same handful of top-ranked
#: hits every time, and always carry nutrition data so a suggestion's
#: calorie/macro numbers come from Spoonacular rather than being
#: re-estimated.
_ALWAYS_ON_SEARCH_PARAMS: dict[str, object] = {
    "sort": "random",
    "type": "main course",
    "instructionsRequired": True,
    "addRecipeNutrition": True,
}


def build_complex_search_params(food_filter: Optional[dict], count: Optional[int] = None) -> dict[str, object]:
    """Builds the `/recipes/complexSearch` query parameters for a household
    filter - the single source of truth for both the real Spoonacular
    request (SpoonacularSearchProvider.search_many, which adds `apiKey` on
    top) and the read-only JSON preview shown on the recipe-preferences
    page, so what the household sees is exactly what gets sent.
    `food_filter` is the household's own Spoonacular query parameters,
    built on the dedicated /settings/recipe-preferences page (see
    docs/spoonacular_api.md) - passed through as-is except that
    `_ALWAYS_ON_SEARCH_PARAMS` always wins on overlapping keys, and
    `number` (from `count`) is always software-controlled too. Never
    includes `apiKey`.

    Any list-valued entry is comma-joined into the single string
    Spoonacular's own list-shaped parameters (cuisine, intolerances, etc.)
    actually expect - httpx would otherwise encode a list value as
    repeated query keys (`cuisine=a&cuisine=b`), which Spoonacular doesn't
    understand. Only a household whose filter predates the current
    single-string-per-field form (a hand-pasted JSON filter, or a direct
    PUT against the JSON API) would ever hit this.
    """
    params: dict[str, object] = dict(food_filter) if food_filter else {}
    for key, value in params.items():
        if isinstance(value, list):
            params[key] = ",".join(str(v) for v in value)
    params.update(_ALWAYS_ON_SEARCH_PARAMS)
    if count is not None:
        params["number"] = count
    return params


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

    Every complexSearch call always sets `sort=random`, `type=main course`,
    `instructionsRequired=true`, and `addRecipeNutrition=true` - see
    build_complex_search_params/docs/spoonacular_plan.md: results must be
    full meals (never a side dish/dessert/etc.), never a dish-name-specific
    search (only a style/ingredient `query`), and never the same handful of
    top-ranked hits every time.
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

    def search_many(self, food_filter: Optional[dict], count: int) -> list[str]:
        """Fetches up to `count` recipes in bulk - used both by the
        standalone Spoonacular import command (planning/spoonacular_import.py)
        and by plan_builder's suggestion-candidate fetch (3 per AI-suggestion
        slot).

        Deliberately two HTTP calls total, regardless of `count`: one
        complexSearch for candidate ids, one informationBulk for all of
        their full ingredients/instructions - N `/recipes/{id}/information`
        calls would burn through the free tier's daily quota far faster for
        no benefit (see architecture.md's "Online recipe search" row).
        """
        if count <= 0:
            return []

        params = build_complex_search_params(food_filter, count=count)
        params["apiKey"] = self._api_key

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

    def get_substitutes(self, ingredient_name: str) -> IngredientSubstitutes:
        """For the shopping-list "find a substitute" action - looked up by
        plain ingredient name (a shopping-list item is a merged free-text
        name, not a Spoonacular ingredient id)."""
        response = self._client.get(
            f"{self._base_url}/food/ingredients/substitutes",
            params={"ingredientName": ingredient_name, "apiKey": self._api_key},
        )
        response.raise_for_status()
        data = response.json()
        return IngredientSubstitutes(
            ingredient=data.get("ingredient", ingredient_name),
            substitutes=data.get("substitutes") or [],
            message=data.get("message", ""),
        )

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


def generate_search_candidates(
    provider: SearchProvider,
    food_filter: Optional[dict],
    extractor: RecipeExtractionService,
    count: int,
) -> list[ExtractedRecipe]:
    """Search-based suggestion candidates: ask the provider for up to
    `count` results, extract each. A provider failure (including the
    NullSearchProvider default returning nothing) or a candidate that fails
    extraction just means fewer candidates - possibly zero, never an
    exception that aborts plan generation."""
    try:
        results = provider.search_many(food_filter, count)
    except Exception as exc:  # noqa: BLE001 - a third-party search backend can fail in unpredictable ways
        logger.warning("Search provider %s failed, skipping: %s", type(provider).__name__, exc)
        return []

    candidates = []
    for text in results:
        try:
            candidates.append(extractor.extract(text))
        except (ExtractionError, OllamaUnavailable) as exc:
            logger.warning("Skipping a suggestion candidate that failed extraction: %s", exc)
    return candidates
