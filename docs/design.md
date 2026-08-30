# Design

This document covers product purpose and concepts. For the visual design
system (palette, typography, per-screen layout) see
[`ui_design.md`](ui_design.md); for the implementation roadmap see
[`milestones.md`](milestones.md).

## Purpose

`little-meals` is a meal-planning facilitator and recipe book. It removes the
weekly friction of deciding what to cook, collecting the right ingredients, and
following a recipe while cooking. The user builds up a personal library of recipes
they've liked, and the software turns that library into a weekly meal plan, a
single consolidated shopping list, and a guided cook-along mode.

Automatic online recipe collection/suggestion (Milestone 4, backed by
Spoonacular) was tried and removed - see `milestones.md`'s M10 entry. Meal
planning now draws exclusively from recipes already in the household's
cookbook; there is no automatic suggestion of recipes the household hasn't
already saved.

## Goals

- Let the user save recipes they like, with the tedious parts (cook time,
  classification, nutrition/calorie estimate, ingredient list, steps) extracted
  automatically by a local LLM rather than typed by hand.
- Produce a weekly meal plan sized to the user's configured recipe count, drawn
  from the recipes already in the library.
- Let the household like/dislike recipes — either during plan review, or later,
  after actually cooking and trying them — growing (and pruning) the recipe
  library from real feedback.
- Let the user ask for different recipes when the current ones don't land: reroll
  the whole draft plan, reroll a single meal for one new alternative, or run a
  controlled reroll that returns 10 alternatives for a single meal to pick from -
  all drawn from the existing library.
- Turn a week's chosen recipes into one shopping list, correctly scaled for
  however many people are eating each meal, with checkboxes for shopping and a
  place to record what the trip actually cost.
- Walk the user through cooking a recipe step by step.
- Be usable entirely through a web application; no other client is planned.
- Serve one household shared by multiple people and devices (see
  [remote access](architecture.md#remote-access--network-security)), all reading
  and writing the same recipe library, preferences, and meal plan.

## Non-goals

- Per-person accounts or separate preferences within the household — there is one
  shared recipe library, one set of preferences, and one meal plan, even though
  several people/devices in the household use it.
- Pantry/inventory tracking (the shopping list assumes nothing is already on hand).
- Photo/OCR recipe import (recipes are provided as text).
- A native mobile app.
- Budget planning beyond recording the actual cost of a generated shopping list.

## Core concepts

| Concept | Description |
|---|---|
| **Recipe** | A saved dish: id/slug, name, estimated cooking time (`cook_time_minutes`), classification (vegetarian, pescetarian, other), estimated nutrition (`nutrition.calories_per_serving`, at minimum), servings, ingredient list (name, quantity, unit), and an ordered list of cooking steps. Every recipe in the library got there by direct user submission, and carries a preference state — liked by default, or disliked once the household decides, at plan-review time or after actually cooking it, that they don't want it planned again. Stored as a plain Markdown file the user can open and edit directly, not locked inside a database (see [recipe storage format](architecture.md#recipe-storage-format)). |
| **Household preferences** | Configuration shared by the whole household (not per person): recipes-per-week count, day/time of week to receive a new plan, and default servings per meal (e.g. "2 adults", "2 adults + 1 child"). |
| **Reroll** | A request for different recipes than the ones currently on the table, at three granularities: reroll the *whole draft plan* (every slot gets a fresh plan, drawn the same way the original was), reroll a *single meal* (swaps in an unused liked library recipe for that slot), or a *controlled reroll* of a single meal (up to 10 unused liked library recipes to pick from directly). All three draw only from the existing library — a slot simply can't be filled if the library has nothing unused left to offer. Rerolling is only available on a plan that isn't finalized yet. |
| **Meal plan** | The set of recipes selected for a given week from the existing library, each with a servings count the user can override from the default. Meals aren't assigned to specific days — the household picks from the week's set and cooks them in whatever order suits them. Each meal carries a cooked/not-cooked state: the household can mark a meal cooked directly from the plan (a stamp), or it's set automatically when a cook-along session for that meal finishes. |
| **Shopping list** | The ingredient list for an entire meal plan: same ingredients across recipes are merged, quantities scaled to each recipe's servings, presented with checkboxes, in one flat list (no grocery-aisle categorization). The user records the actual amount spent once shopping is done. |
| **Cook-along session** | A guided, step-by-step walkthrough of a single recipe's cooking steps, used while actually cooking - reachable for any recipe, whether or not it's in this week's plan; ends with the option to like/dislike the recipe based on how it actually turned out, which also marks the meal cooked in the current plan if that recipe happens to be in it (the same flag the plan review pot-stamp toggle controls). |

## Data flow

```mermaid
flowchart TD
    U[User submits a recipe: free text] --> L[Local LLM: Ollama]
    L --> R[(Recipe library:\nliked / disliked)]

    S[Weekly scheduler\nconfigured day/time] --> E[Selection engine]
    R --> E
    P[(Household preferences)] --> E
    E --> M[Weekly meal plan draft]

    M --> UF[User reviews:\nlike / dislike each meal,\nadjust servings per recipe]
    UF -->|dislike| R
    UF -->|reroll whole plan| E
    UF -->|reroll one meal, or\npick from 10 alternatives| E
    UF -->|finalized plan| SL[Shopping list generator]
    SL --> SLI[(Shopping list:\nmerged + scaled ingredients,\ncheckboxes, actual cost)]

    R --> CK[Cook-along mode:\nstep-by-step guide]
    CK -->|post-cook like / dislike| R
```

1. The user submits a new recipe as free text. The local LLM (via Ollama) extracts
   estimated cooking time, classification, nutrition/calorie estimate, structured
   ingredients, and cooking steps, and the result is saved to the recipe library.
2. At the user-configured day/time each week, the selection engine builds a draft
   meal plan by drawing from the stored recipe library — excluding disliked
   recipes — up to the configured recipes-per-week count. A library with fewer
   liked recipes than that yields a shorter plan rather than inventing anything.
3. The user reviews the draft: liking or disliking each meal and adjusting
   servings per recipe away from the configured default if needed. If nothing on
   offer fits, the user can reroll the whole plan (step 2 reruns for every
   non-finalized slot), reroll a single meal (swaps in a different unused liked
   library recipe), or run a controlled reroll of a single meal to get 10
   alternatives to choose from instead of one.
4. Once finalized, the shopping list generator merges ingredients across every
   recipe in the plan, scaling each recipe's ingredient quantities to its servings
   count, and produces one checklist. The user checks items off while shopping and
   records what the trip cost.
5. When the user is ready to cook a recipe from the plan (or any recipe in the
   library) — in whatever order they like, since meals aren't scheduled to
   specific days — cook-along mode presents its steps one at a time, and
   afterwards lets the user like or dislike the recipe based on how it
   actually turned out — updating its preference state in the library the
   same way a plan-review dislike would, and marking the meal cooked in
   the plan. The household can also mark a meal cooked directly from the plan
   review screen without going through cook-along.
