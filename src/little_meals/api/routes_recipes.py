from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from little_meals.api.errors import ApiError
from little_meals.config import Settings
from little_meals.models import Recipe, RecipeCreate, RecipeUpdate
from little_meals.store.recipe_store import RecipeNotFound, RecipeStore


def build_recipes_router(store: RecipeStore, settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/api")

    def _fetch(recipe_id: str) -> Recipe:
        try:
            return store.get(recipe_id)
        except RecipeNotFound as exc:
            raise ApiError(404, "NOT_FOUND", str(exc)) from exc

    @router.get("/recipes", response_model=list[Recipe])
    def list_recipes() -> list[Recipe]:
        return store.list()

    @router.get("/recipes/{recipe_id}", response_model=Recipe)
    def get_recipe(recipe_id: str) -> Recipe:
        return _fetch(recipe_id)

    @router.post("/recipes", response_model=Recipe, status_code=201)
    def create_recipe(payload: RecipeCreate) -> Recipe:
        now = datetime.now(timezone.utc)
        recipe = Recipe(
            id="",
            name=payload.name,
            cook_time_minutes=payload.cook_time_minutes,
            classification=payload.classification,
            difficulty=payload.difficulty,
            nutrition=payload.nutrition,
            servings=payload.servings,
            ingredients=payload.ingredients,
            steps=payload.steps,
            source_text=None,
            created_at=now,
            updated_at=now,
        )
        return store.create(recipe)

    @router.put("/recipes/{recipe_id}", response_model=Recipe)
    def update_recipe(recipe_id: str, payload: RecipeUpdate) -> Recipe:
        _fetch(recipe_id)
        now = datetime.now(timezone.utc)
        recipe = Recipe(
            id=recipe_id,
            name=payload.name,
            cook_time_minutes=payload.cook_time_minutes,
            classification=payload.classification,
            difficulty=payload.difficulty,
            nutrition=payload.nutrition,
            servings=payload.servings,
            ingredients=payload.ingredients,
            steps=payload.steps,
            source_text=None,
            created_at=now,
            updated_at=now,
        )
        try:
            return store.update(recipe_id, recipe)
        except RecipeNotFound as exc:
            raise ApiError(404, "NOT_FOUND", str(exc)) from exc

    @router.delete("/recipes/{recipe_id}", status_code=204)
    def delete_recipe(recipe_id: str) -> None:
        try:
            store.delete(recipe_id)
        except RecipeNotFound as exc:
            raise ApiError(404, "NOT_FOUND", str(exc)) from exc

    @router.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "recipes_dir": str(settings.recipes_dir),
        }

    return router
