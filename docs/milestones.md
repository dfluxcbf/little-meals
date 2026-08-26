# Milestones

Each milestone is worked on its own `feature/<name>` branch (`lvx feature
start`/`lvx feature finish`, see `version_policy.md`). A milestone's definition of
done requires all of: docs updated, requirements created/updated in the
requirements DB (`MEALS-...`, see `requirements_policy.md`), code implemented,
automated tests written, and those tests passing. Requirement IDs are listed as
"TBD" below because none are created until their milestone actually starts, per
the documentation policy.

| ID | Objective | Requirements | Status |
|---|---|---|---|
| M0 | Project bootstrap: folder layout, `docs/`, `.lvx/config.json`, `VERSION`. No code. | — (no implementation, not requirement-tracked) | Done |
| M1 | Recipe ingestion pipeline: Ollama-backed extraction service (cook time, classification, ingredients, steps from free-text input), recipe storage, backend API for recipe CRUD, minimal recipe-library UI. First introduction of `src/`, `tests/`, and the project's Bazel build files. | TBD | Not started |
| M2 | User configuration: recipes-per-week count, day/time for weekly recommendations, food preferences, number of AI suggestions per plan, default servings per meal — CRUD API + settings UI. | TBD | Not started |
| M3 | Weekly meal plan generation from stored recipes: scheduler trigger, selection engine that fills a plan from the existing library up to the configured recipe count, plan review UI. | TBD | Not started |
| M4 | AI-suggested recipes: combination-of-stored-recipes generation, online search-based generation (search provider decision made here), extraction via the Milestone 1 pipeline, like/dislike UI wired to promote liked suggestions into the recipe library. | TBD | Not started |
| M5 | Shopping list generation: ingredient merge/dedup across a finalized plan, quantity scaling to each recipe's servings (including per-recipe override away from the default), checkbox UI, actual-cost entry. | TBD | Not started |
| M6 | Guided cook-along mode: step-by-step walkthrough UI for a recipe's cooking steps. | TBD | Not started |
| M7 | Weekly scheduling end-to-end: the M3 scheduler actually firing at the user-configured day/time and notifying the user a new plan is ready. | TBD | Not started |
| M8 | Remote access: Tailscale set up on the home server, tailnet ACLs restricting access to the two household members, `tailscale serve` (not `funnel`) exposing the app over HTTPS via MagicDNS, both phones enrolled in the tailnet. See `architecture.md`'s "Remote access & network security" section. | TBD | Not started |

## Sequencing notes

- M1 must land before M3–M6, since every later milestone operates on recipes the
  M1 pipeline produces.
- M2 (preferences) must land before M3 (meal plan generation) and M4 (AI
  suggestions), since both consume preference configuration.
- M7 depends on M2 (day/time configuration) and M3 (something to generate on
  schedule).
- M5 (shopping list) depends on a finalized plan, which depends on M3 and, if AI
  suggestions are enabled, M4.
- M8 only needs M1 (something running to expose) and can otherwise be done at any
  point in parallel with M2–M7 — it's host/network configuration, not application
  logic, so it doesn't block or get blocked by the feature milestones.
