from __future__ import annotations

from datetime import datetime, time
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Classification(str, Enum):
    VEGETARIAN = "vegetarian"
    PESCETARIAN = "pescetarian"
    VEGAN = "vegan"
    KETOGENIC = "ketogenic"
    PALEO = "paleo"
    OTHER = "other"


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    UNDEFINED = "undefined"


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
    calories_per_serving: Optional[int] = Field(default=None, ge=0)
    protein_g: Optional[float] = None
    fiber_g: Optional[float] = None


class Recipe(BaseModel):
    id: str
    name: str
    cook_time_minutes: int = Field(ge=1)
    classification: Classification
    difficulty: Difficulty = Field(default=Difficulty.UNDEFINED)
    nutrition: Nutrition
    servings: int = Field(default=2, ge=1)
    ingredients: list[Ingredient] = Field(min_length=1)
    steps: list[str] = Field(min_length=1)
    source_text: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class RecipeCreate(BaseModel):
    name: str
    cook_time_minutes: int = Field(ge=1)
    classification: Classification
    difficulty: Difficulty = Field(default=Difficulty.UNDEFINED)
    nutrition: Nutrition
    servings: int = Field(default=2, ge=1)
    ingredients: list[Ingredient] = Field(min_length=1)
    steps: list[str] = Field(min_length=1)


class RecipeUpdate(BaseModel):
    name: str
    cook_time_minutes: int = Field(ge=1)
    classification: Classification
    difficulty: Difficulty = Field(default=Difficulty.UNDEFINED)
    nutrition: Nutrition
    servings: int = Field(default=2, ge=1)
    ingredients: list[Ingredient] = Field(min_length=1)
    steps: list[str] = Field(min_length=1)


class PlanMeal(BaseModel):
    """One meal in a MealPlan - a reference to a library Recipe plus the
    per-plan state that doesn't belong on the Recipe itself: how many
    servings to make this week (starts at the recipe's own `servings`,
    overridable), and whether the household has cooked it yet. Meals in a
    plan aren't bound to specific days (see design.md's "Meal plan"
    concept) - `id` is just a stable per-plan handle, not a day slot."""

    id: str
    recipe_id: str
    servings: int = Field(ge=1)
    cooked: bool = False


class MealPlan(BaseModel):
    id: str
    created_at: datetime
    finalized: bool = False
    meals: list[PlanMeal] = Field(default_factory=list)


class CookAlongSession(BaseModel):
    """An in-progress cook-along's position, keyed by recipe_id - a
    household only ever has one active cook-along per recipe. A row's
    existence means the household left mid-session (resumable via
    "Continue"); finishing (cooked or not) always deletes it, so the next
    cook-along for that recipe starts fresh."""

    recipe_id: str
    current_step: int = 0
    checked_ingredients: list[int] = Field(default_factory=list)
    started_at: datetime
    updated_at: datetime


class ServingsUpdate(BaseModel):
    servings: int = Field(ge=1)


class CookedUpdate(BaseModel):
    cooked: bool


class ShoppingListItem(BaseModel):
    """One merged ingredient line - see planning/shopping_list.py for how
    same-name-and-unit ingredients across a plan's recipes get combined into
    one of these, quantities scaled to each recipe's servings."""

    id: str
    name: str
    quantity: Optional[float] = None
    unit: Optional[str] = None
    checked: bool = False


class ShoppingList(BaseModel):
    id: str
    plan_id: str
    created_at: datetime
    items: list[ShoppingListItem] = Field(default_factory=list)
    actual_cost: Optional[float] = None


class ItemCheckedUpdate(BaseModel):
    checked: bool


class ActualCostUpdate(BaseModel):
    actual_cost: float = Field(ge=0)


class HouseholdPreferences(BaseModel):
    """Configuration shared by the whole household, not per person - see
    design.md's "Household preferences" concept. A singleton, not a
    collection: there is exactly one of these per installation."""

    recipes_per_week: int = Field(default=5, ge=1)
    recommendation_enabled: bool = True
    recommendation_day: DayOfWeek = DayOfWeek.SUNDAY
    recommendation_time: time = time(9, 0)
    auto_confirm_enabled: bool = False
    auto_confirm_day: DayOfWeek = DayOfWeek.SUNDAY
    auto_confirm_time: time = time(9, 0)
    default_servings: str = "2 adults"
    updated_at: Optional[datetime] = None


class HouseholdPreferencesUpdate(BaseModel):
    recipes_per_week: int = Field(ge=1)
    recommendation_enabled: bool
    recommendation_day: DayOfWeek
    recommendation_time: time
    auto_confirm_enabled: bool
    auto_confirm_day: DayOfWeek
    auto_confirm_time: time
    default_servings: str
