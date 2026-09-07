from __future__ import annotations

from fastapi import APIRouter

from little_meals.api.errors import ApiError
from little_meals.models import ActualCostUpdate, ItemCheckedUpdate, ShoppingList
from little_meals.planning.shopping_list import build_shopping_list_items
from little_meals.store.ingredient_catalog_store import IngredientCatalogStore
from little_meals.store.plan_store import MealPlanStore
from little_meals.store.recipe_store import RecipeStore
from little_meals.store.shopping_list_store import ShoppingListItemNotFound, ShoppingListNotFound, ShoppingListStore


def build_shopping_router(
    store: ShoppingListStore,
    plan_store: MealPlanStore,
    recipe_store: RecipeStore,
    ingredient_catalog_store: IngredientCatalogStore,
) -> APIRouter:
    router = APIRouter(prefix="/api/shopping-list")

    def _current_finalized_plan():
        plan = plan_store.get_current()
        if plan is None:
            raise ApiError(404, "NO_CURRENT_PLAN", "No meal plan has been generated yet")
        if not plan.finalized:
            raise ApiError(409, "PLAN_NOT_FINALIZED", "Finalize this week's plan before generating a shopping list")
        return plan

    @router.get("/current", response_model=ShoppingList)
    def get_current() -> ShoppingList:
        plan = _current_finalized_plan()
        shopping_list = store.get_for_plan(plan.id)
        if shopping_list is None:
            raise ApiError(404, "NOT_GENERATED", "No shopping list has been generated for this plan yet")
        return shopping_list

    @router.post("/generate", response_model=ShoppingList, status_code=201)
    def generate() -> ShoppingList:
        plan = _current_finalized_plan()
        existing = store.get_for_plan(plan.id)
        if existing is not None:
            return existing
        items = build_shopping_list_items(plan, recipe_store, ingredient_catalog_store.get_all())
        return store.create(plan.id, items)

    @router.patch("/{list_id}/items/{item_id}/checked", response_model=ShoppingList)
    def update_checked(list_id: str, item_id: str, payload: ItemCheckedUpdate) -> ShoppingList:
        try:
            return store.set_item_checked(list_id, item_id, payload.checked)
        except (ShoppingListNotFound, ShoppingListItemNotFound) as exc:
            raise ApiError(404, "NOT_FOUND", str(exc)) from exc

    @router.patch("/{list_id}/cost", response_model=ShoppingList)
    def update_cost(list_id: str, payload: ActualCostUpdate) -> ShoppingList:
        try:
            return store.set_actual_cost(list_id, payload.actual_cost)
        except ShoppingListNotFound as exc:
            raise ApiError(404, "NOT_FOUND", str(exc)) from exc

    @router.get("/{list_id}", response_model=ShoppingList)
    def get_list(list_id: str) -> ShoppingList:
        try:
            return store.get(list_id)
        except ShoppingListNotFound as exc:
            raise ApiError(404, "NOT_FOUND", str(exc)) from exc

    return router
