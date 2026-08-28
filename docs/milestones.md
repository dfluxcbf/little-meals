# Milestones

Each milestone is worked on its own `feature/<name>` branch (`lvx feature
start`/`lvx feature finish`, see `version_policy.md`). A milestone's definition of
done requires all of: docs updated, requirements created/updated in the
requirements DB (`REQ-#########`, see `requirements_policy.md`), code implemented,
automated tests written, and those tests passing. Requirement IDs are listed as
"TBD" below because none are created until their milestone actually starts, per
the documentation policy.

All UI work from M9 onward — new screens and restyles alike — follows the
design system in [`ui_design.md`](ui_design.md) (palette, typography, the
cookbook/fridge/pinned-paper metaphors, and the shared mobile tab bar /
desktop rail shell). A milestone whose objective mentions "per
`ui_design.md`" is not done until its screens match that system, in addition
to the usual functional definition of done.

| ID | Objective | Requirements | Status |
|---|---|---|---|
| M0 | Project bootstrap: folder layout, `docs/`, `.lvx/config.json`, `VERSION`. No code. | — (no implementation, not requirement-tracked) | Done |
| M1 | Recipe ingestion pipeline: Ollama-backed extraction service (cook time, classification, nutrition/calorie estimate, ingredients, steps from free-text input), recipe storage with a liked/disliked preference state, backend API for recipe CRUD, minimal recipe-library UI. First introduction of `src/`, `tests/`, and the project's Bazel build files. | REQ-000000001, REQ-000000002, REQ-000000003, REQ-000000004, REQ-000000005, REQ-000000006, REQ-000000007, REQ-000000008, REQ-000000009 | Done |
| M2 | Household configuration (shared by every device, not per person): recipes-per-week count, day/time for weekly recommendations, food preferences, number of AI suggestions per plan, default servings per meal — CRUD API + settings UI. | REQ-000000010, REQ-000000011, REQ-000000012 | Done |
| M9 | Visual design system adoption: build the shared base template/CSS per `ui_design.md` (tokens, Fraunces + Inter, the mobile bottom-tab / desktop left-rail shell) and restyle M1's recipe library, recipe detail (including the fridge-door ingredient toggle), and add-recipe screens, plus M2's settings screen, to match. No new functionality — a visual retrofit of what M1/M2 already shipped. | REQ-000000013 to REQ-000000017 | Done |
| M3 | Weekly meal plan generation from stored recipes: scheduler trigger, selection engine that fills a plan from the existing library (excluding disliked recipes) up to the configured recipe count, plan review UI presented as the open-cookbook layout from `ui_design.md` — meals aren't assigned to days, the household picks and cooks them in any order, and can mark a meal cooked directly (the pot-stamp toggle) without going through cook-along. | REQ-000000018 to REQ-000000021 | Done |
| M4 | AI-suggested recipes and reroll: combination-of-stored-recipes generation, extraction via the Milestone 1 pipeline, like/dislike UI at suggestion-review time (reusing the existing recipe preference mechanism — a suggestion is a normal recipe from the moment it's generated, liked by default) wired so a dislike excludes it from future selection, plus reroll actions — whole-plan reroll, single-meal reroll, and controlled reroll (up to 10 unused liked library recipes for one meal, presented as the single-select picker from `ui_design.md`). Online search-based generation (`SearchProvider` protocol, tried before combination) is implemented against **Spoonacular** — chosen over Tavily, Exa, You.com, SerpAPI, Serper.dev, Edamam, TheMealDB, and self-hosted SearXNG for returning structured recipe data directly (no page-scraping) and filter parameters that map onto `food_preferences`, at a free tier (~150 req/day) far beyond this household's actual usage; see `architecture.md`'s "Online recipe search" row for the full rationale, including why Google/Bing/Brave were dead ends despite the household already having a Google account. | REQ-000000022 to REQ-000000028, REQ-000000038 | Done |
| M5 | Shopping list generation: ingredient merge/dedup across a finalized plan, quantity scaling to each recipe's servings (including per-recipe override away from the default), checkbox UI styled as the pinned paper note from `ui_design.md`, actual-cost entry. | REQ-000000029 to REQ-000000032 | Done |
| M6 | Guided cook-along mode: step-by-step walkthrough UI for a recipe's cooking steps as the large single-step cards from `ui_design.md`, ending with a like/dislike prompt that updates the recipe's preference state based on how it actually turned out and sets the same cooked flag M3's pot-stamp toggle controls. | REQ-000000033 to REQ-000000034 | Done |
| M7 | Weekly scheduling end-to-end: the M3 scheduler actually firing at the user-configured day/time and notifying the user a new plan is ready. Notification is an in-app banner (no email/push channel exists) and the trigger polls every 60s rather than firing one precisely-timed job - see `architecture.md`'s Scheduler entry, including its known UTC-interpretation limitation for `recommendation_time`. | REQ-000000035 to REQ-000000037 | Done |
| M8 | Remote access: Tailscale set up on the home server, tailnet ACLs restricting access to the two household members, `tailscale serve` (not `funnel`) exposing the app over HTTPS via MagicDNS, both phones enrolled in the tailnet. See `architecture.md`'s "Remote access & network security" section. | TBD | Not started |

## Sequencing notes

- M1 must land before M3–M6, since every later milestone operates on recipes the
  M1 pipeline produces.
- M9 (visual design system) should land before M3, so M3–M6 build their screens
  once against `ui_design.md` directly rather than shipping placeholder styling
  and needing a second restyle pass later. It only depends on M1/M2 (the
  screens it restyles), so it can start as soon as they're done.
- M2 (preferences) must land before M3 (meal plan generation) and M4 (AI
  suggestions), since both consume preference configuration.
- M7 depends on M2 (day/time configuration) and M3 (something to generate on
  schedule).
- M5 (shopping list) depends on a finalized plan, which depends on M3 and, if AI
  suggestions are enabled, M4.
- M8 only needs M1 (something running to expose) and can otherwise be done at any
  point in parallel with M2–M7 — it's host/network configuration, not application
  logic, so it doesn't block or get blocked by the feature milestones.
