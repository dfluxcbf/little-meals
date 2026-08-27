from __future__ import annotations

from typing import Any, Optional

from pydantic import ValidationError

from little_meals.llm.ollama_client import OllamaBadResponse, OllamaClient
from little_meals.llm.prompts import build_extraction_prompt
from little_meals.models import ExtractedRecipe


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
            return ExtractedRecipe.model_validate(payload)
        except ValidationError as exc:
            raise ExtractionError("Model output did not match the recipe schema", details=exc.errors()) from exc
