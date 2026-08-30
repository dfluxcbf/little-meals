from __future__ import annotations

from datetime import datetime, time, timezone
from typing import Optional

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from little_meals.llm.extraction import ExtractionError, RecipeExtractionService
from little_meals.llm.ollama_client import OllamaUnavailable
from little_meals.models import DayOfWeek, HouseholdPreferencesUpdate, MealPlan, Preference, Recipe
from little_meals.planning.plan_builder import build_meal_specs, generate_single_replacement, list_controlled_reroll_candidates
from little_meals.planning.shopping_list import build_shopping_list_items
from little_meals.planning.spoonacular_fields import (
    FILTER_SECTIONS,
    MACRONUTRIENTS,
    VITAMINS_AND_MINERALS,
    filter_to_display,
    form_to_display,
    parse_filter_form,
)
from little_meals.planning.suggestion import SearchProvider, build_complex_search_params
from little_meals.store.cook_along_store import CookAlongStore
from little_meals.store.household_store import HouseholdPreferencesStore
from little_meals.store.notification_store import NotificationStore
from little_meals.store.plan_store import MealPlanStore, PlanMealNotFound, PlanNotFound
from little_meals.store.recipe_store import RecipeNotFound, RecipeStore
from little_meals.store.shopping_list_store import ShoppingListItemNotFound, ShoppingListNotFound, ShoppingListStore


def build_ui_router(
    store: RecipeStore,
    extractor: RecipeExtractionService,
    household_store: HouseholdPreferencesStore,
    plan_store: MealPlanStore,
    search_provider: SearchProvider,
    shopping_list_store: ShoppingListStore,
    notification_store: NotificationStore,
    cook_along_store: CookAlongStore,
    templates: Jinja2Templates,
) -> APIRouter:
    router = APIRouter()

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
            request,
            "plan.html",
            {"plan": plan, "meals": meals, "nav_active": "plan", "notification_pending": notification_store.is_pending()},
        )

    @router.get("/", include_in_schema=False)
    def index() -> RedirectResponse:
        return RedirectResponse(url="/recipes", status_code=303)

    @router.get("/recipes", response_class=HTMLResponse, include_in_schema=False)
    def recipes_list(request: Request) -> HTMLResponse:
        recipes = store.list(extractor)
        return templates.TemplateResponse(
            request,
            "recipes_list.html",
            {"recipes": recipes, "nav_active": "library", "notification_pending": notification_store.is_pending()},
        )

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

    @router.get("/recipes/{recipe_id}/cook", response_class=HTMLResponse, include_in_schema=False)
    def cook_start(request: Request, recipe_id: str):
        try:
            recipe = store.get(recipe_id)
        except RecipeNotFound:
            return templates.TemplateResponse(
                request, "recipe_not_found.html", {"recipe_id": recipe_id, "nav_active": "library"}, status_code=404
            )

        existing = cook_along_store.get(recipe_id)
        if existing is not None:
            return templates.TemplateResponse(request, "cook_resume.html", {"recipe": recipe, "session": existing})

        cook_along_store.start(recipe_id)
        return RedirectResponse(url=f"/recipes/{recipe_id}/cook/0", status_code=303)

    @router.post("/recipes/{recipe_id}/cook/start-over", include_in_schema=False)
    def cook_start_over(recipe_id: str) -> RedirectResponse:
        cook_along_store.start(recipe_id)
        return RedirectResponse(url=f"/recipes/{recipe_id}/cook/0", status_code=303)

    @router.get("/recipes/{recipe_id}/cook/{step_number}", response_class=HTMLResponse, include_in_schema=False)
    def cook_step(request: Request, recipe_id: str, step_number: int) -> HTMLResponse:
        try:
            recipe = store.get(recipe_id)
        except RecipeNotFound:
            return templates.TemplateResponse(
                request, "recipe_not_found.html", {"recipe_id": recipe_id, "nav_active": "library"}, status_code=404
            )

        total_steps = len(recipe.steps)
        if step_number < 0:
            return RedirectResponse(url=f"/recipes/{recipe_id}/cook/0", status_code=303)
        if step_number > total_steps:
            # Ran past the last step (or there were no steps to begin with) -
            # the guided walkthrough is done, prompt for the cooked/uncooked choice.
            return templates.TemplateResponse(request, "cook_finish.html", {"recipe": recipe, "result": None})

        session = cook_along_store.save_step(recipe_id, step_number)

        if step_number == 0:
            return templates.TemplateResponse(
                request,
                "cook_ingredients.html",
                {"recipe": recipe, "total_steps": total_steps, "checked": set(session.checked_ingredients)},
            )

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

    @router.post(
        "/recipes/{recipe_id}/cook/ingredients/{index}/checked", response_class=HTMLResponse, include_in_schema=False
    )
    def cook_ingredient_toggle(request: Request, recipe_id: str, index: int) -> HTMLResponse:
        try:
            recipe = store.get(recipe_id)
        except RecipeNotFound:
            return templates.TemplateResponse(
                request, "recipe_not_found.html", {"recipe_id": recipe_id, "nav_active": "library"}, status_code=404
            )
        session = cook_along_store.toggle_ingredient(recipe_id, index)
        ingredient = recipe.ingredients[index]
        return templates.TemplateResponse(
            request,
            "partials/_cook_ingredient.html",
            {
                "recipe": recipe,
                "ingredient": ingredient,
                "index": index,
                "checked": index in session.checked_ingredients,
            },
        )

    @router.post("/recipes/{recipe_id}/cook/finish", response_class=HTMLResponse, include_in_schema=False)
    def cook_finish(request: Request, recipe_id: str, action: str = Form(...)) -> HTMLResponse:
        try:
            recipe = store.get(recipe_id)
        except RecipeNotFound:
            return templates.TemplateResponse(
                request, "recipe_not_found.html", {"recipe_id": recipe_id, "nav_active": "library"}, status_code=404
            )

        if action == "cooked":
            plan = plan_store.get_current()
            if plan is not None:
                meal = next((m for m in plan.meals if m.recipe_id == recipe_id), None)
                if meal is not None and not meal.cooked:
                    plan_store.set_cooked(plan.id, meal.id, True)

        cook_along_store.delete(recipe_id)
        return templates.TemplateResponse(request, "cook_finish.html", {"recipe": recipe, "result": action})

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

    def _settings_context(
        preferences,
        *,
        error: Optional[str] = None,
        saved: bool = False,
    ) -> dict:
        return {
            "preferences": preferences,
            "days": list(DayOfWeek),
            "error": error,
            "saved": saved,
            "nav_active": "settings",
        }

    @router.get("/settings", response_class=HTMLResponse, include_in_schema=False)
    def settings_form(request: Request) -> HTMLResponse:
        preferences = household_store.get()
        return templates.TemplateResponse(request, "settings.html", _settings_context(preferences))

    @router.post("/settings", response_class=HTMLResponse, include_in_schema=False)
    def settings_submit(
        request: Request,
        recipes_per_week: int = Form(...),
        recommendation_day: str = Form(...),
        recommendation_time: str = Form(...),
        ai_suggestions_per_plan: int = Form(...),
        default_servings: str = Form(...),
        food_preferences_text: str = Form(""),
    ) -> HTMLResponse:
        try:
            update = HouseholdPreferencesUpdate(
                recipes_per_week=recipes_per_week,
                recommendation_day=DayOfWeek(recommendation_day),
                recommendation_time=time.fromisoformat(recommendation_time),
                ai_suggestions_per_plan=ai_suggestions_per_plan,
                default_servings=default_servings,
                food_preferences_text=food_preferences_text,
            )
        except (ValidationError, ValueError) as exc:
            preferences = household_store.get()
            return templates.TemplateResponse(
                request,
                "settings.html",
                _settings_context(preferences, error=str(exc)),
                status_code=422,
            )

        preferences = household_store.put(update)
        return templates.TemplateResponse(request, "settings.html", _settings_context(preferences, saved=True))

    def _recipe_preferences_context(
        preferences,
        *,
        error: Optional[str] = None,
        errors: Optional[list[str]] = None,
        saved: bool = False,
        display: Optional[dict] = None,
    ) -> dict:
        return {
            "preferences": preferences,
            "sections": FILTER_SECTIONS,
            "macronutrients": MACRONUTRIENTS,
            "vitamins_and_minerals": VITAMINS_AND_MINERALS,
            "display": display if display is not None else filter_to_display(preferences.food_filter),
            "error": error,
            "errors": errors or [],
            "saved": saved,
            "spoonacular_query_preview": (
                build_complex_search_params(preferences.food_filter) if preferences.food_filter else None
            ),
            "nav_active": "settings",
        }

    @router.get("/settings/recipe-preferences", response_class=HTMLResponse, include_in_schema=False)
    def recipe_preferences_form(request: Request) -> HTMLResponse:
        preferences = household_store.get()
        return templates.TemplateResponse(
            request, "recipe_preferences.html", _recipe_preferences_context(preferences)
        )

    @router.post("/settings/recipe-preferences", response_class=HTMLResponse, include_in_schema=False)
    async def recipe_preferences_submit(request: Request) -> HTMLResponse:
        form = await request.form()
        food_filter, errors = parse_filter_form(form)
        preferences = household_store.get()
        if errors:
            return templates.TemplateResponse(
                request,
                "recipe_preferences.html",
                _recipe_preferences_context(
                    preferences,
                    error="Could not save recipe search preferences.",
                    errors=errors,
                    display=form_to_display(form),
                ),
                status_code=422,
            )

        preferences = household_store.save_food_filter(food_filter)
        return templates.TemplateResponse(
            request, "recipe_preferences.html", _recipe_preferences_context(preferences, saved=True)
        )

    @router.get("/plan", response_class=HTMLResponse, include_in_schema=False)
    def plan_view(request: Request) -> HTMLResponse:
        notification_store.clear()
        return _render_plan(request)

    @router.post("/plan/generate", include_in_schema=False)
    def plan_generate() -> RedirectResponse:
        plan_store.create(build_meal_specs(store, household_store, extractor, search_provider))
        return RedirectResponse(url="/plan", status_code=303)

    @router.post("/plan/reroll", include_in_schema=False)
    def plan_reroll_whole() -> RedirectResponse:
        plan = plan_store.get_current()
        if plan is not None and not plan.finalized:
            plan_store.replace_meals(plan.id, build_meal_specs(store, household_store, extractor, search_provider))
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
        recipes = store.list(extractor)
        excluded = {meal.recipe_id for meal in plan.meals}
        replacement = generate_single_replacement(excluded, recipes, store, extractor, search_provider, preferences)
        if replacement is None:
            return _render_plan(request)
        try:
            plan = plan_store.set_recipe(
                plan.id,
                meal_id,
                replacement.recipe.id,
                replacement.servings,
                replacement.is_suggestion,
                tuple(replacement.candidate_recipe_ids),
            )
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
        candidates = list_controlled_reroll_candidates(excluded, store.list(extractor))
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

    @router.get("/plan/meals/{meal_id}/suggestions", response_class=HTMLResponse, include_in_schema=False)
    def plan_meal_suggestions(request: Request, meal_id: str) -> HTMLResponse:
        plan = plan_store.get_current()
        if plan is None:
            return RedirectResponse(url="/plan", status_code=303)
        meal = next((m for m in plan.meals if m.id == meal_id), None)
        if meal is None:
            return RedirectResponse(url="/plan", status_code=303)
        candidate_ids = [rid for rid in plan_store.get_candidates(plan.id, meal_id) if rid != meal.recipe_id]
        candidates = []
        for rid in candidate_ids:
            try:
                candidates.append(store.get(rid))
            except RecipeNotFound:
                continue
        current_recipe = store.get(meal.recipe_id)
        return templates.TemplateResponse(
            request,
            "suggestion_picker.html",
            {"meal_id": meal_id, "current_recipe": current_recipe, "candidates": candidates, "nav_active": "plan"},
        )

    @router.post("/plan/meals/{meal_id}/choose-suggestion", include_in_schema=False)
    def plan_meal_choose_suggestion(meal_id: str, recipe_id: str = Form(...)) -> RedirectResponse:
        plan = plan_store.get_current()
        if plan is None or plan.finalized:
            return RedirectResponse(url="/plan", status_code=303)
        candidate_ids = plan_store.get_candidates(plan.id, meal_id)
        if recipe_id not in candidate_ids:
            return RedirectResponse(url="/plan", status_code=303)
        try:
            recipe = store.get(recipe_id)
        except RecipeNotFound:
            return RedirectResponse(url="/plan", status_code=303)
        try:
            plan_store.set_recipe(
                plan.id, meal_id, recipe.id, recipe.servings, is_suggestion=True, candidate_recipe_ids=tuple(candidate_ids)
            )
        except (PlanNotFound, PlanMealNotFound):
            pass
        return RedirectResponse(url="/plan", status_code=303)

    @router.post("/plan/finalize", include_in_schema=False)
    def plan_finalize() -> RedirectResponse:
        plan = plan_store.get_current()
        if plan is not None:
            plan_store.finalize(plan.id)
        return RedirectResponse(url="/plan", status_code=303)

    @router.post("/plan/cancel", include_in_schema=False)
    def plan_cancel() -> RedirectResponse:
        plan = plan_store.get_current()
        if plan is not None:
            shopping_list_store.delete_for_plan(plan.id)
            plan_store.delete(plan.id)
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

    @router.get("/shopping/items/{item_id}/substitutes", response_class=HTMLResponse, include_in_schema=False)
    def shopping_item_substitutes(request: Request, item_id: str) -> HTMLResponse:
        plan = plan_store.get_current()
        if plan is None:
            return HTMLResponse("")
        shopping_list = shopping_list_store.get_for_plan(plan.id)
        if shopping_list is None:
            return HTMLResponse("")
        item = next((i for i in shopping_list.items if i.id == item_id), None)
        if item is None:
            return HTMLResponse("")
        result = search_provider.get_substitutes(item.name)
        return templates.TemplateResponse(request, "partials/_shopping_substitutes.html", {"item_id": item_id, "result": result})

    @router.post("/shopping/cost", include_in_schema=False)
    def shopping_cost(actual_cost: str = Form("")) -> RedirectResponse:
        # The field is optional in the UI (no cost yet is a normal state,
        # not an error) - only a non-blank, valid, non-negative amount is
        # saved; anything else is left as-is rather than raising a 422 on
        # what amounts to submitting the form with nothing entered.
        plan = plan_store.get_current()
        if plan is not None and actual_cost.strip():
            shopping_list = shopping_list_store.get_for_plan(plan.id)
            if shopping_list is not None:
                try:
                    cost = float(actual_cost)
                except ValueError:
                    cost = None
                if cost is not None and cost >= 0:
                    shopping_list_store.set_actual_cost(shopping_list.id, cost)
        return RedirectResponse(url="/shopping", status_code=303)

    return router


def _render_plan_meal(
    request: Request, templates: Jinja2Templates, plan: MealPlan, meal_id: str, store: RecipeStore
) -> HTMLResponse:
    meal = next(m for m in plan.meals if m.id == meal_id)
    recipe = store.get(meal.recipe_id)
    return templates.TemplateResponse(request, "partials/_plan_meal.html", {"plan": plan, "meal": meal, "recipe": recipe})
