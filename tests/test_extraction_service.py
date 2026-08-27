from __future__ import annotations

import json

import httpx
import pytest

from little_meals.llm.extraction import ExtractionError, RecipeExtractionService
from little_meals.llm.ollama_client import OllamaClient, OllamaUnavailable
from little_meals.models import ExtractedRecipe

VALID_PAYLOAD = {
    "name": "Tomato Soup",
    "cook_time_minutes": 20,
    "classification": "vegetarian",
    "nutrition": {"calories_per_serving": 180},
    "servings": 4,
    "ingredients": [{"name": "tomato", "quantity": 4, "unit": "pieces"}],
    "steps": ["Simmer the tomatoes.", "Blend until smooth."],
}


def _service_with(handler) -> RecipeExtractionService:
    transport = httpx.MockTransport(handler)
    client = OllamaClient("http://ollama.test", "test-model", timeout_s=5.0, client=httpx.Client(transport=transport))
    return RecipeExtractionService(client)


@pytest.mark.requirement("REQ-000000004")
def test_extract_valid_json_returns_extracted_recipe():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": json.dumps(VALID_PAYLOAD)})

    service = _service_with(handler)
    result = service.extract("some tomato soup recipe")

    assert isinstance(result, ExtractedRecipe)
    assert result.name == "Tomato Soup"
    assert result.classification.value == "vegetarian"
    assert result.nutrition.calories_per_serving == 180
    assert len(result.steps) == 2


@pytest.mark.requirement("REQ-000000005")
def test_extract_malformed_json_raises_extraction_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": "Sure! Here's the recipe: {"})

    service = _service_with(handler)
    with pytest.raises(ExtractionError):
        service.extract("some recipe")


def test_extract_schema_invalid_payload_raises_extraction_error_with_details():
    bad_payload = dict(VALID_PAYLOAD)
    bad_payload["cook_time_minutes"] = -5
    bad_payload["ingredients"] = []

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": json.dumps(bad_payload)})

    service = _service_with(handler)
    with pytest.raises(ExtractionError) as excinfo:
        service.extract("some recipe")
    assert excinfo.value.details


def test_extract_empty_input_raises_without_http_call():
    called = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        called["count"] += 1
        return httpx.Response(200, json={"response": json.dumps(VALID_PAYLOAD)})

    service = _service_with(handler)
    with pytest.raises(ExtractionError):
        service.extract("   ")

    assert called["count"] == 0


def test_extract_propagates_ollama_unavailable_unwrapped():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    service = _service_with(handler)
    with pytest.raises(OllamaUnavailable):
        service.extract("some recipe")
