from __future__ import annotations

import importlib.resources
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncIterator, Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from little_meals import __version__
from little_meals.api.errors import ApiError
from little_meals.api.routes_household import build_household_router
from little_meals.api.routes_plan import build_plan_router
from little_meals.api.routes_recipes import build_recipes_router
from little_meals.api.routes_shopping import build_shopping_router
from little_meals.api.routes_ui import build_ui_router
from little_meals.config import Settings
from little_meals.llm.extraction import RecipeExtractionService
from little_meals.llm.ollama_client import OllamaClient
from little_meals.planning.plan_builder import build_meal_specs
from little_meals.scheduler import WeeklyScheduler
from little_meals.store.cook_along_store import CookAlongStore
from little_meals.store.household_store import HouseholdPreferencesStore
from little_meals.store.notification_store import NotificationStore
from little_meals.store.plan_store import MealPlanStore
from little_meals.store.recipe_store import RecipeStore
from little_meals.store.shopping_list_store import ShoppingListStore

logger = logging.getLogger(__name__)


def create_app(
    settings: Optional[Settings] = None,
    store: Optional[RecipeStore] = None,
    extractor: Optional[RecipeExtractionService] = None,
    household_store: Optional[HouseholdPreferencesStore] = None,
    plan_store: Optional[MealPlanStore] = None,
    shopping_list_store: Optional[ShoppingListStore] = None,
    notification_store: Optional[NotificationStore] = None,
    cook_along_store: Optional[CookAlongStore] = None,
    enable_scheduler: bool = False,
) -> FastAPI:
    settings = settings or Settings.from_env()
    store = store or RecipeStore(settings.recipes_dir)
    household_store = household_store or HouseholdPreferencesStore(settings.household_db_path)
    plan_store = plan_store or MealPlanStore(settings.plan_db_path)
    shopping_list_store = shopping_list_store or ShoppingListStore(settings.shopping_list_db_path)
    notification_store = notification_store or NotificationStore(settings.notification_db_path)
    cook_along_store = cook_along_store or CookAlongStore(settings.cook_along_db_path)
    if extractor is None:
        client = OllamaClient(settings.ollama_base_url, settings.ollama_model, settings.ollama_timeout_s)
        extractor = RecipeExtractionService(client)

    background_scheduler = None
    if enable_scheduler:
        from apscheduler.schedulers.background import BackgroundScheduler

        weekly_scheduler = WeeklyScheduler(
            household_store,
            plan_store,
            notification_store,
            generate_fn=lambda: plan_store.create(build_meal_specs(store, household_store, extractor)),
        )
        background_scheduler = BackgroundScheduler()
        background_scheduler.add_job(
            weekly_scheduler.check_and_maybe_generate,
            "interval",
            seconds=60,
            id="weekly-plan-check",
            next_run_time=datetime.now(),
        )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if background_scheduler is not None:
            background_scheduler.start()
        yield
        if background_scheduler is not None:
            background_scheduler.shutdown(wait=False)

    app = FastAPI(title="little-meals", version=__version__, lifespan=lifespan)
    app.state.settings = settings
    app.state.store = store
    app.state.household_store = household_store
    app.state.plan_store = plan_store
    app.state.shopping_list_store = shopping_list_store
    app.state.notification_store = notification_store
    app.state.cook_along_store = cook_along_store
    app.state.scheduler = background_scheduler

    package_root = importlib.resources.files("little_meals")
    templates = Jinja2Templates(directory=str(package_root / "templates"))
    # follow_symlink=True: Bazel runfiles trees are symlink forests, so the
    # served directory's files are individually symlinked to targets outside
    # it - Starlette's default symlink-containment check would 404 them.
    app.mount("/static", StaticFiles(directory=str(package_root / "static"), follow_symlink=True), name="static")

    @app.exception_handler(ApiError)
    async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.message, "code": exc.code, "details": exc.details},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"error": "Validation error", "code": "VALIDATION_ERROR", "details": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def internal_error_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled server error", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "code": "INTERNAL_ERROR", "details": {}},
        )

    app.include_router(build_recipes_router(store, extractor, settings))
    app.include_router(build_household_router(household_store))
    app.include_router(build_plan_router(plan_store, store, household_store, extractor))
    app.include_router(build_shopping_router(shopping_list_store, plan_store, store))
    app.include_router(
        build_ui_router(
            store,
            extractor,
            household_store,
            plan_store,
            shopping_list_store,
            notification_store,
            cook_along_store,
            templates,
        )
    )

    return app
