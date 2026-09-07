# Changelog

All notable changes to this project are documented in this file, grouped by
release version. Versions follow the project's [version policy](docs/version_policy.md)
and are managed exclusively through `lvx`.

## [0.5.5] - 2026-09-07

### Added
- Native ingredient icon library: 58 hand-picked SVG icons for foods and
  cooking techniques, served as CSS masks so they inherit the current accent
  color, with a `manifest.json` index and attribution in
  `static/icons/NOTICE.md`. Steps carry an optional `icon`, picked in the
  recipe editor through an icon-picker `<dialog>`, and shown on the recipe
  row, the recipe detail page and the cook-along.
- Cook-along step carousel: each step page renders the previous, current and
  next step as a stacked card, morphing between steps with the browser's
  cross-document View Transitions (a plain instant swap where unsupported)
  and navigable by swipe (`static/js/cook-step-swipe.js`).
- Per-device accent color: an Appearance section in Settings offers six
  presets (terracotta, sage, teal, plum, rose, gold), stored in
  `localStorage` so each phone in the household picks its own, and applied to
  the native `theme-color` chrome as well as the page. The running app
  version now shows next to the brand in the top bar.
- Pantry / never-buy ingredient catalog (M18): a household-wide
  `IngredientCatalogStore` marks an ingredient *name* as "pantry" (assumed on
  hand) or "never buy" (excluded from the shopping list entirely).
  `/settings/ingredients` shows all three lists at once and moves names
  between them via a hold-to-open action sheet; a glob filter bar
  (`planning/glob_match.py`) narrows long lists. The recipe detail and
  cook-along ingredient screens group a recipe's ingredients into
  Ingredients / Pantry items / Others.
- Glob search in the cookbook's Filters & Sort bar, with a Name / Ingredients
  / Steps / All scope selector (`GlobScope` in `planning/recipe_filters.py`),
  and a reworked filter bar driven by `static/js/recipe-filter-bar.js`.
- Settings > Development gained "Clear shopping list", which deletes the
  current plan's shopping list while keeping the plan itself.
- Server and CI manifests for `little-runner` (M19, M20):
  `.lrun/config.toml` declares how to build, stop and launch this app's
  server, plus the `[server.screenshot]` pages used in change reports;
  `.github/workflows/` gained issue hand-off, server up/down and
  pull-request check workflows.

### Changed
- The shopping list drops the tilted notebook-paper styling for a plain
  checklist card, grouped into To buy / Pantry / Checked / Checked (pantry)
  and sorted alphabetically within each section
  (`group_shopping_list_items`); never-buy ingredients are filtered out
  before quantities are merged.
- "Cancel Plan" moved from the bottom action bar to the top of `/plan`, away
  from the other thumb-reachable buttons.
- `//:relaunch` was simplified and is now deprecated in favour of the
  little-runner server workflows (M19); `//:deploy` remains available.

### Fixed
- Recipe editor ingredient rows had a single free-text amount field whose
  whole value ("2 piece") was stored as `unit`, leaving `quantity` unset - so
  two entries of the same ingredient with different amounts could never merge
  or sum in the shopping list. Quantity and unit are now separate inputs, and
  `RecipeStore` splits the legacy combined form when reading existing recipe
  files.

## [0.3.5] - 2026-09-01

### Added
- Cookbook filter/sort bar (M17): a collapsible `<details>` panel above the
  `/recipes` tab bar with min/max range filters for calories, protein,
  fiber, and cook time; multi-select classification and difficulty tag
  filters; and ascending/descending sort by name, calories, protein, fiber,
  or cook time. Driven entirely by `GET /recipes` query params through a new
  pure `planning/recipe_filters.py` module, so filtered/sorted views are
  bookmarkable and need no JS to apply.
- Swipe-right-to-add-to-plan on cookbook cards (M17): reuses the cook-along
  swipe's touch-delta technique to dispatch a `swiped-right` event that
  triggers `POST /recipes/{id}/add-to-plan`, adding the recipe to the
  current week's plan in place - creates a draft plan if none exists, is a
  no-op if the recipe's already in the plan, and is blocked with an inline
  message if the plan is already finalized.

## [0.3.4] - 2026-08-31

### Added
- `lmeals settings --view` prints the current data/recipes directories and
  every household setting (recipes per week, recommendation/auto-confirm
  day/time, default servings) and its current value.

## [0.3.3] - 2026-08-31

### Removed
- Complete removal of the Ollama/LLM recipe-extraction integration (M16):
  the `llm/` package, the `POST /api/recipes/extract` endpoint,
  `ExtractedRecipe`/`ExtractRequest`, the `ollama_*` Settings/env vars, and
  preflight's "local LLM runtime" dependency tier. Every feature is now
  purely user-driven: recipes are entered directly (M12's edit form) and
  plans are drawn purely from the cookbook on a schedule (M3). An
  unparseable recipe file is simply skipped with a logged warning, same as
  the pre-existing no-extractor fallback.

## [0.3.2] - 2026-08-31

### Added
- Recipe difficulty tag (Easy/Medium/Hard/Undefined) (M15): a new
  `Recipe`/`RecipeCreate`/`RecipeUpdate` field, persisted in the recipe
  store's frontmatter and defaulting to Undefined for both new and
  pre-existing recipes. The add/edit form gets a deselectable Easy/Medium/
  Hard pill-group (clearing it, or leaving it unset, saves Undefined), and a
  difficulty badge now shows in the cookbook list, the recipe detail page,
  and the weekly plan's meal card, alongside the classification badge.
- Vegan, Ketogenic, and Paleo classifications (M15), added to the
  `Classification` enum and wired into the same add/edit pill-group and
  JSON API that already handled Vegetarian/Pescetarian/Other.

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
