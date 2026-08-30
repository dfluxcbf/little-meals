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
    is_suggestion: bool = False
    """True if this slot was filled by the AI suggestion engine (Milestone 4)
    rather than drawn from the existing library (Milestone 3) - drives the
    "NEW" badge in the UI. Purely presentational: once created, a suggestion
    is a normal Recipe like any other (see planning/suggestion.py)."""


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
    recommendation_day: DayOfWeek = DayOfWeek.SUNDAY
    recommendation_time: time = time(9, 0)
    food_preferences_text: str = Field(default="", max_length=2000)
    food_filter: Optional[dict] = None
    """The household's own Spoonacular `/recipes/complexSearch` query
    parameters (see https://spoonacular.com/food-api/docs), built
    field-by-field on the dedicated /settings/recipe-preferences page
    (planning/spoonacular_fields.py) - never LLM-generated or otherwise
    interpreted, just stored and merged with the software's own always-on
    parameters (see planning/suggestion.py's build_complex_search_params)."""
    ai_suggestions_per_plan: int = Field(default=2, ge=0)
    default_servings: str = "2 adults"
    updated_at: Optional[datetime] = None


class HouseholdPreferencesUpdate(BaseModel):
    recipes_per_week: int = Field(ge=1)
    recommendation_day: DayOfWeek
    recommendation_time: time
    ai_suggestions_per_plan: int = Field(ge=0)
    default_servings: str
    food_preferences_text: str = Field(default="", max_length=2000)
    food_filter: Optional[dict] = None
    """Only inspected by the JSON API (routes_household.py) via
    `model_fields_set`, so a partial update that omits this key leaves the
    household's previously-saved filter untouched rather than clearing it -
    the dedicated /settings/recipe-preferences page instead always calls
    HouseholdPreferencesStore.save_food_filter() directly with whatever
    parse_filter_form built from its own POST body."""


class IngredientSubstitutes(BaseModel):
    """Spoonacular's /food/ingredients/substitutes response, for the
    shopping-list "find a substitute" action."""

    ingredient: str
    substitutes: list[str] = Field(default_factory=list)
    message: str = ""
