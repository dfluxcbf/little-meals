from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from little_meals.api.app import create_app
from little_meals.config import Settings
from little_meals.models import Classification, Ingredient, Nutrition, Recipe
from little_meals.store.cook_along_store import CookAlongStore
from little_meals.store.household_store import HouseholdPreferencesStore
from little_meals.store.notification_store import NotificationStore
from little_meals.store.plan_store import MealPlanStore
from little_meals.store.recipe_store import RecipeStore
from little_meals.store.shopping_list_store import ShoppingListStore


def pytest_configure(config: pytest.Config) -> None:
    # little_requirements isn't importable under `bazel test` (it's a
    # pipx-installed dev tool, not a pip.parse dep - see requirements_policy.md),
    # so its pytest11 plugin doesn't self-register the marker there. Registering
    # it here makes `@pytest.mark.requirement(...)` valid in both environments.
    config.addinivalue_line("markers", "requirement(requirement_id): little-requirements requirement ID")


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
def plan_store(tmp_path: Path) -> MealPlanStore:
    return MealPlanStore(tmp_path / "plan.db")


@pytest.fixture
def shopping_list_store(tmp_path: Path) -> ShoppingListStore:
    return ShoppingListStore(tmp_path / "shopping_list.db")


@pytest.fixture
def notification_store(tmp_path: Path) -> NotificationStore:
    return NotificationStore(tmp_path / "notification.db")


@pytest.fixture
def cook_along_store(tmp_path: Path) -> CookAlongStore:
    return CookAlongStore(tmp_path / "cook_along.db")


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
        source_text="chicken with lemon and garlic",
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def client(
    store: RecipeStore,
    household_store: HouseholdPreferencesStore,
    plan_store: MealPlanStore,
    shopping_list_store: ShoppingListStore,
    notification_store: NotificationStore,
    cook_along_store: CookAlongStore,
) -> TestClient:
    settings = Settings(data_dir=store._dir.parent)
    app = create_app(
        settings=settings,
        store=store,
        household_store=household_store,
        plan_store=plan_store,
        shopping_list_store=shopping_list_store,
        notification_store=notification_store,
        cook_along_store=cook_along_store,
    )
    return TestClient(app)
