from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Optional, Protocol

FieldKind = Literal["text", "number", "boolean", "single_select", "multi_select"]

_NUMBER_RE = re.compile(r"-?\d+")


class FormLike(Protocol):
    """The subset of Starlette's FormData this module needs - satisfied by
    both a real form submission and any Mapping[str, str] (e.g. a plain
    dict in tests)."""

    def get(self, key: str) -> Optional[str]: ...

    def getlist(self, key: str) -> list[str]: ...

    def __contains__(self, key: str) -> bool: ...


@dataclass(frozen=True)
class FilterField:
    """One editable Spoonacular `/recipes/complexSearch` parameter -
    `name` is the real Spoonacular parameter name, used directly as both
    the form field name and the food_filter dict key."""

    name: str
    label: str
    kind: FieldKind
    options: tuple[str, ...] = ()
    placeholder: str = ""


@dataclass(frozen=True)
class FilterSection:
    title: str
    fields: tuple[FilterField, ...]


@dataclass(frozen=True)
class NutrientPair:
    key: str
    label: str
    unit: str
    min_name: str
    max_name: str


# Hand-copied from docs/spoonacular_api.md's "Known enum values" section -
# see its caveats about these not being machine-readable in Spoonacular's
# own OpenAPI spec.
CUISINES: tuple[str, ...] = (
    "African", "American", "British", "Cajun", "Caribbean", "Chinese",
    "Eastern European", "European", "French", "German", "Greek", "Indian",
    "Irish", "Italian", "Japanese", "Jewish", "Korean", "Latin American",
    "Mediterranean", "Mexican", "Middle Eastern", "Nordic", "Southern",
    "Spanish", "Thai", "Vietnamese",
)

DIETS: tuple[str, ...] = (
    "Gluten Free", "Ketogenic", "Vegetarian", "Lacto-Vegetarian",
    "Ovo-Vegetarian", "Vegan", "Pescetarian", "Paleo", "Primal",
    "Low FODMAP", "Whole30",
)

INTOLERANCES: tuple[str, ...] = (
    "Dairy", "Egg", "Gluten", "Grain", "Peanut", "Seafood", "Sesame",
    "Shellfish", "Soy", "Sulfite", "Tree Nut", "Wheat",
)

#: `sort`, `type`, `instructionsRequired`, `addRecipeNutrition`, and `number`
#: are deliberately not editable here - the software hardcodes them
#: (suggestion._ALWAYS_ON_SEARCH_PARAMS, and `number` from `count`)
#: regardless of what the household sets, per docs/spoonacular_plan.md's
#: "Software Workflows" section, so exposing them as editable would be
#: misleading.
FILTER_SECTIONS: tuple[FilterSection, ...] = (
    FilterSection("Search text", (
        FilterField("query", "Search phrase", "text", placeholder="e.g. dinner, comfort food"),
        FilterField("titleMatch", "Title must contain", "text", placeholder="e.g. Crock Pot"),
    )),
    FilterSection("Diet & cuisine", (
        FilterField("diet", "Diet", "single_select", options=DIETS),
        FilterField("cuisine", "Cuisines to include", "multi_select", options=CUISINES),
        FilterField("excludeCuisine", "Cuisines to exclude", "multi_select", options=CUISINES),
        FilterField("intolerances", "Intolerances", "multi_select", options=INTOLERANCES),
    )),
    FilterSection("Ingredients & equipment", (
        FilterField("includeIngredients", "Must include ingredients", "text", placeholder="e.g. tomato,cheese"),
        FilterField("excludeIngredients", "Must exclude ingredients", "text", placeholder="e.g. eggs"),
        FilterField("equipment", "Equipment", "text", placeholder="e.g. blender, frying pan"),
        FilterField("ignorePantry", "Ignore typical pantry items (water, salt, flour, etc.)", "boolean"),
    )),
    FilterSection("Recipe matching", (
        FilterField("author", "Author username", "text"),
        FilterField("tags", "Tags", "text", placeholder="diet, meal type, cuisine, or intolerance tags"),
        FilterField("recipeBoxId", "Recipe box id", "number"),
        FilterField("fillIngredients", "Show which ingredients are used vs. missing", "boolean"),
        FilterField("addRecipeInformation", "Include extra recipe information", "boolean"),
    )),
    FilterSection("Timing, servings & pagination", (
        FilterField("maxReadyTime", "Max ready time (minutes)", "number"),
        FilterField("minServings", "Min servings", "number"),
        FilterField("maxServings", "Max servings", "number"),
        FilterField("offset", "Skip this many results (0-900)", "number"),
    )),
)

MACRONUTRIENTS: tuple[NutrientPair, ...] = (
    NutrientPair("calories", "Calories", "kcal", "minCalories", "maxCalories"),
    NutrientPair("protein", "Protein", "g", "minProtein", "maxProtein"),
    NutrientPair("carbs", "Carbs", "g", "minCarbs", "maxCarbs"),
    NutrientPair("fat", "Fat", "g", "minFat", "maxFat"),
    NutrientPair("saturatedFat", "Saturated fat", "g", "minSaturatedFat", "maxSaturatedFat"),
    NutrientPair("sugar", "Sugar", "g", "minSugar", "maxSugar"),
    NutrientPair("fiber", "Fiber", "g", "minFiber", "maxFiber"),
    NutrientPair("cholesterol", "Cholesterol", "mg", "minCholesterol", "maxCholesterol"),
    NutrientPair("alcohol", "Alcohol", "g", "minAlcohol", "maxAlcohol"),
    NutrientPair("caffeine", "Caffeine", "mg", "minCaffeine", "maxCaffeine"),
)

VITAMINS_AND_MINERALS: tuple[NutrientPair, ...] = (
    NutrientPair("vitaminA", "Vitamin A", "IU", "minVitaminA", "maxVitaminA"),
    NutrientPair("vitaminC", "Vitamin C", "mg", "minVitaminC", "maxVitaminC"),
    NutrientPair("vitaminD", "Vitamin D", "mcg", "minVitaminD", "maxVitaminD"),
    NutrientPair("vitaminE", "Vitamin E", "mg", "minVitaminE", "maxVitaminE"),
    NutrientPair("vitaminK", "Vitamin K", "mcg", "minVitaminK", "maxVitaminK"),
    NutrientPair("vitaminB1", "Vitamin B1", "mg", "minVitaminB1", "maxVitaminB1"),
    NutrientPair("vitaminB2", "Vitamin B2", "mg", "minVitaminB2", "maxVitaminB2"),
    NutrientPair("vitaminB3", "Vitamin B3", "mg", "minVitaminB3", "maxVitaminB3"),
    NutrientPair("vitaminB5", "Vitamin B5", "mg", "minVitaminB5", "maxVitaminB5"),
    NutrientPair("vitaminB6", "Vitamin B6", "mg", "minVitaminB6", "maxVitaminB6"),
    NutrientPair("vitaminB12", "Vitamin B12", "mcg", "minVitaminB12", "maxVitaminB12"),
    NutrientPair("folate", "Folate", "mcg", "minFolate", "maxFolate"),
    NutrientPair("folicAcid", "Folic acid", "mcg", "minFolicAcid", "maxFolicAcid"),
    NutrientPair("calcium", "Calcium", "mg", "minCalcium", "maxCalcium"),
    NutrientPair("iron", "Iron", "mg", "minIron", "maxIron"),
    NutrientPair("magnesium", "Magnesium", "mg", "minMagnesium", "maxMagnesium"),
    NutrientPair("phosphorus", "Phosphorus", "mg", "minPhosphorus", "maxPhosphorus"),
    NutrientPair("potassium", "Potassium", "mg", "minPotassium", "maxPotassium"),
    NutrientPair("sodium", "Sodium", "mg", "minSodium", "maxSodium"),
    NutrientPair("zinc", "Zinc", "mg", "minZinc", "maxZinc"),
    NutrientPair("copper", "Copper", "mg", "minCopper", "maxCopper"),
    NutrientPair("manganese", "Manganese", "mg", "minManganese", "maxManganese"),
    NutrientPair("selenium", "Selenium", "mcg", "minSelenium", "maxSelenium"),
    NutrientPair("iodine", "Iodine", "mcg", "minIodine", "maxIodine"),
    NutrientPair("fluoride", "Fluoride", "mg", "minFluoride", "maxFluoride"),
    NutrientPair("choline", "Choline", "mg", "minCholine", "maxCholine"),
)

_ALL_NUTRIENT_PAIRS: tuple[NutrientPair, ...] = MACRONUTRIENTS + VITAMINS_AND_MINERALS


def _parse_number(raw: str) -> object:
    """Ints stay ints (Spoonacular's own examples use whole numbers for
    every one of these fields); anything else is parsed as a float. Raises
    ValueError on unparseable input, left to the caller to turn into a
    field-labeled error message."""
    if _NUMBER_RE.fullmatch(raw):
        return int(raw)
    return float(raw)


def parse_filter_form(form: FormLike) -> tuple[Optional[dict], list[str]]:
    """Builds the food_filter dict Spoonacular's complexSearch expects
    (the same shape HouseholdPreferencesStore.save_food_filter already
    persists) from a recipe-preferences form submission. Returns
    (filter_or_None, errors) - a validation error on any one numeric field
    aborts the whole save (errors non-empty, filter is None) so a
    household never ends up with a partially-applied filter. An
    all-blank/all-unchecked form produces (None, []), clearing any
    previously-saved filter the same way the empty JSON textarea used to."""
    result: dict[str, object] = {}
    errors: list[str] = []

    for section in FILTER_SECTIONS:
        for f in section.fields:
            if f.kind == "text":
                value = (form.get(f.name) or "").strip()
                if value:
                    result[f.name] = value
            elif f.kind == "number":
                raw = (form.get(f.name) or "").strip()
                if raw:
                    try:
                        result[f.name] = _parse_number(raw)
                    except ValueError:
                        errors.append(f"{f.label} must be a number")
            elif f.kind == "boolean":
                if f.name in form:
                    result[f.name] = True
            elif f.kind == "single_select":
                value = (form.get(f.name) or "").strip()
                if value:
                    result[f.name] = value
            elif f.kind == "multi_select":
                values = [v for v in form.getlist(f.name) if v]
                if values:
                    result[f.name] = ",".join(values)

    for pair in _ALL_NUTRIENT_PAIRS:
        for name, bound in ((pair.min_name, "minimum"), (pair.max_name, "maximum")):
            raw = (form.get(name) or "").strip()
            if raw:
                try:
                    result[name] = _parse_number(raw)
                except ValueError:
                    errors.append(f"{pair.label} {bound} must be a number")

    if errors:
        return None, errors
    return (result or None), []


def filter_to_display(food_filter: Optional[dict]) -> dict[str, object]:
    """The prefill shape the recipe-preferences page reads from on a plain
    GET: raw strings for text/number fields, bool for booleans, list[str]
    for multi-select fields (split back out of Spoonacular's
    comma-joined-string storage form)."""
    food_filter = food_filter or {}
    display: dict[str, object] = {}
    for section in FILTER_SECTIONS:
        for f in section.fields:
            value = food_filter.get(f.name)
            if f.kind == "boolean":
                display[f.name] = bool(value)
            elif f.kind == "multi_select":
                # A household that set this field before this page existed
                # (either via a hand-pasted JSON filter or a direct PUT
                # against the JSON API) may have stored a JSON list instead
                # of Spoonacular's own comma-joined-string form - accept
                # both rather than crashing on a household's existing data.
                if isinstance(value, list):
                    display[f.name] = [str(v) for v in value]
                else:
                    display[f.name] = value.split(",") if value else []
            else:
                display[f.name] = "" if value is None else str(value)
    for pair in _ALL_NUTRIENT_PAIRS:
        for name in (pair.min_name, pair.max_name):
            value = food_filter.get(name)
            display[name] = "" if value is None else str(value)
    return display


def form_to_display(form: FormLike) -> dict[str, object]:
    """Same shape as filter_to_display, but built directly from a raw form
    submission - used to redisplay exactly what the household typed when a
    numeric field fails to parse, rather than discarding their input."""
    display: dict[str, object] = {}
    for section in FILTER_SECTIONS:
        for f in section.fields:
            if f.kind == "boolean":
                display[f.name] = f.name in form
            elif f.kind == "multi_select":
                display[f.name] = [v for v in form.getlist(f.name) if v]
            else:
                display[f.name] = (form.get(f.name) or "").strip()
    for pair in _ALL_NUTRIENT_PAIRS:
        for name in (pair.min_name, pair.max_name):
            display[name] = (form.get(name) or "").strip()
    return display
