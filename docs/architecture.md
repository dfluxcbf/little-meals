# Architecture

Nothing is implemented yet (see `milestones.md`) — this document records the
technical decisions made at bootstrap time and is expected to gain detail as each
milestone lands.

## Component breakdown

| Component | Responsibility |
|---|---|
| **Web frontend** | The sole user interface (per `design.md`): recipe library browsing/editing, weekly plan review (like/dislike, servings adjustment), shopping list with checkboxes and cost entry, cook-along view. |
| **Backend API** | HTTP API backing the frontend: recipe CRUD, preferences CRUD, meal-plan lifecycle, shopping-list generation, cost recording. |
| **Recipe extraction service** | Wraps the local Ollama LLM. Given free-text recipe input (user-submitted or fetched from an online search result), returns structured output: estimated cooking time, classification (vegetarian/pescetarian/other), ingredient list, ordered steps. Used both for manual submissions and for suggestion generation. |
| **Suggestion engine** | Builds the configured number of new AI-suggested recipes per meal plan: some by combining stored recipes, some via online search seeded by food preferences + library, each passed through the recipe extraction service. |
| **Scheduler** | Triggers weekly meal-plan generation at the user-configured day/time. |
| **Shopping list generator** | Merges ingredients across a finalized plan's recipes, scaling each recipe's quantities to its servings count, producing one deduplicated checklist. |
| **Data store** | Persists recipes, preferences, meal plans, suggestions (with like/dislike state), and shopping lists. |

## Technical decisions

| Decision | Choice | Rationale |
|---|---|---|
| Local LLM runtime | [Ollama](https://ollama.com), called over its local HTTP API | Required by the feature spec; keeps recipe text and preferences off third-party LLM APIs. Specific model left open until Milestone 1, chosen for structured-output reliability at whatever hardware the project runs on. |
| Backend language/framework | Python, FastAPI | Consistent with the rest of the `little-projects` ecosystem (Python + Bazel + wheel packaging, per the [build policy](../../docs/policies/build_policy.md)); FastAPI's typed request/response models are a natural fit for the structured recipe schema the LLM extraction step produces. |
| Storage | SQLite, accessed via the backend only | Single-user, single-host scope (see `design.md` non-goals) — no need for a client/server database. Kept a plain file so backup is trivial. |
| Frontend | Server-rendered pages progressively enhanced with a small amount of client-side JS, framework TBD at Milestone 1 (candidates: htmx, or a minimal React/Vite SPA) | Deferred until the API shape from Milestone 1 (recipe CRUD) exists; no UI framework decision should predate the API it renders. |
| Online recipe search | Provider TBD at the milestone that implements AI suggestions | Needs to weigh available web-search APIs against cost/rate limits; deferred rather than picked speculatively. |
| Weekly scheduling | In-process scheduler (e.g. APScheduler) triggered by the backend process | Single-user, single-host — no need for an external job queue/broker at this scale. |

## Build

Per the [build policy](../../docs/policies/build_policy.md), this project will be
built and packaged with Bazel (`MODULE.bazel`/`BUILD.bazel` at the root, standard
`//:wheel` / `//:install` / `//:test` targets). Those files are intentionally not
created yet: they only make sense once Milestone 1 introduces real source under
`src/`, `tests/` a Bazel target could point at. They land as part of Milestone 1's
definition of done, not as part of this bootstrap.

## External dependencies

- **Ollama**, running locally, reachable over its HTTP API. A host prerequisite —
  see the build policy's "missing system dependencies" section once the preflight
  check is implemented (Milestone 1).
- An online search mechanism for new-recipe suggestions (provider TBD, see table
  above).

## Project-specific notes (per project-structure policy)

No additional top-level folders beyond the ecosystem standard (`docs/`, `src/`,
`tests/`, `tools/`) exist yet. A `bin/`/`build/`/`output/` folder will be added if
and when the project ships a prebuilt artifact.
