from __future__ import annotations

from fastapi import APIRouter

from little_meals.api.errors import ApiError
from little_meals.models import CookedUpdate, MealPlan, ServingsUpdate
from little_meals.planning.selection import select_recipes_for_plan
from little_meals.store.household_store import HouseholdPreferencesStore
from little_meals.store.plan_store import MealPlanStore, PlanMealNotFound, PlanNotFound
from little_meals.store.recipe_store import RecipeStore


def build_plan_router(store: MealPlanStore, recipe_store: RecipeStore, household_store: HouseholdPreferencesStore) -> APIRouter:
    router = APIRouter(prefix="/api/plan")

    def _fetch(plan_id: str) -> MealPlan:
        try:
            return store.get(plan_id)
        except PlanNotFound as exc:
            raise ApiError(404, "NOT_FOUND", str(exc)) from exc

    @router.get("/current", response_model=MealPlan)
    def get_current() -> MealPlan:
        plan = store.get_current()
        if plan is None:
            raise ApiError(404, "NO_CURRENT_PLAN", "No meal plan has been generated yet")
        return plan

    @router.post("/generate", response_model=MealPlan, status_code=201)
    def generate() -> MealPlan:
        preferences = household_store.get()
        recipes = recipe_store.list()
        selected = select_recipes_for_plan(recipes, preferences.recipes_per_week)
        recipe_servings = [(recipe.id, recipe.servings) for recipe in selected]
        return store.create(recipe_servings)

    @router.patch("/{plan_id}/meals/{meal_id}/servings", response_model=MealPlan)
    def update_servings(plan_id: str, meal_id: str, payload: ServingsUpdate) -> MealPlan:
        try:
            return store.set_servings(plan_id, meal_id, payload.servings)
        except (PlanNotFound, PlanMealNotFound) as exc:
            raise ApiError(404, "NOT_FOUND", str(exc)) from exc

    @router.patch("/{plan_id}/meals/{meal_id}/cooked", response_model=MealPlan)
    def update_cooked(plan_id: str, meal_id: str, payload: CookedUpdate) -> MealPlan:
        try:
            return store.set_cooked(plan_id, meal_id, payload.cooked)
        except (PlanNotFound, PlanMealNotFound) as exc:
            raise ApiError(404, "NOT_FOUND", str(exc)) from exc

    @router.post("/{plan_id}/finalize", response_model=MealPlan)
    def finalize(plan_id: str) -> MealPlan:
        try:
            return store.finalize(plan_id)
        except PlanNotFound as exc:
            raise ApiError(404, "NOT_FOUND", str(exc)) from exc

    @router.get("/{plan_id}", response_model=MealPlan)
    def get_plan(plan_id: str) -> MealPlan:
        return _fetch(plan_id)

    return router
