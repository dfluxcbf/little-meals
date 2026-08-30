from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from little_meals.api.errors import ApiError
from little_meals.llm.extraction import RecipeExtractionService
from little_meals.models import CookedUpdate, MealPlan, Recipe, ServingsUpdate
from little_meals.planning.plan_builder import build_meal_specs, generate_single_replacement, list_controlled_reroll_candidates
from little_meals.store.household_store import HouseholdPreferencesStore
from little_meals.store.plan_store import MealPlanStore, PlanMealNotFound, PlanNotFound
from little_meals.store.recipe_store import RecipeNotFound, RecipeStore


class ChooseRecipe(BaseModel):
    recipe_id: str


def build_plan_router(
    store: MealPlanStore,
    recipe_store: RecipeStore,
    household_store: HouseholdPreferencesStore,
    extractor: RecipeExtractionService,
) -> APIRouter:
    router = APIRouter(prefix="/api/plan")

    def _fetch(plan_id: str) -> MealPlan:
        try:
            return store.get(plan_id)
        except PlanNotFound as exc:
            raise ApiError(404, "NOT_FOUND", str(exc)) from exc

    def _require_draft(plan: MealPlan) -> None:
        if plan.finalized:
            raise ApiError(409, "PLAN_FINALIZED", "This plan is finalized and can no longer be rerolled")

    def _require_finalized(plan: MealPlan) -> None:
        if not plan.finalized:
            raise ApiError(409, "PLAN_NOT_FINALIZED", "This plan must be confirmed before marking a meal cooked")

    @router.get("/current", response_model=MealPlan)
    def get_current() -> MealPlan:
        plan = store.get_current()
        if plan is None:
            raise ApiError(404, "NO_CURRENT_PLAN", "No meal plan has been generated yet")
        return plan

    @router.post("/generate", response_model=MealPlan, status_code=201)
    def generate() -> MealPlan:
        return store.create(build_meal_specs(recipe_store, household_store, extractor))

    @router.post("/{plan_id}/reroll", response_model=MealPlan)
    def reroll_whole_plan(plan_id: str) -> MealPlan:
        plan = _fetch(plan_id)
        _require_draft(plan)
        return store.replace_meals(plan_id, build_meal_specs(recipe_store, household_store, extractor))

    @router.post("/{plan_id}/meals/{meal_id}/reroll", response_model=MealPlan)
    def reroll_single_meal(plan_id: str, meal_id: str) -> MealPlan:
        plan = _fetch(plan_id)
        _require_draft(plan)
        recipes = recipe_store.list(extractor)
        excluded = {meal.recipe_id for meal in plan.meals}
        replacement = generate_single_replacement(excluded, recipes)
        if replacement is None:
            raise ApiError(422, "NO_REPLACEMENT_AVAILABLE", "No unused recipe available in the library")
        try:
            return store.set_recipe(plan_id, meal_id, replacement.recipe.id, replacement.servings)
        except PlanMealNotFound as exc:
            raise ApiError(404, "NOT_FOUND", str(exc)) from exc

    @router.post("/{plan_id}/meals", response_model=MealPlan, status_code=201)
    def add_meal(plan_id: str) -> MealPlan:
        plan = _fetch(plan_id)
        _require_draft(plan)
        recipes = recipe_store.list(extractor)
        excluded = {meal.recipe_id for meal in plan.meals}
        replacement = generate_single_replacement(excluded, recipes)
        if replacement is None:
            raise ApiError(422, "NO_REPLACEMENT_AVAILABLE", "No unused recipe available in the library")
        return store.add_meal(plan_id, replacement.recipe.id, replacement.servings)

    @router.delete("/{plan_id}/meals/{meal_id}", response_model=MealPlan)
    def remove_meal(plan_id: str, meal_id: str) -> MealPlan:
        plan = _fetch(plan_id)
        _require_draft(plan)
        try:
            return store.remove_meal(plan_id, meal_id)
        except PlanMealNotFound as exc:
            raise ApiError(404, "NOT_FOUND", str(exc)) from exc

    @router.get("/{plan_id}/meals/{meal_id}/alternatives", response_model=list[Recipe])
    def controlled_reroll_alternatives(plan_id: str, meal_id: str) -> list[Recipe]:
        plan = _fetch(plan_id)
        if not any(meal.id == meal_id for meal in plan.meals):
            raise ApiError(404, "NOT_FOUND", f"Meal {meal_id} not found in plan {plan_id}")
        excluded = {meal.recipe_id for meal in plan.meals}
        recipes = recipe_store.list(extractor)
        return list_controlled_reroll_candidates(excluded, recipes)

    @router.post("/{plan_id}/meals/{meal_id}/choose", response_model=MealPlan)
    def choose_alternative(plan_id: str, meal_id: str, payload: ChooseRecipe) -> MealPlan:
        plan = _fetch(plan_id)
        _require_draft(plan)
        try:
            recipe = recipe_store.get(payload.recipe_id)
        except RecipeNotFound as exc:
            raise ApiError(404, "NOT_FOUND", f"Recipe not found: {payload.recipe_id}") from exc
        try:
            return store.set_recipe(plan_id, meal_id, recipe.id, recipe.servings)
        except PlanMealNotFound as exc:
            raise ApiError(404, "NOT_FOUND", str(exc)) from exc

    @router.patch("/{plan_id}/meals/{meal_id}/servings", response_model=MealPlan)
    def update_servings(plan_id: str, meal_id: str, payload: ServingsUpdate) -> MealPlan:
        try:
            return store.set_servings(plan_id, meal_id, payload.servings)
        except (PlanNotFound, PlanMealNotFound) as exc:
            raise ApiError(404, "NOT_FOUND", str(exc)) from exc

    @router.patch("/{plan_id}/meals/{meal_id}/cooked", response_model=MealPlan)
    def update_cooked(plan_id: str, meal_id: str, payload: CookedUpdate) -> MealPlan:
        plan = _fetch(plan_id)
        _require_finalized(plan)
        try:
            return store.set_cooked(plan_id, meal_id, payload.cooked)
        except PlanMealNotFound as exc:
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
