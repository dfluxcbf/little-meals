from __future__ import annotations

from datetime import datetime, time
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Classification(str, Enum):
    VEGETARIAN = "vegetarian"
    PESCETARIAN = "pescetarian"
    OTHER = "other"


class Preference(str, Enum):
    LIKED = "liked"
    DISLIKED = "disliked"


class DayOfWeek(str, Enum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class Ingredient(BaseModel):
    name: str
    quantity: Optional[float] = None
    unit: Optional[str] = None
    note: Optional[str] = None


class Nutrition(BaseModel):
    calories_per_serving: int = Field(ge=0)
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None


class ExtractedRecipe(BaseModel):
    """The LLM-facing subset of a Recipe: everything the extraction service
    is responsible for producing. Deliberately excludes id, preference, and
    timestamps so the LLM can never invent an id or a preference state."""

    name: str
    cook_time_minutes: int = Field(ge=1)
    classification: Classification
    nutrition: Nutrition
    servings: int = Field(default=2, ge=1)
    ingredients: list[Ingredient] = Field(min_length=1)
    steps: list[str] = Field(min_length=1)


class Recipe(BaseModel):
    id: str
    name: str
    cook_time_minutes: int = Field(ge=1)
    classification: Classification
    nutrition: Nutrition
    servings: int = Field(default=2, ge=1)
    ingredients: list[Ingredient] = Field(min_length=1)
    steps: list[str] = Field(min_length=1)
    preference: Preference = Preference.LIKED
    source_text: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_extracted(cls, extracted: ExtractedRecipe, *, id: str, source_text: Optional[str], now: datetime) -> "Recipe":
        return cls(
            id=id,
            name=extracted.name,
            cook_time_minutes=extracted.cook_time_minutes,
            classification=extracted.classification,
            nutrition=extracted.nutrition,
            servings=extracted.servings,
            ingredients=extracted.ingredients,
            steps=extracted.steps,
            preference=Preference.LIKED,
            source_text=source_text,
            created_at=now,
            updated_at=now,
        )


class RecipeCreate(BaseModel):
    name: str
    cook_time_minutes: int = Field(ge=1)
    classification: Classification
    nutrition: Nutrition
    servings: int = Field(default=2, ge=1)
    ingredients: list[Ingredient] = Field(min_length=1)
    steps: list[str] = Field(min_length=1)


class RecipeUpdate(BaseModel):
    name: str
    cook_time_minutes: int = Field(ge=1)
    classification: Classification
    nutrition: Nutrition
    servings: int = Field(default=2, ge=1)
    ingredients: list[Ingredient] = Field(min_length=1)
    steps: list[str] = Field(min_length=1)


class PreferenceUpdate(BaseModel):
    preference: Preference


class ExtractRequest(BaseModel):
    text: str


class HouseholdPreferences(BaseModel):
    """Configuration shared by the whole household, not per person - see
    design.md's "Household preferences" concept. A singleton, not a
    collection: there is exactly one of these per installation."""

    recipes_per_week: int = Field(default=5, ge=1)
    recommendation_day: DayOfWeek = DayOfWeek.SUNDAY
    recommendation_time: time = time(9, 0)
    food_preferences: list[str] = Field(default_factory=list)
    ai_suggestions_per_plan: int = Field(default=2, ge=0)
    default_servings: str = "2 adults"
    updated_at: Optional[datetime] = None


class HouseholdPreferencesUpdate(BaseModel):
    recipes_per_week: int = Field(ge=1)
    recommendation_day: DayOfWeek
    recommendation_time: time
    food_preferences: list[str] = Field(default_factory=list)
    ai_suggestions_per_plan: int = Field(ge=0)
    default_servings: str
