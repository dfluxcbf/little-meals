from __future__ import annotations

from fastapi import APIRouter

from little_meals.models import HouseholdPreferences, HouseholdPreferencesUpdate
from little_meals.store.household_store import HouseholdPreferencesStore


def build_household_router(store: HouseholdPreferencesStore) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.get("/household-preferences", response_model=HouseholdPreferences)
    def get_preferences() -> HouseholdPreferences:
        return store.get()

    @router.put("/household-preferences", response_model=HouseholdPreferences)
    def update_preferences(payload: HouseholdPreferencesUpdate) -> HouseholdPreferences:
        """Saves everything in one action. `food_filter` (the household's
        own Spoonacular query parameters, see
        https://spoonacular.com/food-api/docs) is only touched when the
        request body actually includes that key - `model_fields_set` (not
        just "is it None") distinguishes an omitted key (leave the
        previously-saved filter alone) from an explicit `"food_filter":
        null` (clear it)."""
        preferences = store.put(payload)
        if "food_filter" in payload.model_fields_set:
            preferences = store.save_food_filter(payload.food_filter)
        return preferences

    @router.delete("/household-preferences", response_model=HouseholdPreferences)
    def reset_preferences() -> HouseholdPreferences:
        return store.delete()

    return router
