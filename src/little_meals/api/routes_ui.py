from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from little_meals.llm.extraction import ExtractionError, RecipeExtractionService
from little_meals.llm.ollama_client import OllamaUnavailable
from little_meals.models import Preference, Recipe
from little_meals.store.recipe_store import RecipeNotFound, RecipeStore


def build_ui_router(store: RecipeStore, extractor: RecipeExtractionService, templates: Jinja2Templates) -> APIRouter:
    router = APIRouter()

    @router.get("/", include_in_schema=False)
    def index() -> RedirectResponse:
        return RedirectResponse(url="/recipes", status_code=303)

    @router.get("/recipes", response_class=HTMLResponse, include_in_schema=False)
    def recipes_list(request: Request) -> HTMLResponse:
        recipes = store.list()
        return templates.TemplateResponse(request, "recipes_list.html", {"recipes": recipes})

    @router.get("/recipes/new", response_class=HTMLResponse, include_in_schema=False)
    def recipe_new_form(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(request, "recipe_new.html", {"error": None})

    @router.post("/recipes", include_in_schema=False)
    def recipe_new_submit(request: Request, text: str = Form(...)):
        try:
            extracted = extractor.extract(text)
        except (OllamaUnavailable, ExtractionError) as exc:
            return templates.TemplateResponse(request, "recipe_new.html", {"error": str(exc)}, status_code=422)

        recipe = Recipe.from_extracted(extracted, id="", source_text=text, now=datetime.now(timezone.utc))
        stored = store.create(recipe)
        return RedirectResponse(url=f"/recipes/{stored.id}", status_code=303)

    @router.get("/recipes/{recipe_id}", response_class=HTMLResponse, include_in_schema=False)
    def recipe_detail(request: Request, recipe_id: str) -> HTMLResponse:
        try:
            recipe = store.get(recipe_id)
        except RecipeNotFound:
            return templates.TemplateResponse(request, "recipe_not_found.html", {"recipe_id": recipe_id}, status_code=404)
        return templates.TemplateResponse(request, "recipe_detail.html", {"recipe": recipe})

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

    return router
