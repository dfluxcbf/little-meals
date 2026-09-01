from __future__ import annotations

from datetime import datetime, time, timezone
from typing import Optional

from fastapi import APIRouter, Form, Query, Request
from fastapi.datastructures import FormData
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ValidationError

from little_meals.models import Classification, DayOfWeek, Difficulty, HouseholdPreferencesUpdate, Ingredient, MealPlan, Recipe, RecipeCreate, RecipeUpdate
from little_meals.planning.plan_builder import build_meal_specs, generate_single_replacement, list_controlled_reroll_candidates
from little_meals.planning.recipe_filters import RecipeFilter, SortDirection, SortField, filter_recipes, sort_recipes
from little_meals.planning.shopping_list import build_shopping_list_items
from little_meals.store.cook_along_store import CookAlongStore
from little_meals.store.household_store import HouseholdPreferencesStore
from little_meals.store.notification_store import NotificationStore
from little_meals.store.plan_store import MealPlanStore, MealSpec, PlanMealNotFound, PlanNotFound
from little_meals.store.recipe_store import RecipeNotFound, RecipeStore
from little_meals.store.shopping_list_store import ShoppingListItemNotFound, ShoppingListNotFound, ShoppingListStore


def build_ui_router(
    store: RecipeStore,
    household_store: HouseholdPreferencesStore,
    plan_store: MealPlanStore,
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
        all_cooked = bool(plan is not None and plan.finalized and meals and all(item["meal"].cooked for item in meals))
        library_has_recipes = bool(store.list()) if plan is not None and not meals else True
        return templates.TemplateResponse(
            request,
            "plan.html",
            {
                "plan": plan,
                "meals": meals,
                "all_cooked": all_cooked,
                "library_has_recipes": library_has_recipes,
                "nav_active": "plan",
                "notification_pending": notification_store.is_pending(),
            },
        )

    @router.get("/", include_in_schema=False)
    def index() -> RedirectResponse:
        return RedirectResponse(url="/recipes", status_code=303)

    @router.get("/recipes", response_class=HTMLResponse, include_in_schema=False)
    def recipes_list(
        request: Request,
        min_calories: Optional[str] = None,
        max_calories: Optional[str] = None,
        min_protein: Optional[str] = None,
        max_protein: Optional[str] = None,
        min_fiber: Optional[str] = None,
        max_fiber: Optional[str] = None,
        min_cook_time: Optional[str] = None,
        max_cook_time: Optional[str] = None,
        classification: list[str] = Query(default=[]),
        difficulty: list[str] = Query(default=[]),
        sort_by: str = "name",
        sort_dir: str = "asc",
    ) -> HTMLResponse:
        # A blank number field submits as an empty string, not an absent
        # param - FastAPI's int/float coercion rejects that outright (a 422
        # for the whole page) rather than treating it as "no bound set", so
        # these arrive as raw strings and get parsed leniently here instead.
        min_calories = _parse_optional_int(min_calories)
        max_calories = _parse_optional_int(max_calories)
        min_protein = _parse_optional_float(min_protein)
        max_protein = _parse_optional_float(max_protein)
        min_fiber = _parse_optional_float(min_fiber)
        max_fiber = _parse_optional_float(max_fiber)
        min_cook_time = _parse_optional_int(min_cook_time)
        max_cook_time = _parse_optional_int(max_cook_time)

        classifications = _parse_enum_set(Classification, classification)
        difficulties = _parse_enum_set(Difficulty, difficulty)
        criteria = RecipeFilter(
            min_calories=min_calories,
            max_calories=max_calories,
            min_protein=min_protein,
            max_protein=max_protein,
            min_fiber=min_fiber,
            max_fiber=max_fiber,
            min_cook_time=min_cook_time,
            max_cook_time=max_cook_time,
            classifications=classifications,
            difficulties=difficulties,
        )
        sort_field = _parse_enum(SortField, sort_by, SortField.NAME)
        sort_direction = _parse_enum(SortDirection, sort_dir, SortDirection.ASC)

        all_recipes = store.list()
        recipes = filter_recipes(all_recipes, criteria)
        recipes = sort_recipes(recipes, sort_field, sort_direction)

        current_plan = plan_store.get_current()
        plan_recipe_ids = {meal.recipe_id for meal in current_plan.meals} if current_plan is not None else set()

        active_filter_count = sum(
            [
                min_calories is not None,
                max_calories is not None,
                min_protein is not None,
                max_protein is not None,
                min_fiber is not None,
                max_fiber is not None,
                min_cook_time is not None,
                max_cook_time is not None,
                bool(classifications),
                bool(difficulties),
            ]
        )
        return templates.TemplateResponse(
            request,
            "recipes_list.html",
            {
                "recipes": recipes,
                "nav_active": "library",
                "notification_pending": notification_store.is_pending(),
                "library_is_empty": not all_recipes,
                "plan_recipe_ids": plan_recipe_ids,
                "filters": {
                    "min_calories": min_calories,
                    "max_calories": max_calories,
                    "min_protein": min_protein,
                    "max_protein": max_protein,
                    "min_fiber": min_fiber,
                    "max_fiber": max_fiber,
                    "min_cook_time": min_cook_time,
                    "max_cook_time": max_cook_time,
                    "classification": {c.value for c in classifications},
                    "difficulty": {d.value for d in difficulties},
                    "sort_by": sort_field.value,
                    "sort_dir": sort_direction.value,
                },
                "active_filter_count": active_filter_count,
                "classifications": list(Classification),
                "difficulties": list(Difficulty),
                "sort_fields": list(SortField),
            },
        )

    @router.get("/recipes/new", response_class=HTMLResponse, include_in_schema=False)
    def recipe_new_form(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request, "recipe_edit.html", _recipe_edit_context(mode="new", values=_empty_recipe_values())
        )

    @router.post("/recipes/new", response_class=HTMLResponse, include_in_schema=False)
    async def recipe_new_submit(request: Request) -> HTMLResponse:
        form = await request.form()
        try:
            payload = _parse_recipe_form(form, RecipeCreate)
        except (ValidationError, ValueError) as exc:
            return templates.TemplateResponse(
                request,
                "recipe_edit.html",
                _recipe_edit_context(mode="new", values=_recipe_values_from_form(form), error=str(exc)),
                status_code=422,
            )

        now = datetime.now(timezone.utc)
        recipe = Recipe(
            id="",
            source_text=None,
            created_at=now,
            updated_at=now,
            **payload.model_dump(),
        )
        stored = store.create(recipe)
        return RedirectResponse(url=f"/recipes/{stored.id}", status_code=303)

    @router.get("/recipes/{recipe_id}/edit", response_class=HTMLResponse, include_in_schema=False)
    def recipe_edit_form(request: Request, recipe_id: str) -> HTMLResponse:
        try:
            recipe = store.get(recipe_id)
        except RecipeNotFound:
            return templates.TemplateResponse(
                request, "recipe_not_found.html", {"recipe_id": recipe_id, "nav_active": "library"}, status_code=404
            )
        return templates.TemplateResponse(
            request,
            "recipe_edit.html",
            _recipe_edit_context(mode="edit", values=_recipe_values_from_recipe(recipe), recipe_id=recipe_id),
        )

    @router.post("/recipes/{recipe_id}/edit", response_class=HTMLResponse, include_in_schema=False)
    async def recipe_edit_submit(request: Request, recipe_id: str) -> HTMLResponse:
        form = await request.form()
        try:
            payload = _parse_recipe_form(form, RecipeUpdate)
        except (ValidationError, ValueError) as exc:
            return templates.TemplateResponse(
                request,
                "recipe_edit.html",
                _recipe_edit_context(
                    mode="edit", values=_recipe_values_from_form(form), error=str(exc), recipe_id=recipe_id
                ),
                status_code=422,
            )

        now = datetime.now(timezone.utc)
        recipe = Recipe(
            id=recipe_id,
            source_text=None,
            created_at=now,
            updated_at=now,
            **payload.model_dump(),
        )
        try:
            store.update(recipe_id, recipe)
        except RecipeNotFound:
            return templates.TemplateResponse(
                request, "recipe_not_found.html", {"recipe_id": recipe_id, "nav_active": "library"}, status_code=404
            )
        return RedirectResponse(url=f"/recipes/{recipe_id}", status_code=303)

    @router.post("/recipes/{recipe_id}/duplicate", include_in_schema=False)
    def recipe_duplicate(recipe_id: str) -> RedirectResponse:
        try:
            original = store.get(recipe_id)
        except RecipeNotFound:
            return RedirectResponse(url="/recipes", status_code=303)
        now = datetime.now(timezone.utc)
        duplicate = original.model_copy(
            update={"id": "", "name": f"{original.name} (copy)", "created_at": now, "updated_at": now}
        )
        stored = store.create(duplicate)
        return RedirectResponse(url=f"/recipes/{stored.id}/edit", status_code=303)

    def _recipe_row_response(request: Request, recipe: Recipe, *, swipe_blocked: bool = False, status_code: int = 200) -> HTMLResponse:
        plan = plan_store.get_current()
        plan_recipe_ids = {meal.recipe_id for meal in plan.meals} if plan is not None else set()
        return templates.TemplateResponse(
            request,
            "partials/_recipe_row.html",
            {"recipe": recipe, "plan_recipe_ids": plan_recipe_ids, "swipe_blocked": swipe_blocked},
            status_code=status_code,
        )

    @router.post("/recipes/{recipe_id}/add-to-plan", response_class=HTMLResponse, include_in_schema=False)
    def recipe_add_to_plan(request: Request, recipe_id: str) -> HTMLResponse:
        try:
            recipe = store.get(recipe_id)
        except RecipeNotFound:
            return templates.TemplateResponse(
                request, "recipe_not_found.html", {"recipe_id": recipe_id, "nav_active": "library"}, status_code=404
            )

        plan = plan_store.get_current()
        if plan is not None and plan.finalized:
            return _recipe_row_response(request, recipe, swipe_blocked=True, status_code=409)

        already_in_plan = plan is not None and any(meal.recipe_id == recipe_id for meal in plan.meals)
        if not already_in_plan:
            if plan is None:
                plan_store.create([MealSpec(recipe.id, recipe.servings)])
            else:
                plan_store.add_meal(plan.id, recipe.id, recipe.servings)

        return _recipe_row_response(request, recipe)

    @router.post("/recipes/{recipe_id}/remove-from-plan", response_class=HTMLResponse, include_in_schema=False)
    def recipe_remove_from_plan(request: Request, recipe_id: str) -> HTMLResponse:
        try:
            recipe = store.get(recipe_id)
        except RecipeNotFound:
            return templates.TemplateResponse(
                request, "recipe_not_found.html", {"recipe_id": recipe_id, "nav_active": "library"}, status_code=404
            )

        plan = plan_store.get_current()
        if plan is not None and plan.finalized:
            return _recipe_row_response(request, recipe, swipe_blocked=True, status_code=409)

        if plan is not None:
            meal = next((m for m in plan.meals if m.recipe_id == recipe_id), None)
            if meal is not None:
                plan_store.remove_meal(plan.id, meal.id)

        return _recipe_row_response(request, recipe)

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
        recommendation_enabled: Optional[str] = Form(None),
        recommendation_day: str = Form(...),
        recommendation_time: str = Form(...),
        auto_confirm_enabled: Optional[str] = Form(None),
        auto_confirm_day: str = Form(...),
        auto_confirm_time: str = Form(...),
        default_servings: str = Form(...),
    ) -> HTMLResponse:
        try:
            update = HouseholdPreferencesUpdate(
                recipes_per_week=recipes_per_week,
                recommendation_enabled=recommendation_enabled is not None,
                recommendation_day=DayOfWeek(recommendation_day),
                recommendation_time=time.fromisoformat(recommendation_time),
                auto_confirm_enabled=auto_confirm_enabled is not None,
                auto_confirm_day=DayOfWeek(auto_confirm_day),
                auto_confirm_time=time.fromisoformat(auto_confirm_time),
                default_servings=default_servings,
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

    @router.get("/plan", response_class=HTMLResponse, include_in_schema=False)
    def plan_view(request: Request) -> HTMLResponse:
        notification_store.clear()
        return _render_plan(request)

    @router.post("/plan/generate", include_in_schema=False)
    def plan_generate() -> RedirectResponse:
        plan_store.create(build_meal_specs(store, household_store))
        return RedirectResponse(url="/plan", status_code=303)

    @router.post("/plan/reroll", include_in_schema=False)
    def plan_reroll_whole() -> RedirectResponse:
        plan = plan_store.get_current()
        if plan is not None and not plan.finalized:
            plan_store.replace_meals(plan.id, build_meal_specs(store, household_store))
        return RedirectResponse(url="/plan", status_code=303)

    @router.post("/plan/meals/add", include_in_schema=False)
    def plan_meal_add() -> RedirectResponse:
        plan = plan_store.get_current()
        if plan is not None and not plan.finalized:
            recipes = store.list()
            excluded = {meal.recipe_id for meal in plan.meals}
            replacement = generate_single_replacement(excluded, recipes)
            if replacement is not None:
                plan_store.add_meal(plan.id, replacement.recipe.id, replacement.servings)
        return RedirectResponse(url="/plan", status_code=303)

    @router.post("/plan/meals/{meal_id}/remove", include_in_schema=False)
    def plan_meal_remove(meal_id: str) -> RedirectResponse:
        plan = plan_store.get_current()
        if plan is not None and not plan.finalized:
            try:
                plan_store.remove_meal(plan.id, meal_id)
            except (PlanNotFound, PlanMealNotFound):
                pass
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
        if plan is None or not plan.finalized:
            return RedirectResponse(url="/plan", status_code=303)
        try:
            plan = plan_store.set_cooked(plan.id, meal_id, cooked == "true")
        except (PlanNotFound, PlanMealNotFound):
            return RedirectResponse(url="/plan", status_code=303)
        return _render_plan_meal(request, templates, plan, meal_id, store)

    @router.post("/plan/meals/{meal_id}/reroll", response_class=HTMLResponse, include_in_schema=False)
    def plan_meal_reroll(request: Request, meal_id: str) -> HTMLResponse:
        plan = plan_store.get_current()
        if plan is None or plan.finalized:
            return RedirectResponse(url="/plan", status_code=303)
        recipes = store.list()
        excluded = {meal.recipe_id for meal in plan.meals}
        replacement = generate_single_replacement(excluded, recipes)
        if replacement is None:
            return _render_plan(request)
        try:
            plan = plan_store.set_recipe(plan.id, meal_id, replacement.recipe.id, replacement.servings)
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
            plan_store.set_recipe(plan.id, meal_id, recipe.id, recipe.servings)
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


def _parse_optional_int(raw: Optional[str]) -> Optional[int]:
    if raw is None or not raw.strip():
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _parse_optional_float(raw: Optional[str]) -> Optional[float]:
    if raw is None or not raw.strip():
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _parse_enum(enum_cls, raw: str, default):
    try:
        return enum_cls(raw)
    except ValueError:
        return default


def _parse_enum_set(enum_cls, raw_values: list[str]) -> frozenset:
    # Invalid/stale values (a hand-edited or bookmarked URL) are dropped
    # rather than erroring the whole page.
    parsed = set()
    for raw in raw_values:
        try:
            parsed.add(enum_cls(raw))
        except ValueError:
            continue
    return frozenset(parsed)


def _empty_recipe_values() -> dict:
    return {
        "name": "",
        "cook_time_minutes": "",
        "servings": 2,
        "classification": Classification.OTHER.value,
        "difficulty": Difficulty.UNDEFINED.value,
        "calories_per_serving": "",
        "protein_g": "",
        "fiber_g": "",
        "ingredients": [{"name": "", "quantity": ""}],
        "steps": [""],
    }


def _format_ingredient_quantity(ingredient: Ingredient) -> str:
    parts = []
    if ingredient.quantity is not None:
        quantity = ingredient.quantity
        if quantity == int(quantity):
            quantity = int(quantity)
        parts.append(str(quantity))
    if ingredient.unit:
        parts.append(ingredient.unit)
    return " ".join(parts)


def _recipe_values_from_recipe(recipe: Recipe) -> dict:
    return {
        "name": recipe.name,
        "cook_time_minutes": recipe.cook_time_minutes,
        "servings": recipe.servings,
        "classification": recipe.classification.value,
        "difficulty": recipe.difficulty.value,
        "calories_per_serving": recipe.nutrition.calories_per_serving if recipe.nutrition.calories_per_serving is not None else "",
        "protein_g": recipe.nutrition.protein_g if recipe.nutrition.protein_g is not None else "",
        "fiber_g": recipe.nutrition.fiber_g if recipe.nutrition.fiber_g is not None else "",
        "ingredients": [
            {"name": ingredient.name, "quantity": _format_ingredient_quantity(ingredient)}
            for ingredient in recipe.ingredients
        ]
        or [{"name": "", "quantity": ""}],
        "steps": list(recipe.steps) or [""],
    }


def _recipe_values_from_form(form: FormData) -> dict:
    names = form.getlist("ingredient_name")
    quantities = form.getlist("ingredient_quantity")
    steps = list(form.getlist("step"))
    return {
        "name": form.get("name", ""),
        "cook_time_minutes": form.get("cook_time_minutes", ""),
        "servings": form.get("servings", ""),
        "classification": form.get("classification", ""),
        "difficulty": form.get("difficulty", ""),
        "calories_per_serving": form.get("calories_per_serving", ""),
        "protein_g": form.get("protein_g", ""),
        "fiber_g": form.get("fiber_g", ""),
        "ingredients": [{"name": name, "quantity": quantity} for name, quantity in zip(names, quantities)]
        or [{"name": "", "quantity": ""}],
        "steps": steps or [""],
    }


def _recipe_edit_context(
    *, mode: str, values: dict, error: Optional[str] = None, recipe_id: Optional[str] = None
) -> dict:
    return {
        "mode": mode,
        "values": values,
        "error": error,
        "classifications": list(Classification),
        "difficulties": [d for d in Difficulty if d != Difficulty.UNDEFINED],
        "form_action": "/recipes/new" if mode == "new" else f"/recipes/{recipe_id}/edit",
        "cancel_url": "/recipes" if mode == "new" else f"/recipes/{recipe_id}",
        "recipe_id": recipe_id,
        "nav_active": "library",
    }


def _parse_recipe_form(form: FormData, model_cls: type[BaseModel]) -> BaseModel:
    names = form.getlist("ingredient_name")
    quantities = form.getlist("ingredient_quantity")
    ingredients = []
    for name, quantity_text in zip(names, quantities):
        name = name.strip()
        if not name:
            continue
        ingredients.append(Ingredient(name=name, unit=quantity_text.strip() or None))
    steps = [step.strip() for step in form.getlist("step") if step.strip()]

    def _optional_float(key: str) -> Optional[float]:
        raw = str(form.get(key) or "").strip()
        return float(raw) if raw else None

    def _optional_int(key: str) -> Optional[int]:
        raw = str(form.get(key) or "").strip()
        return int(raw) if raw else None

    name = str(form.get("name") or "").strip()
    if not name:
        raise ValueError("Name is required")

    data = {
        "name": name,
        "cook_time_minutes": int(str(form.get("cook_time_minutes") or "").strip()),
        "classification": str(form.get("classification") or ""),
        "difficulty": str(form.get("difficulty") or Difficulty.UNDEFINED.value),
        "nutrition": {
            "calories_per_serving": _optional_int("calories_per_serving"),
            "protein_g": _optional_float("protein_g"),
            "fiber_g": _optional_float("fiber_g"),
        },
        "servings": int(str(form.get("servings") or "").strip()),
        "ingredients": ingredients,
        "steps": steps,
    }
    return model_cls(**data)
