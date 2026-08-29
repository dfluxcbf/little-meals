# Spoonacular API Reference

Locally mirrored reference for the Spoonacular Food API, generated from the community-maintained OpenAPI 3 spec at [ddsky/spoonacular-api-clients](https://github.com/ddsky/spoonacular-api-clients) (spec version `2.0.2`), cross-checked against [spoonacular.com/food-api/docs](https://spoonacular.com/food-api/docs). Regenerate by re-running `gen_spoonacular_docs.py` against a freshly-downloaded copy of `spoonacular-openapi-3.json` if Spoonacular's API changes.

## Caveats about this reference

- **No enum data.** Spoonacular does not publish machine-readable enum lists for `cuisine`, `excludeCuisine`, `diet`, `intolerances`, `type`, or `sort` - not even in this OpenAPI spec. Those parameters are typed as plain strings whose valid values are documented only as prose on the docs site. See the hand-copied lists in ["Known enum values"](#known-enum-values) below; treat them as best-effort, not authoritative.
- **`required` is occasionally wrong.** A handful of shared parameters (e.g. `query` on `/recipes/complexSearch`) are marked `required: true` in this spec via a reused `$ref` component even though Spoonacular's own docs describe them as optional there. This is a spec-authoring quirk in the community repo, not a live API constraint - verify against the prose docs before trusting `required` at face value.
- **Response schemas are best-effort.** Only 8 named schemas exist in `components/schemas`; most endpoint responses are defined inline and were unrolled here up to 3 levels deep (deeper object/array bodies are shown as `object{...}`).
- **Auth.** The spec declares an `apiKeyScheme` security scheme using the `x-api-key` header, but Spoonacular's docs and most examples pass the key as an `apiKey` query parameter instead - both work in practice.

## Table of contents

- [ingredients](#ingredients)
  - [GET /food/ingredients/autocomplete](#get-foodingredientsautocomplete) - Autocomplete Ingredient Search
  - [POST /food/ingredients/map](#post-foodingredientsmap) - Map Ingredients to Grocery Products
  - [GET /food/ingredients/search](#get-foodingredientssearch) - Ingredient Search
  - [GET /food/ingredients/substitutes](#get-foodingredientssubstitutes) - Get Ingredient Substitutes
  - [GET /food/ingredients/{id}/amount](#get-foodingredientsidamount) - Compute Ingredient Amount
  - [GET /food/ingredients/{id}/information](#get-foodingredientsidinformation) - Get Ingredient Information
  - [GET /food/ingredients/{id}/substitutes](#get-foodingredientsidsubstitutes) - Get Ingredient Substitutes by ID
  - [POST /recipes/visualizeIngredients](#post-recipesvisualizeingredients) - Ingredients Widget
  - [GET /recipes/{id}/ingredientWidget.png](#get-recipesidingredientwidgetpng) - Ingredients by ID Image
- [meal planning](#meal-planning)
  - [GET /mealplanner/generate](#get-mealplannergenerate) - Generate Meal Plan
  - [DELETE /mealplanner/{username}/day/{date}](#delete-mealplannerusernamedaydate) - Clear Meal Plan Day
  - [POST /mealplanner/{username}/items](#post-mealplannerusernameitems) - Add to Meal Plan
  - [DELETE /mealplanner/{username}/items/{id}](#delete-mealplannerusernameitemsid) - Delete from Meal Plan
  - [GET /mealplanner/{username}/shopping-list](#get-mealplannerusernameshopping-list) - Get Shopping List
  - [POST /mealplanner/{username}/shopping-list/items](#post-mealplannerusernameshopping-listitems) - Add to Shopping List
  - [DELETE /mealplanner/{username}/shopping-list/items/{id}](#delete-mealplannerusernameshopping-listitemsid) - Delete from Shopping List
  - [POST /mealplanner/{username}/shopping-list/{start_date}/{end_date}](#post-mealplannerusernameshopping-liststart_dateend_date) - Generate Shopping List
  - [GET /mealplanner/{username}/templates](#get-mealplannerusernametemplates) - Get Meal Plan Templates
  - [POST /mealplanner/{username}/templates](#post-mealplannerusernametemplates) - Add Meal Plan Template
  - [GET /mealplanner/{username}/templates/{id}](#get-mealplannerusernametemplatesid) - Get Meal Plan Template
  - [DELETE /mealplanner/{username}/templates/{id}](#delete-mealplannerusernametemplatesid) - Delete Meal Plan Template
  - [GET /mealplanner/{username}/week/{start_date}](#get-mealplannerusernameweekstart_date) - Get Meal Plan Week
  - [POST /users/connect](#post-usersconnect) - Connect User
- [menu items](#menu-items)
  - [GET /food/menuItems/search](#get-foodmenuitemssearch) - Search Menu Items
  - [GET /food/menuItems/suggest](#get-foodmenuitemssuggest) - Autocomplete Menu Item Search
  - [GET /food/menuItems/{id}](#get-foodmenuitemsid) - Get Menu Item Information
  - [GET /food/menuItems/{id}/nutritionLabel](#get-foodmenuitemsidnutritionlabel) - Menu Item Nutrition Label Widget
  - [GET /food/menuItems/{id}/nutritionLabel.png](#get-foodmenuitemsidnutritionlabelpng) - Menu Item Nutrition Label Image
  - [GET /food/menuItems/{id}/nutritionWidget](#get-foodmenuitemsidnutritionwidget) - Menu Item Nutrition by ID Widget
  - [GET /food/menuItems/{id}/nutritionWidget.png](#get-foodmenuitemsidnutritionwidgetpng) - Menu Item Nutrition by ID Image
- [misc](#misc)
  - [GET /food/converse](#get-foodconverse) - Talk to Chatbot
  - [GET /food/converse/suggest](#get-foodconversesuggest) - Conversation Suggests
  - [GET /food/customFoods/search](#get-foodcustomfoodssearch) - Search Custom Foods
  - [POST /food/detect](#post-fooddetect) - Detect Food in Text
  - [GET /food/images/analyze](#get-foodimagesanalyze) - Image Analysis by URL
  - [GET /food/images/classify](#get-foodimagesclassify) - Image Classification by URL
  - [GET /food/jokes/random](#get-foodjokesrandom) - Random Food Joke
  - [GET /food/search](#get-foodsearch) - Search All Food
  - [GET /food/site/search](#get-foodsitesearch) - Search Site Content
  - [GET /food/trivia/random](#get-foodtriviarandom) - Random Food Trivia
  - [GET /food/videos/search](#get-foodvideossearch) - Search Food Videos
- [products](#products)
  - [POST /food/products/classify](#post-foodproductsclassify) - Classify Grocery Product
  - [POST /food/products/classifyBatch](#post-foodproductsclassifybatch) - Classify Grocery Product Bulk
  - [GET /food/products/search](#get-foodproductssearch) - Search Grocery Products
  - [GET /food/products/suggest](#get-foodproductssuggest) - Autocomplete Product Search
  - [GET /food/products/upc/{upc}](#get-foodproductsupcupc) - Search Grocery Products by UPC
  - [GET /food/products/upc/{upc}/comparable](#get-foodproductsupcupccomparable) - Get Comparable Products
  - [GET /food/products/{id}](#get-foodproductsid) - Get Product Information
  - [GET /food/products/{id}/nutritionLabel](#get-foodproductsidnutritionlabel) - Product Nutrition Label Widget
  - [GET /food/products/{id}/nutritionLabel.png](#get-foodproductsidnutritionlabelpng) - Product Nutrition Label Image
  - [GET /food/products/{id}/nutritionWidget](#get-foodproductsidnutritionwidget) - Product Nutrition by ID Widget
  - [GET /food/products/{id}/nutritionWidget.png](#get-foodproductsidnutritionwidgetpng) - Product Nutrition by ID Image
- [recipes](#recipes)
  - [POST /food/ingredients/glycemicLoad](#post-foodingredientsglycemicload) - Compute Glycemic Load
  - [POST /recipes/analyzeInstructions](#post-recipesanalyzeinstructions) - Analyze Recipe Instructions
  - [GET /recipes/autocomplete](#get-recipesautocomplete) - Autocomplete Recipe Search
  - [GET /recipes/complexSearch](#get-recipescomplexsearch) - Search Recipes
  - [GET /recipes/convert](#get-recipesconvert) - Convert Amounts
  - [POST /recipes/cuisine](#post-recipescuisine) - Classify Cuisine
  - [GET /recipes/extract](#get-recipesextract) - Extract Recipe from Website
  - [GET /recipes/findByIngredients](#get-recipesfindbyingredients) - Search Recipes by Ingredients
  - [GET /recipes/findByNutrients](#get-recipesfindbynutrients) - Search Recipes by Nutrients
  - [GET /recipes/guessNutrition](#get-recipesguessnutrition) - Guess Nutrition by Dish Name
  - [GET /recipes/informationBulk](#get-recipesinformationbulk) - Get Recipe Information Bulk
  - [POST /recipes/parseIngredients](#post-recipesparseingredients) - Parse Ingredients
  - [GET /recipes/queries/analyze](#get-recipesqueriesanalyze) - Analyze a Recipe Search Query
  - [GET /recipes/quickAnswer](#get-recipesquickanswer) - Quick Answer
  - [GET /recipes/random](#get-recipesrandom) - Get Random Recipes
  - [POST /recipes/visualizeEquipment](#post-recipesvisualizeequipment) - Equipment Widget
  - [POST /recipes/visualizeNutrition](#post-recipesvisualizenutrition) - Recipe Nutrition Widget
  - [POST /recipes/visualizePriceEstimator](#post-recipesvisualizepriceestimator) - Price Breakdown Widget
  - [POST /recipes/visualizeRecipe](#post-recipesvisualizerecipe) - Create Recipe Card
  - [POST /recipes/visualizeTaste](#post-recipesvisualizetaste) - Recipe Taste Widget
  - [GET /recipes/{id}/analyzedInstructions](#get-recipesidanalyzedinstructions) - Get Analyzed Recipe Instructions
  - [GET /recipes/{id}/equipmentWidget](#get-recipesidequipmentwidget) - Equipment by ID Widget
  - [GET /recipes/{id}/equipmentWidget.json](#get-recipesidequipmentwidgetjson) - Equipment by ID
  - [GET /recipes/{id}/equipmentWidget.png](#get-recipesidequipmentwidgetpng) - Equipment by ID Image
  - [GET /recipes/{id}/information](#get-recipesidinformation) - Get Recipe Information
  - [GET /recipes/{id}/ingredientWidget](#get-recipesidingredientwidget) - Ingredients by ID Widget
  - [GET /recipes/{id}/ingredientWidget.json](#get-recipesidingredientwidgetjson) - Ingredients by ID
  - [GET /recipes/{id}/nutritionLabel](#get-recipesidnutritionlabel) - Recipe Nutrition Label Widget
  - [GET /recipes/{id}/nutritionLabel.png](#get-recipesidnutritionlabelpng) - Recipe Nutrition Label Image
  - [GET /recipes/{id}/nutritionWidget](#get-recipesidnutritionwidget) - Recipe Nutrition by ID Widget
  - [GET /recipes/{id}/nutritionWidget.json](#get-recipesidnutritionwidgetjson) - Nutrition by ID
  - [GET /recipes/{id}/nutritionWidget.png](#get-recipesidnutritionwidgetpng) - Recipe Nutrition by ID Image
  - [GET /recipes/{id}/priceBreakdownWidget](#get-recipesidpricebreakdownwidget) - Price Breakdown by ID Widget
  - [GET /recipes/{id}/priceBreakdownWidget.json](#get-recipesidpricebreakdownwidgetjson) - Price Breakdown by ID
  - [GET /recipes/{id}/priceBreakdownWidget.png](#get-recipesidpricebreakdownwidgetpng) - Price Breakdown by ID Image
  - [GET /recipes/{id}/similar](#get-recipesidsimilar) - Get Similar Recipes
  - [GET /recipes/{id}/summary](#get-recipesidsummary) - Summarize Recipe
  - [GET /recipes/{id}/tasteWidget](#get-recipesidtastewidget) - Recipe Taste by ID Widget
  - [GET /recipes/{id}/tasteWidget.json](#get-recipesidtastewidgetjson) - Taste by ID
  - [GET /recipes/{id}/tasteWidget.png](#get-recipesidtastewidgetpng) - Recipe Taste by ID Image
- [untagged](#untagged)
  - [GET /food/restaurants/search](#get-foodrestaurantssearch) - Search Restaurants
  - [POST /recipes/analyze](#post-recipesanalyze) - Analyze Recipe
  - [GET /recipes/{id}/card](#get-recipesidcard) - Create Recipe Card
- [wine](#wine)
  - [GET /food/wine/description](#get-foodwinedescription) - Wine Description
  - [GET /food/wine/dishes](#get-foodwinedishes) - Dish Pairing for Wine
  - [GET /food/wine/pairing](#get-foodwinepairing) - Wine Pairing
  - [GET /food/wine/recommendation](#get-foodwinerecommendation) - Wine Recommendation

## ingredients

### GET /food/ingredients/autocomplete

**Autocomplete Ingredient Search**

Autocomplete the entry of an ingredient.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `query` | query | string | yes | The (natural language) search query. (e.g. `burger`) |
| `number` | query | integer | no | The maximum number of items to return (between 1 and 100). Defaults to 10. (e.g. `10`) |
| `metaInformation` | query | boolean | no | Whether to return more meta information about the ingredients. (e.g. `False`) |
| `intolerances` | query | string | no | A comma-separated list of intolerances. All recipes returned must not contain ingredients that are not suitable for people with the intolerances entered. See a full list of supported intolerances. (e.g. `egg`) |
| `language` | query | string | no | The language of the input. Either 'en' or 'de'. (e.g. `en`) |

**Response 200** (`application/json`):

`array<` `object` {
  - `name`*: `string`
  - `image`*: `string`
  - `id`: `integer`
  - `aisle`: `string`
  - `possibleUnits`: `array<` `string` `>`
} `>`

Other responses: `401`, `403`, `404`

---

### POST /food/ingredients/map

**Map Ingredients to Grocery Products**

Map a set of ingredients to products you can buy in the grocery store.

_No parameters._

**Request body** (`application/json`):

`object` {
  - `ingredients`*: `array<` `string` `>`
  - `servings`*: `number`
}

**Response 200** (`application/json`):

`array<` `object` {
  - `original`*: `string`
  - `originalName`*: `string`
  - `ingredientImage`*: `string`
  - `meta`*: `array<` `string` `>`
  - `products`*: `array<` `object` {
    - `id`*: `integer`
    - `title`*: `string`
    - `upc`*: `string`
  } `>`
} `>`

Other responses: `401`, `403`, `404`

---

### GET /food/ingredients/search

**Ingredient Search**

Search for simple whole foods (e.g. fruits, vegetables, nuts, grains, meat, fish, dairy etc.).

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `query` | query | string | yes | The (natural language) search query. (e.g. `burger`) |
| `addChildren` | query | boolean | no | Whether to add children of found foods. (e.g. `True`) |
| `minProteinPercent` | query | number | no | The minimum percentage of protein the food must have (between 0 and 100). (e.g. `10`) |
| `maxProteinPercent` | query | number | no | The maximum percentage of protein the food can have (between 0 and 100). (e.g. `90`) |
| `minFatPercent` | query | number | no | The minimum percentage of fat the food must have (between 0 and 100). (e.g. `10`) |
| `maxFatPercent` | query | number | no | The maximum percentage of fat the food can have (between 0 and 100). (e.g. `90`) |
| `minCarbsPercent` | query | number | no | The minimum percentage of carbs the food must have (between 0 and 100). (e.g. `10`) |
| `maxCarbsPercent` | query | number | no | The maximum percentage of carbs the food can have (between 0 and 100). (e.g. `90`) |
| `metaInformation` | query | boolean | no | Whether to return more meta information about the ingredients. (e.g. `False`) |
| `intolerances` | query | string | no | A comma-separated list of intolerances. All recipes returned must not contain ingredients that are not suitable for people with the intolerances entered. See a full list of supported intolerances. (e.g. `egg`) |
| `sort` | query | string | no | The strategy to sort recipes by. See a full list of supported sorting options. (e.g. `calories`) |
| `sortDirection` | query | string | no | The direction in which to sort. Must be either 'asc' (ascending) or 'desc' (descending). (e.g. `asc`) |
| `offset` | query | integer | no | The number of results to skip (between 0 and 900). |
| `number` | query | integer | no | The maximum number of items to return (between 1 and 100). Defaults to 10. (e.g. `10`) |
| `language` | query | string | no | The language of the input. Either 'en' or 'de'. (e.g. `en`) |

**Response 200** (`application/json`):

`object` {
  - `results`*: `array<` `object` {
    - `id`*: `integer`
    - `name`*: `string`
    - `image`*: `string`
  } `>`
  - `offset`*: `integer`
  - `number`*: `integer`
  - `totalResults`*: `integer`
}

Other responses: `401`, `403`, `404`

---

### GET /food/ingredients/substitutes

**Get Ingredient Substitutes**

Search for substitutes for a given ingredient.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `ingredientName` | query | string | yes | The name of the ingredient you want to replace. (e.g. `butter`) |

**Response 200** (`application/json`):

`object` {
  - `ingredient`*: `string`
  - `substitutes`*: `array<` `string` `>`
  - `message`*: `string`
}

Other responses: `401`, `403`, `404`

---

### GET /food/ingredients/{id}/amount

**Compute Ingredient Amount**

Compute the amount you need of a certain ingredient for a certain nutritional goal. For example, how much pineapple do you have to eat to get 10 grams of protein?

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `id` | path | integer | yes | The id of the ingredient you want the amount for. (e.g. `9266`) |
| `nutrient` | query | string | yes | The target nutrient. See a list of supported nutrients. (e.g. `protein`) |
| `target` | query | integer | yes | The target number of the given nutrient. (e.g. `2`) |
| `unit` | query | string | no | The target unit. (e.g. `oz`) |

**Response 200** (`application/json`):

`object` {
  - `amount`*: `number`
  - `unit`*: `string`
}

Other responses: `401`, `403`, `404`

---

### GET /food/ingredients/{id}/information

**Get Ingredient Information**

Use an ingredient id to get all available information about an ingredient, such as its image and supermarket aisle.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `id` | path | integer | yes | The ingredient id. (e.g. `9266`) |
| `amount` | query | number | no | The amount of this ingredient. (e.g. `150`) |
| `unit` | query | string | no | The unit for the given amount. (e.g. `grams`) |

**Response 200** (`application/json`):

[`IngredientInformation`](#schema-ingredientinformation)

Other responses: `401`, `403`, `404`

---

### GET /food/ingredients/{id}/substitutes

**Get Ingredient Substitutes by ID**

Search for substitutes for a given ingredient.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `id` | path | integer | yes | The id of the ingredient you want substitutes for. (e.g. `1001`) |

**Response 200** (`application/json`):

`object` {
  - `ingredient`*: `string`
  - `substitutes`*: `array<` `string` `>`
  - `message`*: `string`
}

Other responses: `401`, `403`, `404`

---

### POST /recipes/visualizeIngredients

**Ingredients Widget**

Visualize ingredients of a recipe. You can play around with that endpoint!

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `language` | query | string | no | The language of the input. Either 'en' or 'de'. (e.g. `en`) |

**Request body** (`application/x-www-form-urlencoded`):

`object` {
  - `ingredientList`*: `string`
  - `servings`*: `number`
  - `measure`: `string`
  - `view`: `string`
  - `defaultCss`: `boolean`
  - `showBacklink`: `boolean`
}

**Response 200** (`text/html`):

`string`

Other responses: `401`, `403`, `404`

---

### GET /recipes/{id}/ingredientWidget.png

**Ingredients by ID Image**

Visualize a recipe's ingredient list.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `id` | path | integer | yes | The recipe id. (e.g. `1082038`) |
| `measure` | query | string | no | Whether the the measures should be 'us' or 'metric'. (e.g. `metric`) |

**Response 200** (`image/png`):

`string` (binary)

Other responses: `401`, `403`, `404`

---

## meal planning

### GET /mealplanner/generate

**Generate Meal Plan**

Generate a meal plan with three meals per day (breakfast, lunch, and dinner).

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `timeFrame` | query | string | no | Either for one "day" or an entire "week". (e.g. `day`) |
| `targetCalories` | query | number | no | What is the caloric target for one day? The meal plan generator will try to get as close as possible to that goal. (e.g. `2000`) |
| `diet` | query | string | no | Enter a diet that the meal plan has to adhere to. See a full list of supported diets. (e.g. `vegetarian`) |
| `exclude` | query | string | no | A comma-separated list of allergens or ingredients that must be excluded. (e.g. `shellfish, olives`) |

**Response 200** (`application/json`):

`object` {
  - `meals`*: `array<` `object` {
    - `id`*: `integer`
    - `title`*: `string`
    - `imageType`*: `string`
    - `readyInMinutes`*: `integer`
    - `servings`*: `number`
    - `sourceUrl`*: `string`
  } `>`
  - `nutrients`*: `object` {
    - `calories`*: `number`
    - `carbohydrates`*: `number`
    - `fat`*: `number`
    - `protein`*: `number`
  }
}

Other responses: `401`, `403`, `404`

---

### DELETE /mealplanner/{username}/day/{date}

**Clear Meal Plan Day**

Delete all planned items from the user's meal plan for a specific day.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `username` | path | string | yes | The username. (e.g. `dsky`) |
| `date` | path | string | yes | The date in the format yyyy-mm-dd. (e.g. `2020-06-01`) |
| `hash` | query | string | yes | The private hash for the username. |

**Response 200** (`application/json`):

`object`

Other responses: `401`, `403`, `404`

---

### POST /mealplanner/{username}/items

**Add to Meal Plan**

Add an item to the user's meal plan.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `username` | path | string | yes | The username. (e.g. `dsky`) |
| `hash` | query | string | yes | The private hash for the username. |

**Request body** (`application/json`):

`object` {
  - `date`*: `number`
  - `slot`*: `integer`
  - `position`*: `integer`
  - `type`*: `string`
  - `value`*: `object` {
    - `ingredients`*: `array<` `object` {
      - `name`*: `string`
    } `>`
  }
}

**Response 200** (`application/json`):

`object`

Other responses: `401`, `403`, `404`

---

### DELETE /mealplanner/{username}/items/{id}

**Delete from Meal Plan**

Delete an item from the user's meal plan.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `username` | path | string | yes | The username. (e.g. `dsky`) |
| `id` | path | integer | yes | The shopping list item id. (e.g. `15678`) |
| `hash` | query | string | yes | The private hash for the username. |

**Response 200** (`application/json`):

`object`

Other responses: `401`, `403`, `404`

---

### GET /mealplanner/{username}/shopping-list

**Get Shopping List**

Get the current shopping list for the given user.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `username` | path | string | yes | The username. (e.g. `dsky`) |
| `hash` | query | string | yes | The private hash for the username. |

**Response 200** (`application/json`):

`object` {
  - `aisles`*: `array<` `object` {
    - `aisle`*: `string`
    - `items`: `array<` `object` {
      - `id`*: `integer`
      - `name`*: `string`
      - `measures`: `object{...}`
      - `pantryItem`*: `boolean`
      - `aisle`*: `string`
      - `cost`*: `number`
      - `ingredientId`*: `integer`
    } `>`
  } `>`
  - `cost`*: `number`
  - `startDate`*: `number`
  - `endDate`*: `number`
}

Other responses: `401`, `403`, `404`

---

### POST /mealplanner/{username}/shopping-list/items

**Add to Shopping List**

Add an item to the current shopping list of a user.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `username` | path | string | yes | The username. (e.g. `dsky`) |
| `hash` | query | string | yes | The private hash for the username. |

**Request body** (`application/json`):

`object` {
  - `item`*: `string`
  - `aisle`*: `string`
  - `parse`*: `boolean`
}

**Response 200** (`application/json`):

`object` {
  - `aisles`*: `array<` `object` {
    - `aisle`*: `string`
    - `items`: `array<` `object` {
      - `id`*: `integer`
      - `name`*: `string`
      - `measures`: `object{...}`
      - `pantryItem`*: `boolean`
      - `aisle`*: `string`
      - `cost`*: `number`
      - `ingredientId`*: `integer`
    } `>`
  } `>`
  - `cost`*: `number`
  - `startDate`*: `number`
  - `endDate`*: `number`
}

Other responses: `401`, `403`, `404`

---

### DELETE /mealplanner/{username}/shopping-list/items/{id}

**Delete from Shopping List**

Delete an item from the current shopping list of the user.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `username` | path | string | yes | The username. (e.g. `dsky`) |
| `id` | path | integer | yes | The shopping list item id. (e.g. `15678`) |
| `hash` | query | string | yes | The private hash for the username. |

**Response 200** (`application/json`):

`object`

Other responses: `401`, `403`, `404`

---

### POST /mealplanner/{username}/shopping-list/{start_date}/{end_date}

**Generate Shopping List**

Generate the shopping list for a user from the meal planner in a given time frame.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `username` | path | string | yes | The username. (e.g. `dsky`) |
| `start_date` | path | string | yes | The start date in the format yyyy-mm-dd. (e.g. `2020-06-01`) |
| `end_date` | path | string | yes | The end date in the format yyyy-mm-dd. (e.g. `2020-06-07`) |
| `hash` | query | string | yes | The private hash for the username. |

**Response 200** (`application/json`):

`object` {
  - `aisles`*: `array<` `object` {
    - `aisle`*: `string`
    - `items`: `array<` `object` {
      - `id`*: `integer`
      - `name`*: `string`
      - `measures`: `object{...}`
      - `pantryItem`*: `boolean`
      - `aisle`*: `string`
      - `cost`*: `number`
      - `ingredientId`*: `integer`
    } `>`
  } `>`
  - `cost`*: `number`
  - `startDate`*: `number`
  - `endDate`*: `number`
}

Other responses: `401`, `403`, `404`

---

### GET /mealplanner/{username}/templates

**Get Meal Plan Templates**

Get meal plan templates from user or public ones.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `username` | path | string | yes | The username. (e.g. `dsky`) |
| `hash` | query | string | yes | The private hash for the username. |

**Response 200** (`application/json`):

`object` {
  - `templates`*: `array<` `object` {
    - `id`*: `integer`
    - `name`*: `string`
  } `>`
}

Other responses: `401`, `403`, `404`

---

### POST /mealplanner/{username}/templates

**Add Meal Plan Template**

Add a meal plan template for a user.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `username` | path | string | yes | The username. (e.g. `dsky`) |
| `hash` | query | string | yes | The private hash for the username. (e.g. `4b5v4398573406`) |

**Response 200** (`application/json`):

`object` {
  - `name`*: `string`
  - `items`*: `array<` `object` {
    - `day`*: `integer`
    - `slot`*: `integer`
    - `position`*: `integer`
    - `type`*: `string`
    - `value`: `object` {
      - `id`: `integer`
      - `servings`: `number`
      - `title`: `string`
      - `imageType`: `string`
    }
  } `>`
  - `publishAsPublic`*: `boolean`
}

Other responses: `401`, `403`, `404`

---

### GET /mealplanner/{username}/templates/{id}

**Get Meal Plan Template**

Get information about a meal plan template.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `username` | path | string | yes | The username. (e.g. `dsky`) |
| `id` | path | integer | yes | The shopping list item id. (e.g. `15678`) |
| `hash` | query | string | yes | The private hash for the username. |

**Response 200** (`application/json`):

`object` {
  - `id`*: `integer`
  - `name`*: `string`
  - `days`*: `array<` `object` {
    - `nutritionSummary`: `object` {
      - `nutrients`*: `array<` `object{...}` `>`
    }
    - `nutritionSummaryBreakfast`: `object` {
      - `nutrients`*: `array<` `object{...}` `>`
    }
    - `nutritionSummaryLunch`: `object` {
      - `nutrients`*: `array<` `object{...}` `>`
    }
    - `nutritionSummaryDinner`: `object` {
      - `nutrients`*: `array<` `object{...}` `>`
    }
    - `day`*: `string`
    - `items`: `array<` `object` {
      - `id`*: `integer`
      - `slot`*: `integer`
      - `position`*: `integer`
      - `type`*: `string`
      - `value`: `object{...}`
    } `>`
  } `>`
}

Other responses: `401`, `403`, `404`

---

### DELETE /mealplanner/{username}/templates/{id}

**Delete Meal Plan Template**

Delete a meal plan template for a user.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `username` | path | string | yes | The username. (e.g. `dsky`) |
| `id` | path | integer | yes | The shopping list item id. (e.g. `15678`) |
| `hash` | query | string | yes | The private hash for the username. (e.g. `4b5v4398573406`) |

**Response 200** (`application/json`):

`object`

Other responses: `401`, `403`, `404`

---

### GET /mealplanner/{username}/week/{start_date}

**Get Meal Plan Week**

Retrieve a meal planned week for the given user. The username must be a spoonacular user and the hash must the the user's hash that can be found in his/her account.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `username` | path | string | yes | The username. (e.g. `dsky`) |
| `start_date` | path | string | yes | The start date of the meal planned week in the format yyyy-mm-dd. (e.g. `2020-06-01`) |
| `hash` | query | string | yes | The private hash for the username. |

**Response 200** (`application/json`):

`object` {
  - `days`*: `array<` `object` {
    - `nutritionSummary`: `object` {
      - `nutrients`*: `array<` `object{...}` `>`
    }
    - `nutritionSummaryBreakfast`: `object` {
      - `nutrients`*: `array<` `object{...}` `>`
    }
    - `nutritionSummaryLunch`: `object` {
      - `nutrients`*: `array<` `object{...}` `>`
    }
    - `nutritionSummaryDinner`: `object` {
      - `nutrients`*: `array<` `object{...}` `>`
    }
    - `date`*: `number`
    - `day`*: `string`
    - `items`: `array<` `object` {
      - `id`*: `integer`
      - `slot`*: `integer`
      - `position`*: `integer`
      - `type`*: `string`
      - `value`: `object{...}`
    } `>`
  } `>`
}

Other responses: `401`, `403`, `404`

---

### POST /users/connect

**Connect User**

In order to call user-specific endpoints, you need to connect your app's users to spoonacular users.

_No parameters._

**Request body** (`application/json`):

`object` {
  - `username`*: `string`
  - `firstName`*: `string`
  - `lastName`*: `string`
  - `email`*: `string`
}

**Response 200** (`application/json`):

`object` {
  - `username`*: `string`
  - `hash`*: `string`
}

Other responses: `401`, `403`, `404`

---

## menu items

### GET /food/menuItems/search

**Search Menu Items**

Search over 115,000 menu items from over 800 fast food and chain restaurants. For example, McDonald's Big Mac or Starbucks Mocha.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `query` | query | string | yes | The (natural language) search query. (e.g. `burger`) |
| `minCalories` | query | number | no | The minimum amount of calories the menu item must have. (e.g. `50`) |
| `maxCalories` | query | number | no | The maximum amount of calories the menu item can have. (e.g. `800`) |
| `minCarbs` | query | number | no | The minimum amount of carbohydrates in grams the menu item must have. (e.g. `10`) |
| `maxCarbs` | query | number | no | The maximum amount of carbohydrates in grams the menu item can have. (e.g. `100`) |
| `minProtein` | query | number | no | The minimum amount of protein in grams the menu item must have. (e.g. `10`) |
| `maxProtein` | query | number | no | The maximum amount of protein in grams the menu item can have. (e.g. `100`) |
| `minFat` | query | number | no | The minimum amount of fat in grams the menu item must have. (e.g. `1`) |
| `maxFat` | query | number | no | The maximum amount of fat in grams the menu item can have. (e.g. `100`) |
| `addMenuItemInformation` | query | boolean | no | If set to true, you get more information about the menu items returned. (e.g. `True`) |
| `offset` | query | integer | no | The number of results to skip (between 0 and 900). |
| `number` | query | integer | no | The maximum number of items to return (between 1 and 100). Defaults to 10. (e.g. `10`) |

**Response 200** (`application/json`):

`object` {
  - `menuItems`*: `array<` [`MenuItem`](#schema-menuitem) `>`
  - `totalMenuItems`*: `integer`
  - `type`*: `string`
  - `offset`*: `integer`
  - `number`*: `integer`
}

Other responses: `401`, `403`, `404`

---

### GET /food/menuItems/suggest

**Autocomplete Menu Item Search**

Generate suggestions for menu items based on a (partial) query. The matches will be found by looking in the title only.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `query` | query | string | yes | The (partial) search query. (e.g. `chicke`) |
| `number` | query | integer | no | The number of results to return (between 1 and 25). (e.g. `10`) |

**Response 200** (`application/json`):

`object` {
  - `results`*: `array<` `object` {
    - `id`*: `integer`
    - `title`*: `string`
  } `>`
}

Other responses: `401`, `403`, `404`

---

### GET /food/menuItems/{id}

**Get Menu Item Information**

Use a menu item id to get all available information about a menu item, such as nutrition.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `id` | path | integer | yes | The menu item id. (e.g. `424571`) |

**Response 200** (`application/json`):

[`MenuItem`](#schema-menuitem)

Other responses: `401`, `403`, `404`

---

### GET /food/menuItems/{id}/nutritionLabel

**Menu Item Nutrition Label Widget**

Visualize a menu item's nutritional label information as HTML including CSS.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `id` | path | integer | yes | The menu item id. (e.g. `342313`) |
| `defaultCss` | query | boolean | no | Whether the default CSS should be added to the response. (e.g. `False`) |
| `showOptionalNutrients` | query | boolean | no | Whether to show optional nutrients. (e.g. `False`) |
| `showZeroValues` | query | boolean | no | Whether to show zero values. (e.g. `False`) |
| `showIngredients` | query | boolean | no | Whether to show a list of ingredients. (e.g. `False`) |

**Response 200** (`text/html`):

`string`

Other responses: `401`, `403`, `404`

---

### GET /food/menuItems/{id}/nutritionLabel.png

**Menu Item Nutrition Label Image**

Visualize a menu item's nutritional label information as an image.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `id` | path | integer | yes | The menu item id. (e.g. `342313`) |
| `showOptionalNutrients` | query | boolean | no | Whether to show optional nutrients. (e.g. `False`) |
| `showZeroValues` | query | boolean | no | Whether to show zero values. (e.g. `False`) |
| `showIngredients` | query | boolean | no | Whether to show a list of ingredients. (e.g. `False`) |

**Response 200** (`image/png`):

`string` (binary)

Other responses: `401`, `403`, `404`

---

### GET /food/menuItems/{id}/nutritionWidget

**Menu Item Nutrition by ID Widget**

Visualize a menu item's nutritional information as HTML including CSS.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `id` | path | integer | yes | The menu item id. (e.g. `1003464`) |
| `defaultCss` | query | boolean | no | Whether the default CSS should be added to the response. (e.g. `False`) |

**Response 200** (`text/html`):

`string`

Other responses: `401`, `403`, `404`

---

### GET /food/menuItems/{id}/nutritionWidget.png

**Menu Item Nutrition by ID Image**

Visualize a menu item's nutritional information as HTML including CSS.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `id` | path | integer | yes | The menu item id. (e.g. `424571`) |

**Response 200** (`image/png`):

`string` (binary)

Other responses: `401`, `403`, `404`

---

## misc

### GET /food/converse

**Talk to Chatbot**

This endpoint can be used to have a conversation about food with the spoonacular chatbot. Use the "Get Conversation Suggests" endpoint to show your user what he or she can say.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `text` | query | string | yes | The request / question / answer from the user to the chatbot. (e.g. `donut recipes`) |
| `contextId` | query | string | no | An arbitrary globally unique id for your conversation. The conversation can contain states so you should pass your context id if you want the bot to be able to remember the conversation. (e.g. `342938`) |

**Response 200** (`application/json`):

`object` {
  - `answerText`*: `string`
  - `media`*: `array<` `object` {
    - `title`: `string`
    - `image`: `string`
    - `link`: `string`
  } `>`
}

Other responses: `401`, `403`, `404`

---

### GET /food/converse/suggest

**Conversation Suggests**

This endpoint returns suggestions for things the user can say or ask the chatbot.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `query` | query | string | yes | A (partial) query from the user. The endpoint will return if it matches topics it can talk about. (e.g. `tell`) |
| `number` | query | number | no | The number of suggestions to return (between 1 and 25). (e.g. `5`) |

**Response 200** (`application/json`):

`object` {
  - `suggests`*: `object` {
    - `_`*: `array<` `object` {
      - `name`*: `string`
    } `>`
  }
  - `words`*: `array<` `string` `>`
}

Other responses: `401`, `403`, `404`

---

### GET /food/customFoods/search

**Search Custom Foods**

Search custom foods in a user's account.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `query` | query | string | yes | The (natural language) search query. (e.g. `burger`) |
| `username` | query | string | yes | The username. (e.g. `dsky`) |
| `hash` | query | string | yes | The private hash for the username. (e.g. `4b5v4398573406`) |
| `offset` | query | integer | no | The number of results to skip (between 0 and 900). |
| `number` | query | integer | no | The maximum number of items to return (between 1 and 100). Defaults to 10. (e.g. `10`) |

**Response 200** (`application/json`):

`object` {
  - `customFoods`*: `array<` `object` {
    - `id`*: `integer`
    - `title`*: `string`
    - `servings`*: `number`
    - `imageUrl`*: `string`
    - `price`*: `number`
  } `>`
  - `type`*: `string`
  - `offset`*: `integer`
  - `number`*: `integer`
}

Other responses: `401`, `403`, `404`

---

### POST /food/detect

**Detect Food in Text**

Take any text and find all mentions of food contained within it. This task is also called Named Entity Recognition (NER). In this case, the entities are foods. Either dishes, such as pizza or cheeseburger, or ingredients, such as cucumber or almonds.

_No parameters._

**Request body** (`application/x-www-form-urlencoded`):

`object` {
  - `text`*: `string`
}

**Response 200** (`application/json`):

`object` {
  - `annotations`*: `array<` `object` {
    - `annotation`*: `string`
    - `image`*: `string`
    - `tag`*: `string`
  } `>`
}

Other responses: `401`, `403`, `404`

---

### GET /food/images/analyze

**Image Analysis by URL**

Analyze a food image. The API tries to classify the image, guess the nutrition, and find a matching recipes.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `imageUrl` | query | string | yes | The URL of the image to be analyzed. (e.g. `https://spoonacular.com/recipeImages/635350-240x150.jpg`) |

**Response 200** (`application/json`):

`object` {
  - `nutrition`*: `object` {
    - `recipesUsed`*: `integer`
    - `calories`*: `object` {
      - `value`*: `number`
      - `unit`*: `string`
      - `confidenceRange95Percent`*: `object{...}`
      - `standardDeviation`*: `number`
    }
    - `fat`*: `object` {
      - `value`*: `number`
      - `unit`*: `string`
      - `confidenceRange95Percent`*: `object{...}`
      - `standardDeviation`*: `number`
    }
    - `protein`*: `object` {
      - `value`*: `number`
      - `unit`*: `string`
      - `confidenceRange95Percent`*: `object{...}`
      - `standardDeviation`*: `number`
    }
    - `carbs`*: `object` {
      - `value`*: `number`
      - `unit`*: `string`
      - `confidenceRange95Percent`*: `object{...}`
      - `standardDeviation`*: `number`
    }
  }
  - `category`*: `object` {
    - `name`*: `string`
    - `probability`*: `number`
  }
  - `recipes`*: `array<` `object` {
    - `id`*: `integer`
    - `title`*: `string`
    - `imageType`*: `string`
    - `url`*: `string`
  } `>`
}

Other responses: `401`, `403`, `404`

---

### GET /food/images/classify

**Image Classification by URL**

Classify a food image.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `imageUrl` | query | string | yes | The URL of the image to be classified. (e.g. `https://spoonacular.com/recipeImages/635350-240x150.jpg`) |

**Response 200** (`application/json`):

`object` {
  - `category`*: `string`
  - `probability`*: `number`
}

Other responses: `401`, `403`, `404`

---

### GET /food/jokes/random

**Random Food Joke**

Get a random joke that is related to food. Caution: this is an endpoint for adults!

_No parameters._

**Response 200** (`application/json`):

`object` {
  - `text`*: `string`
}

Other responses: `401`, `403`, `404`

---

### GET /food/search

**Search All Food**

Search all food content with one call. That includes recipes, grocery products, menu items, simple foods (ingredients), and food videos.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `query` | query | string | yes | The search query. (e.g. `apple`) |
| `offset` | query | integer | no | The number of results to skip (between 0 and 900). |
| `number` | query | integer | no | The maximum number of items to return (between 1 and 100). Defaults to 10. (e.g. `10`) |

**Response 200** (`application/json`):

`object` {
  - `query`*: `string`
  - `totalResults`*: `integer`
  - `limit`*: `integer`
  - `offset`*: `integer`
  - `searchResults`*: `array<` `object` {
    - `name`*: `string`
    - `totalResults`*: `integer`
    - `results`: `array<` [`SearchResult`](#schema-searchresult) `>`
  } `>`
}

Other responses: `401`, `403`, `404`

---

### GET /food/site/search

**Search Site Content**

Search spoonacular's site content. You'll be able to find everything that you could also find using the search suggestions on spoonacular.com. This is a suggest API so you can send partial strings as queries.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `query` | query | string | yes | The query to search for. You can also use partial queries such as "spagh" to already find spaghetti recipes, articles, grocery products, and other content. (e.g. `past`) |

**Response 200** (`application/json`):

`object` {
  - `Articles`*: `array<` [`SearchResult`](#schema-searchresult) `>`
  - `Grocery Products`*: `array<` [`SearchResult`](#schema-searchresult) `>`
  - `Menu Items`*: `array<` [`SearchResult`](#schema-searchresult) `>`
  - `Recipes`*: `array<` [`SearchResult`](#schema-searchresult) `>`
}

Other responses: `401`, `403`, `404`

---

### GET /food/trivia/random

**Random Food Trivia**

Returns random food trivia.

_No parameters._

**Response 200** (`application/json`):

`object` {
  - `text`*: `string`
}

Other responses: `401`, `403`, `404`

---

### GET /food/videos/search

**Search Food Videos**

Find recipe and other food related videos.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `query` | query | string | yes | The (natural language) search query. (e.g. `burger`) |
| `type` | query | string | no | The type of the recipes. See a full list of supported meal types. (e.g. `main course`) |
| `cuisine` | query | string | no | The cuisine(s) of the recipes. One or more, comma separated. See a full list of supported cuisines. (e.g. `italian`) |
| `diet` | query | string | no | The diet for which the recipes must be suitable. See a full list of supported diets. (e.g. `vegetarian`) |
| `includeIngredients` | query | string | no | A comma-separated list of ingredients that the recipes should contain. (e.g. `tomato,cheese`) |
| `excludeIngredients` | query | string | no | A comma-separated list of ingredients or ingredient types that the recipes must not contain. (e.g. `eggs`) |
| `minLength` | query | number | no | Minimum video length in seconds. (e.g. `0`) |
| `maxLength` | query | number | no | Maximum video length in seconds. (e.g. `999`) |
| `offset` | query | integer | no | The number of results to skip (between 0 and 900). |
| `number` | query | integer | no | The maximum number of items to return (between 1 and 100). Defaults to 10. (e.g. `10`) |

**Response 200** (`application/json`):

`object` {
  - `videos`*: `array<` `object` {
    - `title`*: `string`
    - `length`*: `integer`
    - `rating`*: `number`
    - `shortTitle`*: `string`
    - `thumbnail`*: `string`
    - `views`*: `integer`
    - `youTubeId`*: `string`
  } `>`
  - `totalResults`*: `integer`
}

Other responses: `401`, `403`, `404`

---

## products

### POST /food/products/classify

**Classify Grocery Product**

This endpoint allows you to match a packaged food to a basic category, e.g. a specific brand of milk to the category milk.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `locale` | query | string | no | The display name of the returned category, supported is en_US (for American English) and en_GB (for British English). (e.g. `en_US`) |

**Request body** (`application/json`):

`object` {
  - `title`*: `string`
  - `upc`*: `string`
  - `plu_code`*: `string`
}

**Response 200** (`application/json`):

`object` {
  - `cleanTitle`*: `string`
  - `image`*: `string`
  - `category`*: `string`
  - `breadcrumbs`*: `array<` `string` `>`
  - `usdaCode`*: `integer`
}

Other responses: `401`, `403`, `404`

---

### POST /food/products/classifyBatch

**Classify Grocery Product Bulk**

Provide a set of product jsons, get back classified products.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `locale` | query | string | no | The display name of the returned category, supported is en_US (for American English) and en_GB (for British English). (e.g. `en_US`) |

**Request body** (`application/json`):

`array<` `object` {
  - `title`*: `string`
  - `upc`*: `string`
  - `plu_code`*: `string`
} `>`

**Response 200** (`application/json`):

`array<` `object` {
  - `cleanTitle`*: `string`
  - `image`*: `string`
  - `category`*: `string`
  - `breadcrumbs`*: `array<` `string` `>`
  - `usdaCode`*: `integer`
} `>`

Other responses: `401`, `403`, `404`

---

### GET /food/products/search

**Search Grocery Products**

Search packaged food products, such as frozen pizza or Greek yogurt.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `query` | query | string | yes | The (natural language) search query. (e.g. `burger`) |
| `minCalories` | query | number | no | The minimum amount of calories the product must have. (e.g. `50`) |
| `maxCalories` | query | number | no | The maximum amount of calories the product can have. (e.g. `800`) |
| `minCarbs` | query | number | no | The minimum amount of carbohydrates in grams the product must have. (e.g. `10`) |
| `maxCarbs` | query | number | no | The maximum amount of carbohydrates in grams the product can have. (e.g. `100`) |
| `minProtein` | query | number | no | The minimum amount of protein in grams the product must have. (e.g. `10`) |
| `maxProtein` | query | number | no | The maximum amount of protein in grams the product can have. (e.g. `100`) |
| `minFat` | query | number | no | The minimum amount of fat in grams the product must have. (e.g. `1`) |
| `maxFat` | query | number | no | The maximum amount of fat in grams the product can have. (e.g. `100`) |
| `addProductInformation` | query | boolean | no | If set to true, you get more information about the products returned. (e.g. `True`) |
| `offset` | query | integer | no | The number of results to skip (between 0 and 900). |
| `number` | query | integer | no | The maximum number of items to return (between 1 and 100). Defaults to 10. (e.g. `10`) |

**Response 200** (`application/json`):

`object` {
  - `products`*: `array<` `object` {
    - `id`*: `integer`
    - `title`*: `string`
    - `imageType`*: `string`
  } `>`
  - `totalProducts`*: `integer`
  - `type`*: `string`
  - `offset`*: `integer`
  - `number`*: `integer`
}

Other responses: `401`, `403`, `404`

---

### GET /food/products/suggest

**Autocomplete Product Search**

Generate suggestions for grocery products based on a (partial) query. The matches will be found by looking in the title only.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `query` | query | string | yes | The (partial) search query. (e.g. `chicke`) |
| `number` | query | integer | no | The number of results to return (between 1 and 25). (e.g. `10`) |

**Response 200** (`application/json`):

`object` {
  - `results`*: `array<` `object` {
    - `id`*: `integer`
    - `title`*: `string`
  } `>`
}

Other responses: `401`, `403`, `404`

---

### GET /food/products/upc/{upc}

**Search Grocery Products by UPC**

Get information about a packaged food using its UPC.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `upc` | path | string | yes | The product's UPC. (e.g. `041631000564`) |

**Response 200** (`application/json`):

`object` {
  - `id`*: `integer`
  - `title`*: `string`
  - `badges`*: `array<` `string` `>`
  - `importantBadges`*: `array<` `string` `>`
  - `breadcrumbs`*: `array<` `string` `>`
  - `generatedText`*: `string`
  - `imageType`*: `string`
  - `ingredientCount`: `integer`
  - `ingredientList`*: `string`
  - `ingredients`*: `array<` [`IngredientBasics`](#schema-ingredientbasics) `>`
  - `likes`*: `number`
  - `nutrition`*: `object` {
    - `nutrients`*: `array<` `object` {
      - `name`*: `string`
      - `amount`*: `number`
      - `unit`*: `string`
      - `percentOfDailyNeeds`*: `number`
    } `>`
    - `caloricBreakdown`*: `object` {
      - `percentProtein`*: `number`
      - `percentFat`*: `number`
      - `percentCarbs`*: `number`
    }
  }
  - `price`*: `number`
  - `servings`*: `object` {
    - `number`*: `number`
    - `size`*: `number`
    - `unit`*: `string`
  }
  - `spoonacularScore`*: `number`
}

Other responses: `401`, `403`, `404`

---

### GET /food/products/upc/{upc}/comparable

**Get Comparable Products**

Find comparable products to the given one.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `upc` | path | string | yes | The UPC of the product for which you want to find comparable products. (e.g. `033698816271`) |

**Response 200** (`application/json`):

`object` {
  - `comparableProducts`*: `object` {
    - `calories`*: `array<` [`ComparableProduct`](#schema-comparableproduct) `>`
    - `likes`*: `array<` [`ComparableProduct`](#schema-comparableproduct) `>`
    - `price`*: `array<` [`ComparableProduct`](#schema-comparableproduct) `>`
    - `protein`*: `array<` [`ComparableProduct`](#schema-comparableproduct) `>`
    - `spoonacular_score`*: `array<` [`ComparableProduct`](#schema-comparableproduct) `>`
    - `sugar`*: `array<` [`ComparableProduct`](#schema-comparableproduct) `>`
  }
}

Other responses: `401`, `403`, `404`

---

### GET /food/products/{id}

**Get Product Information**

Use a product id to get full information about a product, such as ingredients, nutrition, etc. The nutritional information is per serving.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `id` | path | integer | yes | The id of the packaged food. (e.g. `22347`) |

**Response 200** (`application/json`):

[`ProductInformation`](#schema-productinformation)

Other responses: `401`, `403`, `404`

---

### GET /food/products/{id}/nutritionLabel

**Product Nutrition Label Widget**

Get a product's nutrition label as an HTML widget.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `id` | path | integer | yes | The product id. (e.g. `22347`) |
| `defaultCss` | query | boolean | no | Whether the default CSS should be added to the response. (e.g. `False`) |
| `showOptionalNutrients` | query | boolean | no | Whether to show optional nutrients. (e.g. `False`) |
| `showZeroValues` | query | boolean | no | Whether to show zero values. (e.g. `False`) |
| `showIngredients` | query | boolean | no | Whether to show a list of ingredients. (e.g. `False`) |

**Response 200** (`text/html`):

`string`

Other responses: `401`, `403`, `404`

---

### GET /food/products/{id}/nutritionLabel.png

**Product Nutrition Label Image**

Get a product's nutrition label as an image.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `id` | path | integer | yes | The product id. (e.g. `22347`) |
| `showOptionalNutrients` | query | boolean | no | Whether to show optional nutrients. (e.g. `False`) |
| `showZeroValues` | query | boolean | no | Whether to show zero values. (e.g. `False`) |
| `showIngredients` | query | boolean | no | Whether to show a list of ingredients. (e.g. `False`) |

**Response 200** (`image/png`):

`string` (binary)

Other responses: `401`, `403`, `404`

---

### GET /food/products/{id}/nutritionWidget

**Product Nutrition by ID Widget**

Visualize a product's nutritional information as HTML including CSS.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `id` | path | integer | yes | The id of the product. (e.g. `7657`) |
| `defaultCss` | query | boolean | no | Whether the default CSS should be added to the response. (e.g. `False`) |

**Response 200** (`text/html`):

`string`

Other responses: `401`, `403`, `404`

---

### GET /food/products/{id}/nutritionWidget.png

**Product Nutrition by ID Image**

Visualize a product's nutritional information as an image.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `id` | path | integer | yes | The id of the product. (e.g. `7657`) |

**Response 200** (`image/png`):

`string` (binary)

Other responses: `401`, `403`, `404`

---

## recipes

### POST /food/ingredients/glycemicLoad

**Compute Glycemic Load**

Retrieve the glycemic index for a list of ingredients and compute the individual and total glycemic load.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `language` | query | string | no | The language of the input. Either 'en' or 'de'. (e.g. `en`) |

**Request body** (`application/json`):

`object` {
  - `ingredients`*: `array<` `string` `>`
}

**Response 200** (`application/json`):

`object` {
  - `totalGlycemicLoad`*: `number`
  - `ingredients`*: `array<` `object` {
    - `id`*: `integer`
    - `original`*: `string`
    - `glycemicIndex`*: `number`
    - `glycemicLoad`*: `number`
  } `>`
}

Other responses: `401`, `403`, `404`

---

### POST /recipes/analyzeInstructions

**Analyze Recipe Instructions**

This endpoint allows you to break down instructions into atomic steps. Furthermore, each step will contain the ingredients and equipment required. Additionally, all ingredients and equipment from the recipe's instructions will be extracted independently of the step they're used in.

_No parameters._

**Request body** (`application/x-www-form-urlencoded`):

`object` {
  - `instructions`*: `string`
}

**Response 200** (`application/json`):

`object` {
  - `parsedInstructions`*: `array<` `object` {
    - `name`*: `string`
    - `steps`: `array<` `object` {
      - `number`*: `number`
      - `step`*: `string`
      - `ingredients`: `array<` `object{...}` `>`
      - `equipment`: `array<` `object{...}` `>`
    } `>`
  } `>`
  - `ingredients`*: `array<` `object` {
    - `id`*: `integer`
    - `name`*: `string`
  } `>`
  - `equipment`*: `array<` `object` {
    - `id`*: `integer`
    - `name`*: `string`
  } `>`
}

Other responses: `401`, `403`, `404`

---

### GET /recipes/autocomplete

**Autocomplete Recipe Search**

Autocomplete a partial input to suggest possible recipe names.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `query` | query | string | yes | The (natural language) search query. (e.g. `burger`) |
| `number` | query | integer | no | The maximum number of items to return (between 1 and 100). Defaults to 10. (e.g. `10`) |

**Response 200** (`application/json`):

`array<` `object` {
  - `id`*: `integer`
  - `title`*: `string`
  - `imageType`*: `string`
} `>`

Other responses: `401`, `403`, `404`

---

### GET /recipes/complexSearch

**Search Recipes**

Search through hundreds of thousands of recipes using advanced filtering and ranking. NOTE: This method combines searching by query, by ingredients, and by nutrients into one endpoint.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `query` | query | string | yes | The (natural language) search query. (e.g. `burger`) |
| `cuisine` | query | string | no | The cuisine(s) of the recipes. One or more, comma separated (will be interpreted as 'OR'). See a full list of supported cuisines. (e.g. `italian`) |
| `excludeCuisine` | query | string | no | The cuisine(s) the recipes must not match. One or more, comma separated (will be interpreted as 'AND'). See a full list of supported cuisines. (e.g. `greek`) |
| `diet` | query | string | no | The diet for which the recipes must be suitable. See a full list of supported diets. (e.g. `vegetarian`) |
| `intolerances` | query | string | no | A comma-separated list of intolerances. All recipes returned must not contain ingredients that are not suitable for people with the intolerances entered. See a full list of supported intolerances. (e.g. `gluten`) |
| `equipment` | query | string | no | The equipment required. Multiple values will be interpreted as 'or'. For example, value could be "blender, frying pan, bowl". (e.g. `pan`) |
| `includeIngredients` | query | string | no | A comma-separated list of ingredients that should/must be used in the recipes. (e.g. `tomato,cheese`) |
| `excludeIngredients` | query | string | no | A comma-separated list of ingredients or ingredient types that the recipes must not contain. (e.g. `eggs`) |
| `type` | query | string | no | The type of recipe. See a full list of supported meal types. (e.g. `main course`) |
| `instructionsRequired` | query | boolean | no | Whether the recipes must have instructions. (e.g. `True`) |
| `fillIngredients` | query | boolean | no | Add information about the ingredients and whether they are used or missing in relation to the query. (e.g. `False`) |
| `addRecipeInformation` | query | boolean | no | If set to true, you get more information about the recipes returned. (e.g. `False`) |
| `addRecipeNutrition` | query | boolean | no | If set to true, you get nutritional information about each recipes returned. (e.g. `False`) |
| `author` | query | string | no | The username of the recipe author. (e.g. `coffeebean`) |
| `tags` | query | string | no | The tags (can be diets, meal types, cuisines, or intolerances) that the recipe must have. |
| `recipeBoxId` | query | integer | no | The id of the recipe box to which the search should be limited to. (e.g. `2468`) |
| `titleMatch` | query | string | no | Enter text that must be found in the title of the recipes. (e.g. `Crock Pot`) |
| `maxReadyTime` | query | number | no | The maximum time in minutes it should take to prepare and cook the recipe. (e.g. `20`) |
| `minServings` | query | number | no | The minimum amount of servings the recipe is for. (e.g. `1`) |
| `maxServings` | query | number | no | The maximum amount of servings the recipe is for. (e.g. `8`) |
| `ignorePantry` | query | boolean | no | Whether to ignore typical pantry items, such as water, salt, flour, etc. (e.g. `False`) |
| `sort` | query | string | no | The strategy to sort recipes by. See a full list of supported sorting options. (e.g. `calories`) |
| `sortDirection` | query | string | no | The direction in which to sort. Must be either 'asc' (ascending) or 'desc' (descending). (e.g. `asc`) |
| `minCarbs` | query | number | no | The minimum amount of carbohydrates in grams the recipe must have. (e.g. `10`) |
| `maxCarbs` | query | number | no | The maximum amount of carbohydrates in grams the recipe can have. (e.g. `100`) |
| `minProtein` | query | number | no | The minimum amount of protein in grams the recipe must have. (e.g. `10`) |
| `maxProtein` | query | number | no | The maximum amount of protein in grams the recipe can have. (e.g. `100`) |
| `minCalories` | query | number | no | The minimum amount of calories the recipe must have. (e.g. `50`) |
| `maxCalories` | query | number | no | The maximum amount of calories the recipe can have. (e.g. `800`) |
| `minFat` | query | number | no | The minimum amount of fat in grams the recipe must have. (e.g. `1`) |
| `maxFat` | query | number | no | The maximum amount of fat in grams the recipe can have. (e.g. `100`) |
| `minAlcohol` | query | number | no | The minimum amount of alcohol in grams the recipe must have. (e.g. `0`) |
| `maxAlcohol` | query | number | no | The maximum amount of alcohol in grams the recipe can have. (e.g. `100`) |
| `minCaffeine` | query | number | no | The minimum amount of caffeine in milligrams the recipe must have. (e.g. `0`) |
| `maxCaffeine` | query | number | no | The maximum amount of caffeine in milligrams the recipe can have. (e.g. `100`) |
| `minCopper` | query | number | no | The minimum amount of copper in milligrams the recipe must have. (e.g. `0`) |
| `maxCopper` | query | number | no | The maximum amount of copper in milligrams the recipe can have. (e.g. `100`) |
| `minCalcium` | query | number | no | The minimum amount of calcium in milligrams the recipe must have. (e.g. `0`) |
| `maxCalcium` | query | number | no | The maximum amount of calcium in milligrams the recipe can have. (e.g. `100`) |
| `minCholine` | query | number | no | The minimum amount of choline in milligrams the recipe must have. (e.g. `0`) |
| `maxCholine` | query | number | no | The maximum amount of choline in milligrams the recipe can have. (e.g. `100`) |
| `minCholesterol` | query | number | no | The minimum amount of cholesterol in milligrams the recipe must have. (e.g. `0`) |
| `maxCholesterol` | query | number | no | The maximum amount of cholesterol in milligrams the recipe can have. (e.g. `100`) |
| `minFluoride` | query | number | no | The minimum amount of fluoride in milligrams the recipe must have. (e.g. `0`) |
| `maxFluoride` | query | number | no | The maximum amount of fluoride in milligrams the recipe can have. (e.g. `100`) |
| `minSaturatedFat` | query | number | no | The minimum amount of saturated fat in grams the recipe must have. (e.g. `0`) |
| `maxSaturatedFat` | query | number | no | The maximum amount of saturated fat in grams the recipe can have. (e.g. `100`) |
| `minVitaminA` | query | number | no | The minimum amount of Vitamin A in IU the recipe must have. (e.g. `0`) |
| `maxVitaminA` | query | number | no | The maximum amount of Vitamin A in IU the recipe can have. (e.g. `100`) |
| `minVitaminC` | query | number | no | The minimum amount of Vitamin C milligrams the recipe must have. (e.g. `0`) |
| `maxVitaminC` | query | number | no | The maximum amount of Vitamin C in milligrams the recipe can have. (e.g. `100`) |
| `minVitaminD` | query | number | no | The minimum amount of Vitamin D in micrograms the recipe must have. (e.g. `0`) |
| `maxVitaminD` | query | number | no | The maximum amount of Vitamin D in micrograms the recipe can have. (e.g. `100`) |
| `minVitaminE` | query | number | no | The minimum amount of Vitamin E in milligrams the recipe must have. (e.g. `0`) |
| `maxVitaminE` | query | number | no | The maximum amount of Vitamin E in milligrams the recipe can have. (e.g. `100`) |
| `minVitaminK` | query | number | no | The minimum amount of Vitamin K in micrograms the recipe must have. (e.g. `0`) |
| `maxVitaminK` | query | number | no | The maximum amount of Vitamin K in micrograms the recipe can have. (e.g. `100`) |
| `minVitaminB1` | query | number | no | The minimum amount of Vitamin B1 in milligrams the recipe must have. (e.g. `0`) |
| `maxVitaminB1` | query | number | no | The maximum amount of Vitamin B1 in milligrams the recipe can have. (e.g. `100`) |
| `minVitaminB2` | query | number | no | The minimum amount of Vitamin B2 in milligrams the recipe must have. (e.g. `0`) |
| `maxVitaminB2` | query | number | no | The maximum amount of Vitamin B2 in milligrams the recipe can have. (e.g. `100`) |
| `minVitaminB5` | query | number | no | The minimum amount of Vitamin B5 in milligrams the recipe must have. (e.g. `0`) |
| `maxVitaminB5` | query | number | no | The maximum amount of Vitamin B5 in milligrams the recipe can have. (e.g. `100`) |
| `minVitaminB3` | query | number | no | The minimum amount of Vitamin B3 in milligrams the recipe must have. (e.g. `0`) |
| `maxVitaminB3` | query | number | no | The maximum amount of Vitamin B3 in milligrams the recipe can have. (e.g. `100`) |
| `minVitaminB6` | query | number | no | The minimum amount of Vitamin B6 in milligrams the recipe must have. (e.g. `0`) |
| `maxVitaminB6` | query | number | no | The maximum amount of Vitamin B6 in milligrams the recipe can have. (e.g. `100`) |
| `minVitaminB12` | query | number | no | The minimum amount of Vitamin B12 in micrograms the recipe must have. (e.g. `0`) |
| `maxVitaminB12` | query | number | no | The maximum amount of Vitamin B12 in micrograms the recipe can have. (e.g. `100`) |
| `minFiber` | query | number | no | The minimum amount of fiber in grams the recipe must have. (e.g. `0`) |
| `maxFiber` | query | number | no | The maximum amount of fiber in grams the recipe can have. (e.g. `100`) |
| `minFolate` | query | number | no | The minimum amount of folate in micrograms the recipe must have. (e.g. `0`) |
| `maxFolate` | query | number | no | The maximum amount of folate in micrograms the recipe can have. (e.g. `100`) |
| `minFolicAcid` | query | number | no | The minimum amount of folic acid in micrograms the recipe must have. (e.g. `0`) |
| `maxFolicAcid` | query | number | no | The maximum amount of folic acid in micrograms the recipe can have. (e.g. `100`) |
| `minIodine` | query | number | no | The minimum amount of iodine in micrograms the recipe must have. (e.g. `0`) |
| `maxIodine` | query | number | no | The maximum amount of iodine in micrograms the recipe can have. (e.g. `100`) |
| `minIron` | query | number | no | The minimum amount of iron in milligrams the recipe must have. (e.g. `0`) |
| `maxIron` | query | number | no | The maximum amount of iron in milligrams the recipe can have. (e.g. `100`) |
| `minMagnesium` | query | number | no | The minimum amount of magnesium in milligrams the recipe must have. (e.g. `0`) |
| `maxMagnesium` | query | number | no | The maximum amount of magnesium in milligrams the recipe can have. (e.g. `100`) |
| `minManganese` | query | number | no | The minimum amount of manganese in milligrams the recipe must have. (e.g. `0`) |
| `maxManganese` | query | number | no | The maximum amount of manganese in milligrams the recipe can have. (e.g. `100`) |
| `minPhosphorus` | query | number | no | The minimum amount of phosphorus in milligrams the recipe must have. (e.g. `0`) |
| `maxPhosphorus` | query | number | no | The maximum amount of phosphorus in milligrams the recipe can have. (e.g. `100`) |
| `minPotassium` | query | number | no | The minimum amount of potassium in milligrams the recipe must have. (e.g. `0`) |
| `maxPotassium` | query | number | no | The maximum amount of potassium in milligrams the recipe can have. (e.g. `100`) |
| `minSelenium` | query | number | no | The minimum amount of selenium in micrograms the recipe must have. (e.g. `0`) |
| `maxSelenium` | query | number | no | The maximum amount of selenium in micrograms the recipe can have. (e.g. `100`) |
| `minSodium` | query | number | no | The minimum amount of sodium in milligrams the recipe must have. (e.g. `0`) |
| `maxSodium` | query | number | no | The maximum amount of sodium in milligrams the recipe can have. (e.g. `100`) |
| `minSugar` | query | number | no | The minimum amount of sugar in grams the recipe must have. (e.g. `0`) |
| `maxSugar` | query | number | no | The maximum amount of sugar in grams the recipe can have. (e.g. `100`) |
| `minZinc` | query | number | no | The minimum amount of zinc in milligrams the recipe must have. (e.g. `0`) |
| `maxZinc` | query | number | no | The maximum amount of zinc in milligrams the recipe can have. (e.g. `100`) |
| `offset` | query | integer | no | The number of results to skip (between 0 and 900). |
| `number` | query | integer | no | The maximum number of items to return (between 1 and 100). Defaults to 10. (e.g. `10`) |

**Response 200** (`application/json`):

`object` {
  - `offset`*: `integer`
  - `number`*: `integer`
  - `results`*: `array<` `object` {
    - `id`*: `integer`
    - `title`*: `string`
    - `image`*: `string`
    - `imageType`*: `string`
  } `>`
  - `totalResults`*: `integer`
}

Other responses: `401`, `403`, `404`

---

### GET /recipes/convert

**Convert Amounts**

Convert amounts like "2 cups of flour to grams".

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `ingredientName` | query | string | yes | The ingredient which you want to convert. (e.g. `flour`) |
| `sourceAmount` | query | number | yes | The amount from which you want to convert, e.g. the 2.5 in "2.5 cups of flour to grams". (e.g. `2.5`) |
| `sourceUnit` | query | string | yes | The unit from which you want to convert, e.g. the grams in "2.5 cups of flour to grams". You can also use "piece", e.g. "3.4 oz tomatoes to piece" (e.g. `cups`) |
| `targetUnit` | query | string | yes | The unit to which you want to convert, e.g. the grams in "2.5 cups of flour to grams". You can also use "piece", e.g. "3.4 oz tomatoes to piece" (e.g. `grams`) |

**Response 200** (`application/json`):

`object` {
  - `sourceAmount`*: `number`
  - `sourceUnit`*: `string`
  - `targetAmount`*: `number`
  - `targetUnit`*: `string`
  - `answer`*: `string`
}

Other responses: `401`, `403`, `404`

---

### POST /recipes/cuisine

**Classify Cuisine**

Classify the recipe's cuisine.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `language` | query | string | no | The language of the input. Either 'en' or 'de'. (e.g. `en`) |

**Request body** (`application/x-www-form-urlencoded`):

`object` {
  - `title`*: `string`
  - `ingredientList`*: `string`
}

**Response 200** (`application/json`):

`object` {
  - `cuisine`*: `string`
  - `cuisines`*: `array<` `string` `>`
  - `confidence`*: `number`
}

Other responses: `401`, `403`, `404`

---

### GET /recipes/extract

**Extract Recipe from Website**

This endpoint lets you extract recipe data such as title, ingredients, and instructions from any properly formatted Website.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `url` | query | string | yes | The URL of the recipe page. (e.g. `https://foodista.com/recipe/ZHK4KPB6/chocolate-crinkle-cookies`) |
| `forceExtraction` | query | boolean | no | If true, the extraction will be triggered whether we already know the recipe or not. Use this only if information is missing as this operation is slower. (e.g. `True`) |
| `analyze` | query | boolean | no | If true, the recipe will be analyzed and classified resolving in more data such as cuisines, dish types, and more. (e.g. `False`) |
| `includeNutrition` | query | boolean | no | Include nutrition data in the recipe information. Nutrition data is per serving. If you want the nutrition data for the entire recipe, just multiply by the number of servings. |
| `includeTaste` | query | boolean | no | Whether taste data should be added to correctly parsed ingredients. (e.g. `False`) |

**Response 200** (`application/json`):

[`RecipeInformation`](#schema-recipeinformation)

Other responses: `401`, `403`, `404`

---

### GET /recipes/findByIngredients

**Search Recipes by Ingredients**


Ever wondered what recipes you can cook with the ingredients you have in your fridge or pantry? This endpoint lets you find recipes that either maximize the usage of ingredients you have at hand (pre shopping) or minimize the ingredients that you don't currently have (post shopping).
        

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `ingredients` | query | string | yes | A comma-separated list of ingredients that the recipes should contain. (e.g. `carrots,tomatoes`) |
| `number` | query | integer | no | The maximum number of items to return (between 1 and 100). Defaults to 10. (e.g. `10`) |
| `ranking` | query | integer | no | Whether to maximize used ingredients (1) or minimize missing ingredients (2) first. (e.g. `1`) |
| `ignorePantry` | query | boolean | no | Whether to ignore typical pantry items, such as water, salt, flour, etc. (e.g. `False`) |

**Response 200** (`application/json`):

`array<` `object` {
  - `id`*: `integer`
  - `image`*: `string`
  - `imageType`*: `string`
  - `likes`*: `integer`
  - `missedIngredientCount`*: `integer`
  - `missedIngredients`*: `array<` `object` {
    - `aisle`*: `string`
    - `amount`*: `number`
    - `id`*: `integer`
    - `image`*: `string`
    - `meta`: `array<` `string` `>`
    - `name`*: `string`
    - `extendedName`: `string`
    - `original`*: `string`
    - `originalName`*: `string`
    - `unit`*: `string`
    - `unitLong`*: `string`
    - `unitShort`*: `string`
  } `>`
  - `title`*: `string`
  - `unusedIngredients`*: `array<` `object` `>`
  - `usedIngredientCount`*: `number`
  - `usedIngredients`*: `array<` `object` {
    - `aisle`*: `string`
    - `amount`*: `number`
    - `id`*: `integer`
    - `image`*: `string`
    - `meta`: `array<` `string` `>`
    - `name`*: `string`
    - `extendedName`: `string`
    - `original`*: `string`
    - `originalName`*: `string`
    - `unit`*: `string`
    - `unitLong`*: `string`
    - `unitShort`*: `string`
  } `>`
} `>`

Other responses: `401`, `403`, `404`

---

### GET /recipes/findByNutrients

**Search Recipes by Nutrients**

Find a set of recipes that adhere to the given nutritional limits. You may set limits for macronutrients (calories, protein, fat, and carbohydrate) and/or many micronutrients.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `minCarbs` | query | number | no | The minimum amount of carbohydrates in grams the recipe must have. (e.g. `10`) |
| `maxCarbs` | query | number | no | The maximum amount of carbohydrates in grams the recipe can have. (e.g. `100`) |
| `minProtein` | query | number | no | The minimum amount of protein in grams the recipe must have. (e.g. `10`) |
| `maxProtein` | query | number | no | The maximum amount of protein in grams the recipe can have. (e.g. `100`) |
| `minCalories` | query | number | no | The minimum amount of calories the recipe must have. (e.g. `50`) |
| `maxCalories` | query | number | no | The maximum amount of calories the recipe can have. (e.g. `800`) |
| `minFat` | query | number | no | The minimum amount of fat in grams the recipe must have. (e.g. `1`) |
| `maxFat` | query | number | no | The maximum amount of fat in grams the recipe can have. (e.g. `100`) |
| `minAlcohol` | query | number | no | The minimum amount of alcohol in grams the recipe must have. (e.g. `0`) |
| `maxAlcohol` | query | number | no | The maximum amount of alcohol in grams the recipe can have. (e.g. `100`) |
| `minCaffeine` | query | number | no | The minimum amount of caffeine in milligrams the recipe must have. (e.g. `0`) |
| `maxCaffeine` | query | number | no | The maximum amount of caffeine in milligrams the recipe can have. (e.g. `100`) |
| `minCopper` | query | number | no | The minimum amount of copper in milligrams the recipe must have. (e.g. `0`) |
| `maxCopper` | query | number | no | The maximum amount of copper in milligrams the recipe can have. (e.g. `100`) |
| `minCalcium` | query | number | no | The minimum amount of calcium in milligrams the recipe must have. (e.g. `0`) |
| `maxCalcium` | query | number | no | The maximum amount of calcium in milligrams the recipe can have. (e.g. `100`) |
| `minCholine` | query | number | no | The minimum amount of choline in milligrams the recipe must have. (e.g. `0`) |
| `maxCholine` | query | number | no | The maximum amount of choline in milligrams the recipe can have. (e.g. `100`) |
| `minCholesterol` | query | number | no | The minimum amount of cholesterol in milligrams the recipe must have. (e.g. `0`) |
| `maxCholesterol` | query | number | no | The maximum amount of cholesterol in milligrams the recipe can have. (e.g. `100`) |
| `minFluoride` | query | number | no | The minimum amount of fluoride in milligrams the recipe must have. (e.g. `0`) |
| `maxFluoride` | query | number | no | The maximum amount of fluoride in milligrams the recipe can have. (e.g. `100`) |
| `minSaturatedFat` | query | number | no | The minimum amount of saturated fat in grams the recipe must have. (e.g. `0`) |
| `maxSaturatedFat` | query | number | no | The maximum amount of saturated fat in grams the recipe can have. (e.g. `100`) |
| `minVitaminA` | query | number | no | The minimum amount of Vitamin A in IU the recipe must have. (e.g. `0`) |
| `maxVitaminA` | query | number | no | The maximum amount of Vitamin A in IU the recipe can have. (e.g. `100`) |
| `minVitaminC` | query | number | no | The minimum amount of Vitamin C in milligrams the recipe must have. (e.g. `0`) |
| `maxVitaminC` | query | number | no | The maximum amount of Vitamin C in milligrams the recipe can have. (e.g. `100`) |
| `minVitaminD` | query | number | no | The minimum amount of Vitamin D in micrograms the recipe must have. (e.g. `0`) |
| `maxVitaminD` | query | number | no | The maximum amount of Vitamin D in micrograms the recipe can have. (e.g. `100`) |
| `minVitaminE` | query | number | no | The minimum amount of Vitamin E in milligrams the recipe must have. (e.g. `0`) |
| `maxVitaminE` | query | number | no | The maximum amount of Vitamin E in milligrams the recipe can have. (e.g. `100`) |
| `minVitaminK` | query | number | no | The minimum amount of Vitamin K in micrograms the recipe must have. (e.g. `0`) |
| `maxVitaminK` | query | number | no | The maximum amount of Vitamin K in micrograms the recipe can have. (e.g. `100`) |
| `minVitaminB1` | query | number | no | The minimum amount of Vitamin B1 in milligrams the recipe must have. (e.g. `0`) |
| `maxVitaminB1` | query | number | no | The maximum amount of Vitamin B1 in milligrams the recipe can have. (e.g. `100`) |
| `minVitaminB2` | query | number | no | The minimum amount of Vitamin B2 in milligrams the recipe must have. (e.g. `0`) |
| `maxVitaminB2` | query | number | no | The maximum amount of Vitamin B2 in milligrams the recipe can have. (e.g. `100`) |
| `minVitaminB5` | query | number | no | The minimum amount of Vitamin B5 in milligrams the recipe must have. (e.g. `0`) |
| `maxVitaminB5` | query | number | no | The maximum amount of Vitamin B5 in milligrams the recipe can have. (e.g. `100`) |
| `minVitaminB3` | query | number | no | The minimum amount of Vitamin B3 in milligrams the recipe must have. (e.g. `0`) |
| `maxVitaminB3` | query | number | no | The maximum amount of Vitamin B3 in milligrams the recipe can have. (e.g. `100`) |
| `minVitaminB6` | query | number | no | The minimum amount of Vitamin B6 in milligrams the recipe must have. (e.g. `0`) |
| `maxVitaminB6` | query | number | no | The maximum amount of Vitamin B6 in milligrams the recipe can have. (e.g. `100`) |
| `minVitaminB12` | query | number | no | The minimum amount of Vitamin B12 in micrograms the recipe must have. (e.g. `0`) |
| `maxVitaminB12` | query | number | no | The maximum amount of Vitamin B12 in micrograms the recipe can have. (e.g. `100`) |
| `minFiber` | query | number | no | The minimum amount of fiber in grams the recipe must have. (e.g. `0`) |
| `maxFiber` | query | number | no | The maximum amount of fiber in grams the recipe can have. (e.g. `100`) |
| `minFolate` | query | number | no | The minimum amount of folate in micrograms the recipe must have. (e.g. `0`) |
| `maxFolate` | query | number | no | The maximum amount of folate in micrograms the recipe can have. (e.g. `100`) |
| `minFolicAcid` | query | number | no | The minimum amount of folic acid in micrograms the recipe must have. (e.g. `0`) |
| `maxFolicAcid` | query | number | no | The maximum amount of folic acid in micrograms the recipe can have. (e.g. `100`) |
| `minIodine` | query | number | no | The minimum amount of iodine in micrograms the recipe must have. (e.g. `0`) |
| `maxIodine` | query | number | no | The maximum amount of iodine in micrograms the recipe can have. (e.g. `100`) |
| `minIron` | query | number | no | The minimum amount of iron in milligrams the recipe must have. (e.g. `0`) |
| `maxIron` | query | number | no | The maximum amount of iron in milligrams the recipe can have. (e.g. `100`) |
| `minMagnesium` | query | number | no | The minimum amount of magnesium in milligrams the recipe must have. (e.g. `0`) |
| `maxMagnesium` | query | number | no | The maximum amount of magnesium in milligrams the recipe can have. (e.g. `100`) |
| `minManganese` | query | number | no | The minimum amount of manganese in milligrams the recipe must have. (e.g. `0`) |
| `maxManganese` | query | number | no | The maximum amount of manganese in milligrams the recipe can have. (e.g. `100`) |
| `minPhosphorus` | query | number | no | The minimum amount of phosphorus in milligrams the recipe must have. (e.g. `0`) |
| `maxPhosphorus` | query | number | no | The maximum amount of phosphorus in milligrams the recipe can have. (e.g. `100`) |
| `minPotassium` | query | number | no | The minimum amount of potassium in milligrams the recipe must have. (e.g. `0`) |
| `maxPotassium` | query | number | no | The maximum amount of potassium in milligrams the recipe can have. (e.g. `100`) |
| `minSelenium` | query | number | no | The minimum amount of selenium in micrograms the recipe must have. (e.g. `0`) |
| `maxSelenium` | query | number | no | The maximum amount of selenium in micrograms the recipe can have. (e.g. `100`) |
| `minSodium` | query | number | no | The minimum amount of sodium in milligrams the recipe must have. (e.g. `0`) |
| `maxSodium` | query | number | no | The maximum amount of sodium in milligrams the recipe can have. (e.g. `100`) |
| `minSugar` | query | number | no | The minimum amount of sugar in grams the recipe must have. (e.g. `0`) |
| `maxSugar` | query | number | no | The maximum amount of sugar in grams the recipe can have. (e.g. `100`) |
| `minZinc` | query | number | no | The minimum amount of zinc in milligrams the recipe must have. (e.g. `0`) |
| `maxZinc` | query | number | no | The maximum amount of zinc in milligrams the recipe can have. (e.g. `100`) |
| `offset` | query | integer | no | The number of results to skip (between 0 and 900). |
| `number` | query | integer | no | The maximum number of items to return (between 1 and 100). Defaults to 10. (e.g. `10`) |
| `random` | query | boolean | no | If true, every request will give you a random set of recipes within the requested limits. (e.g. `False`) |

**Response 200** (`application/json`):

`array<` `object` {
  - `calories`*: `number`
  - `carbs`*: `string`
  - `fat`*: `string`
  - `id`*: `integer`
  - `image`*: `string`
  - `imageType`*: `string`
  - `protein`*: `string`
  - `title`*: `string`
} `>`

Other responses: `401`, `403`, `404`

---

### GET /recipes/guessNutrition

**Guess Nutrition by Dish Name**

Estimate the macronutrients of a dish based on its title.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `title` | query | string | yes | The title of the dish. (e.g. `Spaghetti Aglio et Olio`) |

**Response 200** (`application/json`):

`object` {
  - `calories`*: `object` {
    - `confidenceRange95Percent`*: `object` {
      - `max`*: `number`
      - `min`*: `number`
    }
    - `standardDeviation`*: `number`
    - `unit`*: `string`
    - `value`*: `number`
  }
  - `carbs`*: `object` {
    - `confidenceRange95Percent`*: `object` {
      - `max`*: `number`
      - `min`*: `number`
    }
    - `standardDeviation`*: `number`
    - `unit`*: `string`
    - `value`*: `number`
  }
  - `fat`*: `object` {
    - `confidenceRange95Percent`*: `object` {
      - `max`*: `number`
      - `min`*: `number`
    }
    - `standardDeviation`*: `number`
    - `unit`*: `string`
    - `value`*: `number`
  }
  - `protein`*: `object` {
    - `confidenceRange95Percent`*: `object` {
      - `max`*: `number`
      - `min`*: `number`
    }
    - `standardDeviation`*: `number`
    - `unit`*: `string`
    - `value`*: `number`
  }
  - `recipesUsed`*: `integer`
}

Other responses: `401`, `403`, `404`

---

### GET /recipes/informationBulk

**Get Recipe Information Bulk**

Get information about multiple recipes at once. This is equivalent to calling the Get Recipe Information endpoint multiple times, but faster.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `ids` | query | string | yes | A comma-separated list of recipe ids. (e.g. `715538,716429`) |
| `includeNutrition` | query | boolean | no | Include nutrition data in the recipe information. Nutrition data is per serving. If you want the nutrition data for the entire recipe, just multiply by the number of servings. |

**Response 200** (`application/json`):

`array<` [`RecipeInformation`](#schema-recipeinformation) `>`

Other responses: `401`, `403`, `404`

---

### POST /recipes/parseIngredients

**Parse Ingredients**

Extract an ingredient from plain text.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `language` | query | string | no | The language of the input. Either 'en' or 'de'. (e.g. `en`) |

**Request body** (`application/x-www-form-urlencoded`):

`object` {
  - `ingredientList`*: `string`
  - `servings`*: `number`
  - `includeNutrition`: `boolean`
}

**Response 200** (`application/json`):

`array<` [`IngredientInformation`](#schema-ingredientinformation) `>`

Other responses: `401`, `403`, `404`

---

### GET /recipes/queries/analyze

**Analyze a Recipe Search Query**

Parse a recipe search query to find out its intention.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `q` | query | string | yes | The recipe search query. (e.g. `salmon with fusilli and no nuts`) |

**Response 200** (`application/json`):

`object` {
  - `dishes`*: `array<` `object` {
    - `image`*: `string`
    - `name`*: `string`
  } `>`
  - `ingredients`*: `array<` `object` {
    - `image`*: `string`
    - `include`*: `boolean`
    - `name`*: `string`
  } `>`
  - `cuisines`*: `array<` `string` `>`
  - `modifiers`*: `array<` `string` `>`
}

Other responses: `401`, `403`, `404`

---

### GET /recipes/quickAnswer

**Quick Answer**

Answer a nutrition related natural language question.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `q` | query | string | yes | The nutrition related question. (e.g. `How much vitamin c is in 2 apples?`) |

**Response 200** (`application/json`):

`object` {
  - `answer`*: `string`
  - `image`*: `string`
}

Other responses: `401`, `403`, `404`

---

### GET /recipes/random

**Get Random Recipes**

Find random (popular) recipes. If you need to filter recipes by diet, nutrition etc. you might want to consider using the complex recipe search endpoint and set the sort request parameter to random.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `includeNutrition` | query | boolean | no | Include nutrition data in the recipe information. Nutrition data is per serving. If you want the nutrition data for the entire recipe, just multiply by the number of servings. |
| `include-tags` | query | string | no | A comma-separated list of tags that the random recipe(s) must adhere to. (e.g. `vegetarian,gluten`) |
| `exclude-tags` | query | string | no | A comma-separated list of tags that the random recipe(s) must not adhere to. (e.g. `meat,dairy`) |
| `number` | query | integer | no | The maximum number of items to return (between 1 and 100). Defaults to 10. (e.g. `10`) |

**Response 200** (`application/json`):

`object` {
  - `recipes`*: `array<` [`RecipeInformation`](#schema-recipeinformation) `>`
}

Other responses: `401`, `403`, `404`

---

### POST /recipes/visualizeEquipment

**Equipment Widget**

Visualize the equipment used to make a recipe.

_No parameters._

**Request body** (`application/x-www-form-urlencoded`):

`object` {
  - `instructions`*: `string`
  - `view`: `string`
  - `defaultCss`: `boolean`
  - `showBacklink`: `boolean`
}

**Response 200** (`text/html`):

`string`

Other responses: `401`, `403`, `404`

---

### POST /recipes/visualizeNutrition

**Recipe Nutrition Widget**

Visualize a recipe's nutritional information as HTML including CSS.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `language` | query | string | no | The language of the input. Either 'en' or 'de'. (e.g. `en`) |

**Request body** (`application/x-www-form-urlencoded`):

`object` {
  - `ingredientList`*: `string`
  - `servings`*: `number`
  - `defaultCss`: `boolean`
  - `showBacklink`: `boolean`
}

**Response 200** (`text/html`):

`string`

Other responses: `401`, `403`, `404`

---

### POST /recipes/visualizePriceEstimator

**Price Breakdown Widget**

Visualize the price breakdown of a recipe.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `language` | query | string | no | The language of the input. Either 'en' or 'de'. (e.g. `en`) |

**Request body** (`application/x-www-form-urlencoded`):

`object` {
  - `ingredientList`*: `string`
  - `servings`*: `number`
  - `mode`: `number`
  - `defaultCss`: `boolean`
  - `showBacklink`: `boolean`
}

**Response 200** (`text/html`):

`string`

Other responses: `401`, `403`, `404`

---

### POST /recipes/visualizeRecipe

**Create Recipe Card**

Generate a recipe card for a recipe.

_No parameters._

**Request body** (`multipart/form-data`):

`object` {
  - `title`*: `string`
  - `ingredients`*: `string`
  - `instructions`*: `string`
  - `readyInMinutes`*: `number`
  - `servings`*: `number`
  - `mask`*: `string`
  - `backgroundImage`*: `string`
  - `image`: `string` (binary)
  - `imageUrl`: `string`
  - `author`: `string`
  - `backgroundColor`: `string`
  - `fontColor`: `string`
  - `source`: `string`
}

**Response 200** (`application/json`):

`object` {
  - `url`*: `string`
}

Other responses: `401`, `403`, `404`

---

### POST /recipes/visualizeTaste

**Recipe Taste Widget**

Visualize a recipe's taste information as HTML including CSS. You can play around with that endpoint!

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `language` | query | string | no | The language of the input. Either 'en' or 'de'. (e.g. `en`) |

**Request body** (`application/x-www-form-urlencoded`):

`object` {
  - `ingredientList`*: `string`
  - `normalize`: `boolean`
  - `rgb`: `string`
}

**Response 200** (`text/html`):

`string`

Other responses: `401`, `403`, `404`

---

### GET /recipes/{id}/analyzedInstructions

**Get Analyzed Recipe Instructions**

Get an analyzed breakdown of a recipe's instructions. Each step is enriched with the ingredients and equipment required.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `id` | path | integer | yes | The recipe id. (e.g. `324694`) |
| `stepBreakdown` | query | boolean | no | Whether to break down the recipe steps even more. (e.g. `True`) |

**Response 200** (`application/json`):

`array<` `object` {
  - `name`*: `string`
  - `steps`: `array<` `object` {
    - `number`*: `number`
    - `step`*: `string`
    - `ingredients`: `array<` `object` {
      - `id`*: `integer`
      - `name`*: `string`
      - `localizedName`*: `string`
      - `image`*: `string`
    } `>`
    - `equipment`: `array<` `object` {
      - `id`*: `integer`
      - `name`*: `string`
      - `localizedName`*: `string`
      - `image`*: `string`
    } `>`
  } `>`
} `>`

Other responses: `401`, `403`, `404`

---

### GET /recipes/{id}/equipmentWidget

**Equipment by ID Widget**

Visualize a recipe's equipment list.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `id` | path | integer | yes | The recipe id. (e.g. `44860`) |
| `defaultCss` | query | boolean | no | Whether the default CSS should be added to the response. (e.g. `False`) |

**Response 200** (`text/html`):

`string`

Other responses: `401`, `403`, `404`

---

### GET /recipes/{id}/equipmentWidget.json

**Equipment by ID**

Get a recipe's equipment list.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `id` | path | integer | yes | The recipe id. (e.g. `1003464`) |

**Response 200** (`application/json`):

`object` {
  - `equipment`*: `array<` `object` {
    - `image`*: `string`
    - `name`*: `string`
  } `>`
}

Other responses: `401`, `403`, `404`

---

### GET /recipes/{id}/equipmentWidget.png

**Equipment by ID Image**

Visualize a recipe's equipment list as an image.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `id` | path | integer | yes | The recipe id. (e.g. `44860`) |

**Response 200** (`image/png`):

`string` (binary)

Other responses: `401`, `403`, `404`

---

### GET /recipes/{id}/information

**Get Recipe Information**

Use a recipe id to get full information about a recipe, such as ingredients, nutrition, diet and allergen information, etc.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `id` | path | integer | yes | The id of the recipe. (e.g. `716429`) |
| `includeNutrition` | query | boolean | no | Include nutrition data in the recipe information. Nutrition data is per serving. If you want the nutrition data for the entire recipe, just multiply by the number of servings. |
| `addWinePairing` | query | boolean | no | Add a wine pairing to the recipe. (e.g. `False`) |
| `addTasteData` | query | boolean | no | Add taste data to the recipe. (e.g. `False`) |

**Response 200** (`application/json`):

[`RecipeInformation`](#schema-recipeinformation)

Other responses: `401`, `403`, `404`

---

### GET /recipes/{id}/ingredientWidget

**Ingredients by ID Widget**

Visualize a recipe's ingredient list.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `id` | path | integer | yes | The recipe id. (e.g. `1082038`) |
| `defaultCss` | query | boolean | no | Whether the default CSS should be added to the response. (e.g. `False`) |
| `measure` | query | string | no | Whether the the measures should be 'us' or 'metric'. (e.g. `metric`) |

**Response 200** (`text/html`):

`string`

Other responses: `401`, `403`, `404`

---

### GET /recipes/{id}/ingredientWidget.json

**Ingredients by ID**

Get a recipe's ingredient list.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `id` | path | integer | yes | The recipe id. (e.g. `1003464`) |

**Response 200** (`application/json`):

`object` {
  - `ingredients`*: `array<` `object` {
    - `amount`: `object` {
      - `metric`*: `object{...}`
      - `us`*: `object{...}`
    }
    - `image`*: `string`
    - `name`*: `string`
  } `>`
}

Other responses: `401`, `403`, `404`

---

### GET /recipes/{id}/nutritionLabel

**Recipe Nutrition Label Widget**

Get a recipe's nutrition label as an HTML widget.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `id` | path | integer | yes | The recipe id. (e.g. `641166`) |
| `defaultCss` | query | boolean | no | Whether the default CSS should be added to the response. (e.g. `False`) |
| `showOptionalNutrients` | query | boolean | no | Whether to show optional nutrients. (e.g. `False`) |
| `showZeroValues` | query | boolean | no | Whether to show zero values. (e.g. `False`) |
| `showIngredients` | query | boolean | no | Whether to show a list of ingredients. (e.g. `False`) |

**Response 200** (`text/html`):

`string`

Other responses: `401`, `403`, `404`

---

### GET /recipes/{id}/nutritionLabel.png

**Recipe Nutrition Label Image**

Get a recipe's nutrition label as an image.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `id` | path | integer | yes | The recipe id. (e.g. `641166`) |
| `showOptionalNutrients` | query | boolean | no | Whether to show optional nutrients. (e.g. `False`) |
| `showZeroValues` | query | boolean | no | Whether to show zero values. (e.g. `False`) |
| `showIngredients` | query | boolean | no | Whether to show a list of ingredients. (e.g. `False`) |

**Response 200** (`image/png`):

`string` (binary)

Other responses: `401`, `403`, `404`

---

### GET /recipes/{id}/nutritionWidget

**Recipe Nutrition by ID Widget**

Visualize a recipe's nutritional information as HTML including CSS.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `id` | path | integer | yes | The recipe id. (e.g. `1082038`) |
| `defaultCss` | query | boolean | no | Whether the default CSS should be added to the response. (e.g. `False`) |

**Response 200** (`text/html`):

`string`

Other responses: `401`, `403`, `404`

---

### GET /recipes/{id}/nutritionWidget.json

**Nutrition by ID**

Get a recipe's nutrition data.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `id` | path | integer | yes | The recipe id. (e.g. `1003464`) |

**Response 200** (`application/json`):

`object` {
  - `calories`*: `string`
  - `carbs`*: `string`
  - `fat`*: `string`
  - `protein`*: `string`
  - `bad`*: `array<` `object` {
    - `title`*: `string`
    - `amount`*: `string`
    - `indented`*: `boolean`
    - `percentOfDailyNeeds`*: `number`
  } `>`
  - `good`*: `array<` `object` {
    - `amount`*: `string`
    - `indented`*: `boolean`
    - `percentOfDailyNeeds`*: `number`
    - `title`*: `string`
  } `>`
}

Other responses: `401`, `403`, `404`

---

### GET /recipes/{id}/nutritionWidget.png

**Recipe Nutrition by ID Image**

Visualize a recipe's nutritional information as an image.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `id` | path | integer | yes | The recipe id. (e.g. `1082038`) |

**Response 200** (`image/png`):

`string` (binary)

Other responses: `401`, `403`, `404`

---

### GET /recipes/{id}/priceBreakdownWidget

**Price Breakdown by ID Widget**

Visualize a recipe's price breakdown.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `id` | path | integer | yes | The recipe id. (e.g. `1082038`) |
| `defaultCss` | query | boolean | no | Whether the default CSS should be added to the response. (e.g. `False`) |

**Response 200** (`text/html`):

`string`

Other responses: `401`, `403`, `404`

---

### GET /recipes/{id}/priceBreakdownWidget.json

**Price Breakdown by ID**

Get a recipe's price breakdown data.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `id` | path | integer | yes | The recipe id. (e.g. `1003464`) |

**Response 200** (`application/json`):

`object` {
  - `ingredients`*: `array<` `object` {
    - `amount`: `object` {
      - `metric`*: `object{...}`
      - `us`*: `object{...}`
    }
    - `image`*: `string`
    - `name`*: `string`
    - `price`*: `number`
  } `>`
  - `totalCost`*: `number`
  - `totalCostPerServing`*: `number`
}

Other responses: `401`, `403`, `404`

---

### GET /recipes/{id}/priceBreakdownWidget.png

**Price Breakdown by ID Image**

Visualize a recipe's price breakdown.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `id` | path | integer | yes | The recipe id. (e.g. `1082038`) |

**Response 200** (`image/png`):

`string` (binary)

Other responses: `401`, `403`, `404`

---

### GET /recipes/{id}/similar

**Get Similar Recipes**

Find recipes which are similar to the given one.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `id` | path | integer | yes | The id of the source recipe for which similar recipes should be found. (e.g. `715538`) |
| `number` | query | integer | no | The maximum number of items to return (between 1 and 100). Defaults to 10. (e.g. `10`) |

**Response 200** (`application/json`):

`array<` `object` {
  - `id`*: `integer`
  - `title`*: `string`
  - `imageType`*: `string`
  - `readyInMinutes`*: `integer`
  - `servings`*: `number`
  - `sourceUrl`*: `string`
} `>`

Other responses: `401`, `403`, `404`

---

### GET /recipes/{id}/summary

**Summarize Recipe**

Automatically generate a short description that summarizes key information about the recipe.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `id` | path | integer | yes | The recipe id. (e.g. `4632`) |

**Response 200** (`application/json`):

`object` {
  - `id`*: `integer`
  - `summary`*: `string`
  - `title`*: `string`
}

Other responses: `401`, `403`, `404`

---

### GET /recipes/{id}/tasteWidget

**Recipe Taste by ID Widget**

Get a recipe's taste. The tastes supported are sweet, salty, sour, bitter, savory, and fatty.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `id` | path | integer | yes | The recipe id. (e.g. `69095`) |
| `normalize` | query | boolean | no | Whether to normalize to the strongest taste. (e.g. `True`) |
| `rgb` | query | string | no | Red, green, blue values for the chart color. (e.g. `75,192,192`) |

**Response 200** (`text/html`):

`string`

Other responses: `401`, `403`, `404`

---

### GET /recipes/{id}/tasteWidget.json

**Taste by ID**

Get a recipe's taste. The tastes supported are sweet, salty, sour, bitter, savory, and fatty.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `id` | path | integer | yes | The recipe id. (e.g. `69095`) |
| `normalize` | query | boolean | no | Normalize to the strongest taste. (e.g. `True`) |

**Response 200** (`application/json`):

[`TasteInformation`](#schema-tasteinformation)

Other responses: `401`, `403`, `404`

---

### GET /recipes/{id}/tasteWidget.png

**Recipe Taste by ID Image**

Get a recipe's taste as an image. The tastes supported are sweet, salty, sour, bitter, savory, and fatty.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `id` | path | integer | yes | The recipe id. (e.g. `69095`) |
| `normalize` | query | boolean | no | Normalize to the strongest taste. (e.g. `False`) |
| `rgb` | query | string | no | Red, green, blue values for the chart color. (e.g. `75,192,192`) |

**Response 200** (`image/png`):

`string` (binary)

Other responses: `401`, `403`, `404`

---

## untagged

### GET /food/restaurants/search

**Search Restaurants**

Search through thousands of restaurants (in North America) by location, cuisine, budget, and more.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `query` | query | string | no | The search query. (e.g. `beach cafe`) |
| `lat` | query | number | no | The latitude of the user's location. (e.g. `37.7786357`) |
| `lng` | query | number | no | The longitude of the user's location.". (e.g. `-122.3918135`) |
| `distance` | query | number | no | The distance around the location in miles. (e.g. `2`) |
| `budget` | query | number | no | The user's budget for a meal in USD. (e.g. `20`) |
| `cuisine` | query | string | no | The cuisine of the restaurant. (e.g. `italian`) |
| `min-rating` | query | number | no | The minimum rating of the restaurant between 0 and 5. (e.g. `4.4`) |
| `is-open` | query | boolean | no | Whether the restaurant must be open at the time of search. (e.g. `True`) |
| `sort` | query | string | no | How to sort the results, one of the following 'cheapest', 'fastest', 'rating', 'distance' or the default 'relevance'. (e.g. `distance`) |
| `page` | query | number | no | The page number of results. (e.g. `0`) |

**Response 200** (`application/json`):

`object` {
  - `restaurants`: `array<` `object` {
    - `_id`: `string`
    - `name`: `string`
    - `phone_number`: `integer`
    - `address`: `object` {
      - `street_addr`: `string`
      - `city`: `string`
      - `state`: `string`
      - `zipcode`: `string`
      - `country`: `string`
      - `lat`: `number`
      - `lon`: `number`
      - `street_addr_2`: `string`
      - `latitude`: `number`
      - `longitude`: `number`
    }
    - `type`: `string`
    - `description`: `string`
    - `local_hours`: `object` {
      - `operational`: `object{...}`
      - `delivery`: `object{...}`
      - `pickup`: `object{...}`
      - `dine_in`: `object{...}`
    }
    - `cuisines`: `array<` `string` `>`
    - `food_photos`: `array<` `string` `>`
    - `logo_photos`: `array<` `string` `>`
    - `store_photos`: `array<` `string` `>`
    - `dollar_signs`: `integer`
    - `pickup_enabled`: `boolean`
    - `delivery_enabled`: `boolean`
    - `is_open`: `boolean`
    - `offers_first_party_delivery`: `boolean`
    - `offers_third_party_delivery`: `boolean`
    - `miles`: `number`
    - `weighted_rating_value`: `number`
    - `aggregated_rating_count`: `integer`
  } `>`
}

Other responses: `401`, `403`, `404`

---

### POST /recipes/analyze

**Analyze Recipe**

This endpoint allows you to send raw recipe information, such as title, servings, and ingredients, to then see what we compute (badges, diets, nutrition, and more). This is useful if you have your own recipe data and want to enrich it with our semantic analysis.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `language` | query | string | no | The input language, either "en" or "de". (e.g. `en`) |
| `includeNutrition` | query | boolean | no | Whether nutrition data should be added to correctly parsed ingredients. (e.g. `False`) |
| `includeTaste` | query | boolean | no | Whether taste data should be added to correctly parsed ingredients. (e.g. `False`) |

**Request body** (`application/json`):

`object` {
  - `title`: `string`
  - `servings`: `integer`
  - `ingredients`: `array<` `string` `>`
  - `instructions`: `string`
}

**Response 200** (`application/json`):

`object`

Other responses: `401`, `403`, `404`

---

### GET /recipes/{id}/card

**Create Recipe Card**

Generate a recipe card for a recipe.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `id` | path | integer | yes | The recipe id. (e.g. `4632`) |
| `mask` | query | string | no | The mask to put over the recipe image ("ellipseMask", "diamondMask", "starMask", "heartMask", "potMask", "fishMask"). (e.g. `ellipseMask`) |
| `backgroundImage` | query | string | no | The background image ("none","background1", or "background2"). (e.g. `background1`) |
| `backgroundColor` | query | string | no | The background color for the recipe card as a hex-string. (e.g. `ffffff`) |
| `fontColor` | query | string | no | The font color for the recipe card as a hex-string. (e.g. `333333`) |

**Response 200** (`application/json`):

`object`

Other responses: `401`, `403`, `404`

---

## wine

### GET /food/wine/description

**Wine Description**

Get a simple description of a certain wine, e.g. "malbec", "riesling", or "merlot".

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `wine` | query | string | yes | The name of the wine that should be paired, e.g. "merlot", "riesling", or "malbec". (e.g. `merlot`) |

**Response 200** (`application/json`):

`object` {
  - `wineDescription`*: `string`
}

Other responses: `401`, `403`, `404`

---

### GET /food/wine/dishes

**Dish Pairing for Wine**

Find a dish that goes well with a given wine.

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `wine` | query | string | yes | The type of wine that should be paired, e.g. "merlot", "riesling", or "malbec". (e.g. `malbec`) |

**Response 200** (`application/json`):

`object` {
  - `pairings`*: `array<` `string` `>`
  - `text`*: `string`
}

Other responses: `401`, `403`, `404`

---

### GET /food/wine/pairing

**Wine Pairing**

Find a wine that goes well with a food. Food can be a dish name ("steak"), an ingredient name ("salmon"), or a cuisine ("italian").

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `food` | query | string | yes | The food to get a pairing for. This can be a dish ("steak"), an ingredient ("salmon"), or a cuisine ("italian"). (e.g. `steak`) |
| `maxPrice` | query | number | no | The maximum price for the specific wine recommendation in USD. (e.g. `50`) |

**Response 200** (`application/json`):

`object` {
  - `pairedWines`*: `array<` `string` `>`
  - `pairingText`*: `string`
  - `productMatches`*: `array<` `object` {
    - `id`*: `integer`
    - `title`*: `string`
    - `averageRating`*: `number`
    - `description`: `string`
    - `imageUrl`*: `string`
    - `link`*: `string`
    - `price`*: `string`
    - `ratingCount`*: `integer`
    - `score`*: `number`
  } `>`
}

Other responses: `401`, `403`, `404`

---

### GET /food/wine/recommendation

**Wine Recommendation**

Get a specific wine recommendation (concrete product) for a given wine type, e.g. "merlot".

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `wine` | query | string | yes | The type of wine to get a specific product recommendation for. (e.g. `merlot`) |
| `maxPrice` | query | number | no | The maximum price for the specific wine recommendation in USD. (e.g. `50`) |
| `minRating` | query | number | no | The minimum rating of the recommended wine between 0 and 1. For example, 0.8 equals 4 out of 5 stars. (e.g. `0.7`) |
| `number` | query | number | no | The number of wine recommendations expected (between 1 and 100). (e.g. `3`) |

**Response 200** (`application/json`):

`object` {
  - `recommendedWines`*: `array<` `object` {
    - `id`*: `integer`
    - `title`*: `string`
    - `averageRating`*: `number`
    - `description`*: `string`
    - `imageUrl`*: `string`
    - `link`*: `string`
    - `price`*: `string`
    - `ratingCount`*: `integer`
    - `score`*: `number`
  } `>`
  - `totalFound`*: `integer`
}

Other responses: `401`, `403`, `404`

---

## Named schemas

### Schema: SearchResult

`object` {
  - `image`: `string`
  - `link`: `string`
  - `name`*: `string`
  - `type`: `string`
  - `kvtable`: `string`
  - `content`: `string`
  - `id`: `integer`
  - `relevance`: `number`
}

### Schema: ProductInformation

`object` {
  - `id`*: `integer`
  - `title`*: `string`
  - `upc`: `string`
  - `usdaCode`: `string`
  - `breadcrumbs`*: `array<` `string` `>`
  - `imageType`*: `string`
  - `badges`*: `array<` `string` `>`
  - `importantBadges`*: `array<` `string` `>`
  - `ingredientCount`*: `integer`
  - `generatedText`: `string`
  - `ingredientList`*: `string`
  - `ingredients`*: `array<` [`IngredientBasics`](#schema-ingredientbasics) `>`
  - `likes`*: `number`
  - `aisle`*: `string`
  - `credits`: `object` {
    - `text`: `string`
    - `link`: `string`
    - `image`: `string`
    - `imageLink`: `string`
  }
  - `nutrition`*: `object` {
    - `nutrients`*: `array<` `object` {
      - `name`*: `string`
      - `amount`*: `number`
      - `unit`*: `string`
      - `percentOfDailyNeeds`*: `number`
    } `>`
    - `caloricBreakdown`*: `object` {
      - `percentProtein`*: `number`
      - `percentFat`*: `number`
      - `percentCarbs`*: `number`
    }
  }
  - `price`*: `number`
  - `servings`*: `object` {
    - `number`*: `number`
    - `size`*: `number`
    - `unit`*: `string`
  }
  - `spoonacularScore`*: `number`
}

### Schema: ComparableProduct

`object` {
  - `difference`*: `number`
  - `id`*: `integer`
  - `image`*: `string`
  - `title`*: `string`
}

### Schema: MenuItem

`object` {
  - `id`*: `integer`
  - `title`*: `string`
  - `restaurantChain`*: `string`
  - `nutrition`: `object` {
    - `nutrients`*: `array<` `object` {
      - `name`*: `string`
      - `amount`*: `number`
      - `unit`*: `string`
      - `percentOfDailyNeeds`*: `number`
    } `>`
    - `caloricBreakdown`*: `object` {
      - `percentProtein`*: `number`
      - `percentFat`*: `number`
      - `percentCarbs`*: `number`
    }
  }
  - `badges`: `array<` `string` `>`
  - `breadcrumbs`: `array<` `string` `>`
  - `generatedText`: `string`
  - `imageType`: `string`
  - `likes`: `integer`
  - `servings`: `object` {
    - `number`*: `number`
    - `size`*: `number`
    - `unit`*: `string`
  }
  - `price`*: `number`
  - `spoonacularScore`*: `number`
}

### Schema: IngredientBasics

`object` {
  - `description`*: `string`
  - `name`*: `string`
  - `safety_level`*: `string`
}

### Schema: IngredientInformation

`object` {
  - `id`*: `integer`
  - `original`*: `string`
  - `originalName`*: `string`
  - `name`*: `string`
  - `amount`*: `number`
  - `unit`*: `string`
  - `unitShort`*: `string`
  - `unitLong`*: `string`
  - `possibleUnits`*: `array<` `string` `>`
  - `estimatedCost`*: `object` {
    - `value`*: `number`
    - `unit`*: `string`
  }
  - `consistency`*: `string`
  - `shoppingListUnits`: `array<` `string` `>`
  - `aisle`*: `string`
  - `image`*: `string`
  - `meta`*: `array<` `string` `>`
  - `nutrition`: `object` {
    - `nutrients`*: `array<` `object` {
      - `name`*: `string`
      - `amount`*: `number`
      - `unit`*: `string`
      - `percentOfDailyNeeds`*: `number`
    } `>`
    - `properties`*: `array<` `object` {
      - `name`*: `string`
      - `amount`*: `number`
      - `unit`*: `string`
    } `>`
    - `caloricBreakdown`*: `object` {
      - `percentProtein`*: `number`
      - `percentFat`*: `number`
      - `percentCarbs`*: `number`
    }
    - `weightPerServing`*: `object` {
      - `amount`*: `number`
      - `unit`*: `string`
    }
  }
  - `categoryPath`: `array<` `string` `>`
}

### Schema: TasteInformation

`object` {
  - `sweetness`*: `number`
  - `saltiness`*: `number`
  - `sourness`*: `number`
  - `bitterness`*: `number`
  - `savoriness`*: `number`
  - `fattiness`*: `number`
  - `spiciness`*: `number`
}

### Schema: RecipeInformation

`object` {
  - `id`*: `integer`
  - `title`*: `string`
  - `image`*: `string`
  - `imageType`: `string`
  - `servings`*: `number`
  - `readyInMinutes`*: `integer`
  - `preparationMinutes`: `integer`
  - `cookingMinutes`: `integer`
  - `license`: `string`
  - `sourceName`*: `string`
  - `sourceUrl`*: `string`
  - `spoonacularSourceUrl`*: `string`
  - `aggregateLikes`*: `integer`
  - `healthScore`*: `number`
  - `spoonacularScore`*: `number`
  - `pricePerServing`*: `number`
  - `analyzedInstructions`*: `array<` `object` `>`
  - `cheap`*: `boolean`
  - `creditsText`*: `string`
  - `cuisines`*: `array<` `string` `>`
  - `dairyFree`*: `boolean`
  - `diets`*: `array<` `string` `>`
  - `gaps`*: `string`
  - `glutenFree`*: `boolean`
  - `instructions`*: `string`
  - `lowFodmap`*: `boolean`
  - `occasions`*: `array<` `string` `>`
  - `sustainable`*: `boolean`
  - `vegan`*: `boolean`
  - `vegetarian`*: `boolean`
  - `veryHealthy`*: `boolean`
  - `veryPopular`*: `boolean`
  - `weightWatcherSmartPoints`*: `number`
  - `dishTypes`*: `array<` `string` `>`
  - `extendedIngredients`*: `array<` `object` {
    - `aisle`*: `string`
    - `amount`*: `number`
    - `consistency`*: `string`
    - `id`*: `integer`
    - `image`*: `string`
    - `measures`: `object` {
      - `metric`*: `object{...}`
      - `us`*: `object{...}`
    }
    - `meta`: `array<` `string` `>`
    - `name`*: `string`
    - `original`*: `string`
    - `originalName`*: `string`
    - `unit`*: `string`
  } `>`
  - `summary`*: `string`
  - `winePairing`: `object` {
    - `pairedWines`: `array<` `string` `>`
    - `pairingText`: `string`
    - `productMatches`: `array<` `object` {
      - `id`*: `integer`
      - `title`*: `string`
      - `description`*: `string`
      - `price`*: `string`
      - `imageUrl`*: `string`
      - `averageRating`*: `number`
      - `ratingCount`*: `integer`
      - `score`*: `number`
      - `link`*: `string`
    } `>`
  }
  - `taste`: [`TasteInformation`](#schema-tasteinformation)
}

## Known enum values

Hand-copied from [spoonacular.com/food-api/docs](https://spoonacular.com/food-api/docs) prose (not present in the OpenAPI spec - see caveats above). Verify against the live docs site before relying on these for validation, since Spoonacular can add values without updating the spec.

**Cuisines** (`cuisine` / `excludeCuisine`): African, American, British, Cajun, Caribbean, Chinese, Eastern European, European, French, German, Greek, Indian, Irish, Italian, Japanese, Jewish, Korean, Latin American, Mediterranean, Mexican, Middle Eastern, Nordic, Southern, Spanish, Thai, Vietnamese.

**Diets** (`diet`): Gluten Free, Ketogenic, Vegetarian, Lacto-Vegetarian, Ovo-Vegetarian, Vegan, Pescetarian, Paleo, Primal, Low FODMAP, Whole30.

**Intolerances** (`intolerances`): Dairy, Egg, Gluten, Grain, Peanut, Seafood, Sesame, Shellfish, Soy, Sulfite, Tree Nut, Wheat.

**Meal types** (`type`): main course, side dish, dessert, appetizer, salad, bread, breakfast, soup, beverage, sauce, marinade, fingerfood, snack, drink.

**Sort** (`sort`): meta-score (default relevance), popularity, healthiness, price, time, random, max-used-ingredients, min-missing-ingredients, plus most nutrient names (e.g. calories, protein, carbs, fat). Pair with `sortDirection` (`asc`/`desc`).
