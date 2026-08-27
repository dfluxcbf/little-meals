from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import httpx
import pytest
from fastapi.testclient import TestClient

from little_meals.api.app import create_app
from little_meals.config import Settings
from little_meals.llm.extraction import RecipeExtractionService
from little_meals.llm.ollama_client import OllamaClient
from little_meals.models import Classification, Ingredient, Nutrition, Preference, Recipe
from little_meals.store.household_store import HouseholdPreferencesStore
from little_meals.store.recipe_store import RecipeStore


def pytest_configure(config: pytest.Config) -> None:
    # little_requirements isn't importable under `bazel test` (it's a
    # pipx-installed dev tool, not a pip.parse dep - see requirements_policy.md),
    # so its pytest11 plugin doesn't self-register the marker there. Registering
    # it here makes `@pytest.mark.requirement(...)` valid in both environments.
    config.addinivalue_line("markers", "requirement(requirement_id): little-requirements requirement ID")
    config.addinivalue_line("markers", "real_ollama: hits a real local Ollama daemon over HTTP")


@pytest.fixture
def tmp_recipes_dir(tmp_path: Path) -> Path:
    return tmp_path / "recipes"


@pytest.fixture
def store(tmp_recipes_dir: Path) -> RecipeStore:
    return RecipeStore(tmp_recipes_dir)


@pytest.fixture
def household_store(tmp_path: Path) -> HouseholdPreferencesStore:
    return HouseholdPreferencesStore(tmp_path / "household.db")


@pytest.fixture
def sample_recipe() -> Recipe:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return Recipe(
        id="",
        name="Lemon Garlic Chicken",
        cook_time_minutes=30,
        classification=Classification.OTHER,
        nutrition=Nutrition(calories_per_serving=450, protein_g=35.0),
        servings=2,
        ingredients=[
            Ingredient(name="chicken breast", quantity=2, unit="pieces"),
            Ingredient(name="lemon", quantity=1, unit=None),
            Ingredient(name="garlic", quantity=3, unit="cloves"),
        ],
        steps=["Season the chicken.", "Sear until golden.", "Add lemon and garlic, simmer 10 minutes."],
        preference=Preference.LIKED,
        source_text="chicken with lemon and garlic",
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def fake_ollama() -> Callable[[Callable[[httpx.Request], httpx.Response]], OllamaClient]:
    def _build(handler: Callable[[httpx.Request], httpx.Response]) -> OllamaClient:
        transport = httpx.MockTransport(handler)
        http_client = httpx.Client(transport=transport)
        return OllamaClient("http://ollama.test", "test-model", timeout_s=5.0, client=http_client)

    return _build


@pytest.fixture
def client(store: RecipeStore, household_store: HouseholdPreferencesStore) -> TestClient:
    settings = Settings(data_dir=store._dir.parent)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": "{}"})

    ollama_client = OllamaClient(settings.ollama_base_url, settings.ollama_model, 5.0, client=httpx.Client(transport=httpx.MockTransport(handler)))
    extractor = RecipeExtractionService(ollama_client)
    app = create_app(settings=settings, store=store, extractor=extractor, household_store=household_store)
    return TestClient(app)
