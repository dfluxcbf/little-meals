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
        return store.put(payload)

    @router.delete("/household-preferences", response_model=HouseholdPreferences)
    def reset_preferences() -> HouseholdPreferences:
        return store.delete()

    return router
