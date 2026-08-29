
# Software Workflows

- The software shall have a local documentation of the API (https://spoonacular.com/food-api/docs).
- I shall update the documentation myself, if neeeded.
- The software shall write error logs if any API call generated errors. 
- The software shall always use the setting "sort=random" in Spoonacular searches.
- The software shall always use the setting "type=main course" - only full meals, never a side/dessert/etc.
- The software shall always use the setting "instructionsRequired=true" - a candidate without real steps is useless to the household.
- The software shall always use the setting "addRecipeNutrition=true" - needed both to enforce any nutrition constraint and to show accurate calorie/macro numbers.
- Every Spoonacular request must follow docs/spoonacular_api.md exactly - only real complexSearch parameters, real enum values, and correct units per field.
- Important contraints:
  - The software never searches for a food dish name specifically.
  - The software shall let spoonacular provide a dish based on user's preferences.
- The software always tries to find full meals in Spoonacular.
  - The goal of the application is to provide a full lunch/dinner guidance.
  - The software shall not provide only the complementary parts of the dish.

## 'lmeals import-spoonacular --count N'

- The software provides the 'complex search', with a wide virety of possibilities. The request must comply with Spoonacular API.
- The software requests all N dishes at once.
- The software downloads all dishes recipies and images.
- The software normalizes all recipies for software input.

## Weekly meals

- If the user has configured to receive N new recipies suggestions:
  - The software requests 3xN new recipies with complex search.
  - The software downloads the recipies and images.
  - The software normalizes the recipies for software inputs using local LLM.
- The software generates a plan with the available recipies and the requested recipies.
  - It shall fit user's settings:
    - Example: X meals per plan, Y new suggestion. X-Y meals are already locally stored. Y meals were new suggestions from Spoonacular.
- The user reviews the plan.
  - The user shall be able to select replace meals:
    - If the meal is pre-existing locally:
      - The software provies a list of 10 random items already available locally.
      - The user shall be able to reroll the replacement options.
      - The user shall be able to select a dish to replace the intended dish.
    - If the meal was a new suggestion:
      - The software shows all 3 collected dishes.
      - The user shall be able to select a dish to replace the intended dish.
      - The user shall NOT be able to reroll new suggestions.
      - The user shall be able to "select from cookbook".
        - Allows user to select a dish as "if the meal is pre-existing locally".

## Shopping list ingredient substitutes

- When a shopping-list ingredient is missing or disliked, the software calls `/food/ingredients/substitutes` (`ingredientName=<item>`) to surface a substitute for that item.
- Read-only and on-demand, one call per ingredient the user asks about - no change to stored plan/recipe data.
- Slots into the existing shopping-list flow as-is, no architecture conflict.

# Future milestone ideas (not yet scoped)

- `/recipes/findByIngredients` - a genuinely different selection mode: "what can I cook with what's already on hand" instead of preference-driven filters. Bigger than a wiring change - it needs a new "pantry" input, a real product decision, not just an API swap.
- `/recipes/autocomplete` / `/food/ingredients/autocomplete` - minor UX sugar for the manual-recipe-submission and shopping-list forms.
