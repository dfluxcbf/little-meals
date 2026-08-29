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


@dataclass
class ImportResult:
    requested: int
    found: int = 0
    """How many candidates Spoonacular's complexSearch actually returned
    for `requested` - can be well under `requested` with no error at all,
    simply because a narrow filter (tight nutrition ranges, several
    excluded cuisines, an exact min==max servings, etc.) combined with the
    software's own always-on constraints (main course, instructions
    required - see suggestion._ALWAYS_ON_SEARCH_PARAMS) leaves few or no
    matching recipes in Spoonacular's database. Distinct from `skipped`
    (a candidate Spoonacular did return, but that failed LLM extraction)
    so the CLI can tell the household which one happened."""
    imported: list[Recipe] = field(default_factory=list)
    skipped: int = 0


def import_recipes(
    provider: SpoonacularSearchProvider,
    extractor: RecipeExtractionService,
    store: RecipeStore,
    *,
    query: Optional[dict],
    count: int,
) -> ImportResult:
    """Fetches up to `count` recipes from Spoonacular matching `query`,
    normalizes each through the same LLM extraction pipeline every other
    recipe source (manual submission, AI suggestion, search suggestion)
    uses, and stores it in the library. A single recipe failing extraction
    (bad Ollama output, Ollama unreachable) is logged and skipped rather
    than aborting the whole batch - same reasoning as
    `generate_search_candidates` in suggestion.py.
    """
    result = ImportResult(requested=count)
    texts = provider.search_many(query, count)
    result.found = len(texts)
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
