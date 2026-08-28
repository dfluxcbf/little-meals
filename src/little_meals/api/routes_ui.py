from __future__ import annotations

from datetime import datetime, time, timezone

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from little_meals.llm.extraction import ExtractionError, RecipeExtractionService
from little_meals.llm.ollama_client import OllamaUnavailable
from little_meals.models import DayOfWeek, HouseholdPreferencesUpdate, MealPlan, Preference, Recipe
from little_meals.planning.plan_builder import build_weekly_plan, generate_single_replacement, list_controlled_reroll_candidates
from little_meals.planning.shopping_list import build_shopping_list_items
from little_meals.planning.suggestion import SearchProvider
from little_meals.store.household_store import HouseholdPreferencesStore
from little_meals.store.plan_store import MealPlanStore, MealSpec, PlanMealNotFound, PlanNotFound
from little_meals.store.recipe_store import RecipeNotFound, RecipeStore
from little_meals.store.shopping_list_store import ShoppingListItemNotFound, ShoppingListNotFound, ShoppingListStore


def build_ui_router(
    store: RecipeStore,
    extractor: RecipeExtractionService,
    household_store: HouseholdPreferencesStore,
    plan_store: MealPlanStore,
    search_provider: SearchProvider,
    shopping_list_store: ShoppingListStore,
    templates: Jinja2Templates,
) -> APIRouter:
    router = APIRouter()

    def _build_meals() -> list[MealSpec]:
        preferences = household_store.get()
        recipes = store.list()
        generated = build_weekly_plan(recipes, preferences, store, extractor, search_provider)
        return [MealSpec(g.recipe.id, g.servings, g.is_suggestion) for g in generated]

    def _render_plan(request: Request) -> HTMLResponse:
        plan = plan_store.get_current()
        meals = []
        if plan is not None:
            for meal in plan.meals:
                try:
                    recipe = store.get(meal.recipe_id)
                except RecipeNotFound:
                    continue
                meals.append({"meal": meal, "recipe": recipe})
        return templates.TemplateResponse(
            request, "plan.html", {"plan": plan, "meals": meals, "nav_active": "plan"}
        )

    @router.get("/", include_in_schema=False)
    def index() -> RedirectResponse:
        return RedirectResponse(url="/recipes", status_code=303)

    @router.get("/recipes", response_class=HTMLResponse, include_in_schema=False)
    def recipes_list(request: Request) -> HTMLResponse:
        recipes = store.list()
        return templates.TemplateResponse(request, "recipes_list.html", {"recipes": recipes, "nav_active": "library"})

    @router.get("/recipes/new", response_class=HTMLResponse, include_in_schema=False)
    def recipe_new_form(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(request, "recipe_new.html", {"error": None, "nav_active": "library"})

    @router.post("/recipes", include_in_schema=False)
    def recipe_new_submit(request: Request, text: str = Form(...)):
        try:
            extracted = extractor.extract(text)
        except (OllamaUnavailable, ExtractionError) as exc:
            return templates.TemplateResponse(
                request, "recipe_new.html", {"error": str(exc), "nav_active": "library"}, status_code=422
            )

        recipe = Recipe.from_extracted(extracted, id="", source_text=text, now=datetime.now(timezone.utc))
        stored = store.create(recipe)
        return RedirectResponse(url=f"/recipes/{stored.id}", status_code=303)

    @router.get("/recipes/{recipe_id}", response_class=HTMLResponse, include_in_schema=False)
    def recipe_detail(request: Request, recipe_id: str) -> HTMLResponse:
        try:
            recipe = store.get(recipe_id)
        except RecipeNotFound:
            return templates.TemplateResponse(
                request, "recipe_not_found.html", {"recipe_id": recipe_id, "nav_active": "library"}, status_code=404
            )
        return templates.TemplateResponse(request, "recipe_detail.html", {"recipe": recipe, "nav_active": "library"})

    @router.get("/recipes/{recipe_id}/cook", include_in_schema=False)
    def cook_start(recipe_id: str) -> RedirectResponse:
        return RedirectResponse(url=f"/recipes/{recipe_id}/cook/1", status_code=303)

    @router.get("/recipes/{recipe_id}/cook/{step_number}", response_class=HTMLResponse, include_in_schema=False)
    def cook_step(request: Request, recipe_id: str, step_number: int) -> HTMLResponse:
        try:
            recipe = store.get(recipe_id)
        except RecipeNotFound:
            return templates.TemplateResponse(
                request, "recipe_not_found.html", {"recipe_id": recipe_id, "nav_active": "library"}, status_code=404
            )

        total_steps = len(recipe.steps)
        if step_number < 1:
            return RedirectResponse(url=f"/recipes/{recipe_id}/cook/1", status_code=303)
        if step_number > total_steps:
            # Ran past the last step (or there were no steps to begin with) -
            # the guided walkthrough is done, prompt for post-cook feedback.
            return templates.TemplateResponse(request, "cook_finish.html", {"recipe": recipe, "feedback": None})

        return templates.TemplateResponse(
            request,
            "cook_step.html",
            {
                "recipe": recipe,
                "step_number": step_number,
                "total_steps": total_steps,
                "step_text": recipe.steps[step_number - 1],
            },
        )

    @router.post("/recipes/{recipe_id}/cook/finish", response_class=HTMLResponse, include_in_schema=False)
    def cook_finish(request: Request, recipe_id: str, preference: str = Form(...)) -> HTMLResponse:
        try:
            recipe = store.set_preference(recipe_id, Preference(preference))
        except RecipeNotFound:
            return templates.TemplateResponse(
                request, "recipe_not_found.html", {"recipe_id": recipe_id, "nav_active": "library"}, status_code=404
            )

        plan = plan_store.get_current()
        if plan is not None:
            meal = next((m for m in plan.meals if m.recipe_id == recipe_id), None)
            if meal is not None and not meal.cooked:
                plan_store.set_cooked(plan.id, meal.id, True)

        return templates.TemplateResponse(request, "cook_finish.html", {"recipe": recipe, "feedback": preference})

    @router.post("/recipes/{recipe_id}/preference", response_class=HTMLResponse, include_in_schema=False)
    def recipe_preference_toggle(request: Request, recipe_id: str, preference: str = Form(...)) -> HTMLResponse:
        recipe = store.set_preference(recipe_id, Preference(preference))
        return templates.TemplateResponse(request, "partials/_recipe_row.html", {"recipe": recipe})

    @router.post("/recipes/{recipe_id}/delete", include_in_schema=False)
    def recipe_delete(recipe_id: str) -> RedirectResponse:
        try:
            store.delete(recipe_id)
        except RecipeNotFound:
            pass
        return RedirectResponse(url="/recipes", status_code=303)

    @router.get("/settings", response_class=HTMLResponse, include_in_schema=False)
    def settings_form(request: Request) -> HTMLResponse:
        preferences = household_store.get()
        return templates.TemplateResponse(
            request,
            "settings.html",
            {"preferences": preferences, "days": list(DayOfWeek), "error": None, "saved": False, "nav_active": "settings"},
        )

    @router.post("/settings", response_class=HTMLResponse, include_in_schema=False)
    def settings_submit(
        request: Request,
        recipes_per_week: int = Form(...),
        recommendation_day: str = Form(...),
        recommendation_time: str = Form(...),
        food_preferences: str = Form(""),
        ai_suggestions_per_plan: int = Form(...),
        default_servings: str = Form(...),
    ) -> HTMLResponse:
        try:
            update = HouseholdPreferencesUpdate(
                recipes_per_week=recipes_per_week,
                recommendation_day=DayOfWeek(recommendation_day),
                recommendation_time=time.fromisoformat(recommendation_time),
                food_preferences=_parse_food_preferences(food_preferences),
                ai_suggestions_per_plan=ai_suggestions_per_plan,
                default_servings=default_servings,
            )
        except (ValidationError, ValueError) as exc:
            preferences = household_store.get()
            return templates.TemplateResponse(
                request,
                "settings.html",
                {
                    "preferences": preferences,
                    "days": list(DayOfWeek),
                    "error": str(exc),
                    "saved": False,
                    "nav_active": "settings",
                },
                status_code=422,
            )

        preferences = household_store.put(update)
        return templates.TemplateResponse(
            request,
            "settings.html",
            {"preferences": preferences, "days": list(DayOfWeek), "error": None, "saved": True, "nav_active": "settings"},
        )

    @router.get("/plan", response_class=HTMLResponse, include_in_schema=False)
    def plan_view(request: Request) -> HTMLResponse:
        return _render_plan(request)

    @router.post("/plan/generate", include_in_schema=False)
    def plan_generate() -> RedirectResponse:
        plan_store.create(_build_meals())
        return RedirectResponse(url="/plan", status_code=303)

    @router.post("/plan/reroll", include_in_schema=False)
    def plan_reroll_whole() -> RedirectResponse:
        plan = plan_store.get_current()
        if plan is not None and not plan.finalized:
            plan_store.replace_meals(plan.id, _build_meals())
        return RedirectResponse(url="/plan", status_code=303)

    @router.post("/plan/meals/{meal_id}/servings", response_class=HTMLResponse, include_in_schema=False)
    def plan_meal_servings(request: Request, meal_id: str, servings: int = Form(...)) -> HTMLResponse:
        plan = plan_store.get_current()
        if plan is None:
            return RedirectResponse(url="/plan", status_code=303)
        try:
            plan = plan_store.set_servings(plan.id, meal_id, max(1, servings))
        except (PlanNotFound, PlanMealNotFound):
            return RedirectResponse(url="/plan", status_code=303)
        return _render_plan_meal(request, templates, plan, meal_id, store)

    @router.post("/plan/meals/{meal_id}/cooked", response_class=HTMLResponse, include_in_schema=False)
    def plan_meal_cooked(request: Request, meal_id: str, cooked: str = Form(...)) -> HTMLResponse:
        plan = plan_store.get_current()
        if plan is None:
            return RedirectResponse(url="/plan", status_code=303)
        try:
            plan = plan_store.set_cooked(plan.id, meal_id, cooked == "true")
        except (PlanNotFound, PlanMealNotFound):
            return RedirectResponse(url="/plan", status_code=303)
        return _render_plan_meal(request, templates, plan, meal_id, store)

    @router.post("/plan/meals/{meal_id}/preference", response_class=HTMLResponse, include_in_schema=False)
    def plan_meal_preference(request: Request, meal_id: str, preference: str = Form(...)) -> HTMLResponse:
        plan = plan_store.get_current()
        if plan is None:
            return RedirectResponse(url="/plan", status_code=303)
        meal = next((m for m in plan.meals if m.id == meal_id), None)
        if meal is None:
            return RedirectResponse(url="/plan", status_code=303)
        store.set_preference(meal.recipe_id, Preference(preference))
        return _render_plan_meal(request, templates, plan, meal_id, store)

    @router.post("/plan/meals/{meal_id}/reroll", response_class=HTMLResponse, include_in_schema=False)
    def plan_meal_reroll(request: Request, meal_id: str) -> HTMLResponse:
        plan = plan_store.get_current()
        if plan is None or plan.finalized:
            return RedirectResponse(url="/plan", status_code=303)
        preferences = household_store.get()
        recipes = store.list()
        excluded = {meal.recipe_id for meal in plan.meals}
        replacement = generate_single_replacement(excluded, recipes, store, extractor, search_provider, preferences)
        if replacement is None:
            return _render_plan(request)
        try:
            plan = plan_store.set_recipe(plan.id, meal_id, replacement.recipe.id, replacement.servings, replacement.is_suggestion)
        except (PlanNotFound, PlanMealNotFound):
            return RedirectResponse(url="/plan", status_code=303)
        return _render_plan_meal(request, templates, plan, meal_id, store)

    @router.get("/plan/meals/{meal_id}/alternatives", response_class=HTMLResponse, include_in_schema=False)
    def plan_meal_alternatives(request: Request, meal_id: str) -> HTMLResponse:
        plan = plan_store.get_current()
        if plan is None:
            return RedirectResponse(url="/plan", status_code=303)
        meal = next((m for m in plan.meals if m.id == meal_id), None)
        if meal is None:
            return RedirectResponse(url="/plan", status_code=303)
        excluded = {m.recipe_id for m in plan.meals}
        candidates = list_controlled_reroll_candidates(excluded, store.list())
        current_recipe = store.get(meal.recipe_id)
        return templates.TemplateResponse(
            request,
            "reroll_picker.html",
            {"meal_id": meal_id, "current_recipe": current_recipe, "candidates": candidates, "nav_active": "plan"},
        )

    @router.post("/plan/meals/{meal_id}/choose", include_in_schema=False)
    def plan_meal_choose(meal_id: str, recipe_id: str = Form(...)) -> RedirectResponse:
        plan = plan_store.get_current()
        if plan is None or plan.finalized:
            return RedirectResponse(url="/plan", status_code=303)
        try:
            recipe = store.get(recipe_id)
        except RecipeNotFound:
            return RedirectResponse(url="/plan", status_code=303)
        try:
            plan_store.set_recipe(plan.id, meal_id, recipe.id, recipe.servings, is_suggestion=False)
        except (PlanNotFound, PlanMealNotFound):
            pass
        return RedirectResponse(url="/plan", status_code=303)

    @router.post("/plan/finalize", include_in_schema=False)
    def plan_finalize() -> RedirectResponse:
        plan = plan_store.get_current()
        if plan is not None:
            plan_store.finalize(plan.id)
        return RedirectResponse(url="/plan", status_code=303)

    @router.get("/shopping", response_class=HTMLResponse, include_in_schema=False)
    def shopping_view(request: Request) -> HTMLResponse:
        plan = plan_store.get_current()
        shopping_list = None
        if plan is not None and plan.finalized:
            shopping_list = shopping_list_store.get_for_plan(plan.id)
        return templates.TemplateResponse(
            request,
            "shopping.html",
            {"plan": plan, "shopping_list": shopping_list, "nav_active": "shopping"},
        )

    @router.post("/shopping/generate", include_in_schema=False)
    def shopping_generate() -> RedirectResponse:
        plan = plan_store.get_current()
        if plan is not None and plan.finalized and shopping_list_store.get_for_plan(plan.id) is None:
            items = build_shopping_list_items(plan, store)
            shopping_list_store.create(plan.id, items)
        return RedirectResponse(url="/shopping", status_code=303)

    @router.post("/shopping/items/{item_id}/checked", response_class=HTMLResponse, include_in_schema=False)
    def shopping_item_checked(request: Request, item_id: str, checked: str = Form(...)) -> HTMLResponse:
        plan = plan_store.get_current()
        if plan is None:
            return RedirectResponse(url="/shopping", status_code=303)
        shopping_list = shopping_list_store.get_for_plan(plan.id)
        if shopping_list is None:
            return RedirectResponse(url="/shopping", status_code=303)
        try:
            shopping_list = shopping_list_store.set_item_checked(shopping_list.id, item_id, checked == "true")
        except (ShoppingListNotFound, ShoppingListItemNotFound):
            return RedirectResponse(url="/shopping", status_code=303)
        item = next(i for i in shopping_list.items if i.id == item_id)
        return templates.TemplateResponse(request, "partials/_shopping_item.html", {"item": item})

    @router.post("/shopping/cost", include_in_schema=False)
    def shopping_cost(actual_cost: float = Form(...)) -> RedirectResponse:
        plan = plan_store.get_current()
        if plan is not None:
            shopping_list = shopping_list_store.get_for_plan(plan.id)
            if shopping_list is not None and actual_cost >= 0:
                shopping_list_store.set_actual_cost(shopping_list.id, actual_cost)
        return RedirectResponse(url="/shopping", status_code=303)

    return router


def _render_plan_meal(
    request: Request, templates: Jinja2Templates, plan: MealPlan, meal_id: str, store: RecipeStore
) -> HTMLResponse:
    meal = next(m for m in plan.meals if m.id == meal_id)
    recipe = store.get(meal.recipe_id)
    return templates.TemplateResponse(request, "partials/_plan_meal.html", {"plan": plan, "meal": meal, "recipe": recipe})


def _parse_food_preferences(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]
