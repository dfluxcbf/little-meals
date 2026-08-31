# Changelog

All notable changes to this project are documented in this file, grouped by
release version. Versions follow the project's [version policy](docs/version_policy.md)
and are managed exclusively through `lvx`.

## [0.2.10] - 2026-08-31

### Added
- PWA installability: web app manifest and full icon set (favicon,
  apple-touch, and maskable/standard 192/512 icons).

### Improved
- UI polish across cook-along step pages, the plan view, and recipe list
  partials (styling and markup refinements).

## [0.1.12] - 2026-08-28

### Improved
- Recipe extraction quality: hardened recipe store handling and adjusted the
  plan builder / API routes that consume it, with real-Ollama coverage added
  for the extraction pipeline.

## [0.1.11] - 2026-08-28

### Added
- Spoonacular-backed online recipe search provider for AI-suggested recipes,
  wired into config and the API app, tried before combination-of-stored-recipes
  generation (M4 follow-up). Spoonacular was chosen over Tavily, Exa, You.com,
  SerpAPI, Serper.dev, Edamam, TheMealDB, and self-hosted SearXNG — see
  `docs/architecture.md`'s "Online recipe search" entry for the full rationale.
- API key vault: encrypted local storage for third-party API keys (e.g. the
  Spoonacular key), plus CLI support and preflight checks for configuring it.

## [0.1.10] - 2026-08-28

### Improved
- Recipe extraction quality: expanded and refined the Ollama-backed extraction
  service and its prompts.

## [0.1.9] - 2026-08-28

### Improved
- Requirements backfill: retroactively filled in test coverage for existing
  API, plan, shopping list, cook-along, scheduler, and notification behavior,
  and reconciled `docs/requirements_policy.md` / `docs/milestones.md` with what
  had actually been built.

## [0.1.8] - 2026-08-28

### Added
- M7: end-to-end weekly scheduling — the M3 scheduler now fires at the
  household's configured day/time and surfaces an in-app banner notification
  when a new plan is ready (poll-based trigger, no email/push channel).

## [0.1.7] - 2026-08-28

### Added
- M6: guided cook-along mode — step-by-step walkthrough UI for a recipe's
  steps, ending in a like/dislike prompt that updates the recipe's preference
  state and marks it cooked.

## [0.1.6] - 2026-08-28

### Added
- M5: shopping list generation — ingredient merge/dedup across a finalized
  plan, quantity scaling to each recipe's servings (with per-recipe override),
  checkbox UI, and actual-cost entry.

## [0.1.5] - 2026-08-28

### Added
- M4: AI-suggested recipes and reroll — combination-of-stored-recipes
  generation, extraction via the M1 pipeline, like/dislike at suggestion-review
  time, and reroll actions (whole-plan, single-meal, and controlled reroll
  from up to 10 unused liked recipes).

## [0.1.4] - 2026-08-28

### Added
- M3: weekly meal plan generation — scheduler trigger, selection engine that
  fills a plan from the recipe library up to the configured count (excluding
  disliked recipes), and a plan review UI with direct cooked-marking.

## [0.1.3] - 2026-08-28

### Added
- M9: shared visual design system (tokens, Fraunces + Inter, mobile bottom-tab
  / desktop left-rail shell) and restyle of the M1 recipe library, recipe
  detail, add-recipe, and M2 settings screens to match.

## [0.1.2] - 2026-08-27

### Added
- M2: household configuration (recipes-per-week count, day/time for weekly
  recommendations, food preferences, AI suggestion count, default servings)
  with CRUD API and settings UI.

## [0.1.1] - 2026-08-27

### Added
- M1: recipe ingestion pipeline — Ollama-backed extraction (cook time,
  classification, nutrition/calorie estimate, ingredients, steps from
  free-text input), recipe storage with liked/disliked preference state,
  backend CRUD API, and a minimal recipe-library UI. First introduction of
  `src/`, `tests/`, and the project's Bazel build files.
