from __future__ import annotations

import re
from typing import Any, Optional

from pydantic import ValidationError

from little_meals.llm.ollama_client import OllamaBadResponse, OllamaClient
from little_meals.llm.prompts import build_extraction_prompt
from little_meals.models import Classification, ExtractedRecipe, Ingredient

# Empirically, the default extraction model (qwen2.5-coder:14b) follows the
# meat/poultry rule reliably but is inconsistent on simple fish-only dishes -
# it sometimes defaults to "other" even when the prompt names the exact dish
# ("baked salmon", "tuna sandwich") as a worked pescetarian example. Rather
# than keep fighting prompt-only fixes against a model that won't reliably
# follow this one instruction, this is a deterministic safety net applied
# after extraction. It only ever overrides *toward* a classification the
# ingredient list clearly supports - an unrecognized protein name is weak
# evidence, not proof of absence, so it never guesses "vegetarian" just
# because it didn't recognize a keyword.
_MEAT_KEYWORDS = frozenset(
    {
        "chicken", "beef", "pork", "turkey", "lamb", "bacon", "ham", "sausage",
        "duck", "veal", "venison", "steak", "mince", "prosciutto", "pancetta",
        "chorizo", "salami", "pepperoni", "brisket", "ribs", "meat", "goat",
        "rabbit", "gelatin", "gelatine", "lard",
    }
)
_FISH_KEYWORDS = frozenset(
    {
        "salmon", "tuna", "shrimp", "prawn", "prawns", "cod", "anchovy",
        "anchovies", "crab", "tilapia", "trout", "halibut", "mackerel",
        "sardine", "sardines", "lobster", "clam", "clams", "mussel", "mussels",
        "oyster", "oysters", "scallop", "scallops", "squid", "calamari",
        "fish", "haddock", "sole", "bass", "snapper", "swordfish", "octopus",
        "eel", "roe", "caviar",
    }
)
_WORD_RE = re.compile(r"[a-z]+")


class ExtractionError(RuntimeError):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message)
        self.details = details


class RecipeExtractionService:
    def __init__(self, client: OllamaClient):
        self._client = client

    def extract(self, free_text: str) -> ExtractedRecipe:
        if not free_text or not free_text.strip():
            raise ExtractionError("Recipe text must not be empty")

        schema = ExtractedRecipe.model_json_schema()
        prompt = build_extraction_prompt(free_text, schema)

        # OllamaUnavailable propagates unwrapped so the API layer can map it
        # to 503 (service unavailable) instead of 422 (bad extraction).
        try:
            payload = self._client.generate_json(prompt, schema=schema)
        except OllamaBadResponse as exc:
            raise ExtractionError(f"Ollama did not return usable JSON: {exc}") from exc

        try:
            extracted = ExtractedRecipe.model_validate(payload)
        except ValidationError as exc:
            raise ExtractionError("Model output did not match the recipe schema", details=exc.errors()) from exc

        return _reconcile_classification(extracted)


def _reconcile_classification(extracted: ExtractedRecipe) -> ExtractedRecipe:
    words = _ingredient_words(extracted.ingredients)
    has_meat = bool(words & _MEAT_KEYWORDS)
    has_fish = bool(words & _FISH_KEYWORDS)

    if has_meat and extracted.classification != Classification.OTHER:
        return extracted.model_copy(update={"classification": Classification.OTHER})
    if has_fish and not has_meat and extracted.classification != Classification.PESCETARIAN:
        return extracted.model_copy(update={"classification": Classification.PESCETARIAN})
    return extracted


def _ingredient_words(ingredients: list[Ingredient]) -> set[str]:
    words: set[str] = set()
    for ingredient in ingredients:
        words.update(_WORD_RE.findall(ingredient.name.lower()))
    return words
