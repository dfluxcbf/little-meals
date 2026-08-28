from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from little_meals.llm.extraction import ExtractionError, RecipeExtractionService
from little_meals.llm.ollama_client import OllamaUnavailable
from little_meals.models import Recipe
from little_meals.planning.suggestion import SpoonacularSearchProvider
from little_meals.store.recipe_store import RecipeStore

logger = logging.getLogger(__name__)


def build_search_query(food_preferences: list[str]) -> Optional[str]:
    """Turns household food preferences into one Spoonacular search query.

    `complexSearch`'s `query` param takes free-text search terms rather than
    a list, so preferences are just joined. `None` (no query - broadest
    search) when the household hasn't configured any, so an import still
    works for a household that hasn't touched /settings yet.
    """
    if not food_preferences:
        return None
    return " ".join(food_preferences)


@dataclass
class ImportResult:
    requested: int
    imported: list[Recipe] = field(default_factory=list)
    skipped: int = 0


def import_recipes(
    provider: SpoonacularSearchProvider,
    extractor: RecipeExtractionService,
    store: RecipeStore,
    *,
    query: Optional[str],
    count: int,
) -> ImportResult:
    """Fetches up to `count` recipes from Spoonacular matching `query`,
    normalizes each through the same LLM extraction pipeline every other
    recipe source (manual submission, AI suggestion, search suggestion)
    uses, and stores it in the library. A single recipe failing extraction
    (bad Ollama output, Ollama unreachable) is logged and skipped rather
    than aborting the whole batch - same reasoning as
    `generate_search_suggestion` in suggestion.py.
    """
    result = ImportResult(requested=count)
    texts = provider.search_many(query, count)
    for text in texts:
        try:
            extracted = extractor.extract(text)
        except (ExtractionError, OllamaUnavailable) as exc:
            logger.warning("Skipping a Spoonacular recipe that failed extraction: %s", exc)
            result.skipped += 1
            continue
        recipe = Recipe.from_extracted(extracted, id="", source_text=text, now=datetime.now(timezone.utc))
        result.imported.append(store.create(recipe))
    return result
