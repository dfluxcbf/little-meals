# Architecture

Nothing is implemented yet (see `milestones.md`) — this document records the
technical decisions made at bootstrap time and is expected to gain detail as each
milestone lands.

## Component breakdown

| Component | Responsibility |
|---|---|
| **Web frontend** | The sole user interface (per `design.md`): recipe library browsing/editing, weekly plan review (like/dislike, servings adjustment), shopping list with checkboxes and cost entry, cook-along view. |
| **Backend API** | HTTP API backing the frontend: recipe CRUD, preferences CRUD, meal-plan lifecycle, shopping-list generation, cost recording. |
| **Recipe extraction service** | Wraps the local Ollama LLM. Given free-text recipe input (user-submitted or fetched from an online search result), returns structured output: estimated cooking time, classification (vegetarian/pescetarian/other), nutrition/calorie estimate, ingredient list, ordered steps. Used both for manual submissions and for suggestion generation. |
| **Selection engine** (`planning/selection.py`, Milestone 3) | Fills a plan from the existing recipe library only: excludes disliked recipes, randomly samples up to the configured `recipes_per_week` count for variety week to week. A pure function over an in-memory recipe list - no I/O, no LLM call. |
| **Suggestion engine** (`planning/suggestion.py` + `planning/plan_builder.py`, Milestone 4) | Extends the selection engine with AI-suggested recipes: `build_weekly_plan` reserves `ai_suggestions_per_plan` slots (never drawn from the library) and fills them via `generate_search_suggestion` (a pluggable `SearchProvider` - see "Online recipe search" below) tried first, falling back to `generate_combination_suggestion` (blends two randomly-picked liked recipes' ingredients/steps into one free-text brief, extracted through the same pipeline as a manual submission). A suggestion that's accepted is written into the recipe library immediately, liked by default - see design.md's updated Recipe concept. Reroll: whole-plan (`replace_meals` - runs the same generation again), single-meal (`generate_single_replacement` - prefers an unused liked library recipe, only generates a new one if the library has nothing left), and controlled reroll (`list_controlled_reroll_candidates` - up to 10 unused liked library recipes to pick from directly; deliberately **not** 10 fresh LLM generations, to avoid the latency/cost of extracting and mostly discarding nine of them per request). All three are blocked once a plan is finalized. A suggestion source that can't produce anything (too few liked recipes, an unconfigured search provider, an LLM hiccup) just contributes nothing to that slot rather than failing the whole request. |
| **Scheduler** (`scheduler.py`, Milestone 7) | `WeeklyScheduler.check_and_maybe_generate` polls every 60s (an APScheduler `BackgroundScheduler` interval job, started in `create_app`'s lifespan handler when `enable_scheduler=True` - the real server passes this via `cli.py`; test/library callers default it off so tests don't spin up background threads) rather than firing one precisely-timed job per week: it computes the most recent `recommendation_day`/`recommendation_time` occurrence (`last_scheduled_occurrence`) and regenerates only if the current plan predates it. Polling means a mid-week change to the household's day/time takes effect on the very next check, with no job to reschedule. **Known limitation**: `recommendation_time` has no timezone field, so it's interpreted as UTC here - a household not on UTC needs to account for the offset when picking a time, until a timezone field is added to household preferences. Auto-generation sets a `NotificationStore` flag (`mark_new_plan_ready`) surfaced as an in-app banner (see "Notifications" below) - there's no email/push channel, so "notifying the user" means that banner, not anything delivered outside the browser tab. |
| **Shopping list generator** (`planning/shopping_list.py`, Milestone 5) | `build_shopping_list_items` merges ingredients across a finalized plan's recipes into one flat, deduplicated list (no grocery-aisle grouping - see design.md), scaling each recipe's quantities from the recipe's own `servings` to that meal's actual servings count in the plan. Two ingredients merge into one line only when name AND unit match (case-insensitively); different units for the same name (e.g. "cups" vs "g" of flour) stay separate lines rather than being silently summed, since that would need unit conversion this doesn't attempt. Generation is on-demand (`POST /shopping/generate`, blocked until the plan is finalized) and idempotent - regenerating an already-generated list just returns the existing one rather than duplicating it. |
| **Cook-along view** (`cook_step.html`/`cook_finish.html`, Milestone 6) | Server-rendered, no client-side step state (per `ui_design.md`'s implementation notes): each step is its own page at `GET /recipes/{id}/cook/{step_number}`, Prev/Next are plain links to `step_number ± 1`, and stepping past the last step renders the post-cook like/dislike prompt directly - no session or database state tracks "where you are" in a session. `POST /recipes/{id}/cook/finish` sets the recipe's preference (reusing the same store method the library/plan-review like/dislike controls use) and, if that recipe is in the current plan, marks that meal cooked via the same `MealPlanStore.set_cooked` the pot-stamp toggle calls. Reachable for any recipe, not just ones in this week's plan - the plan-meal-cooked side effect is skipped (not an error) when there's no matching plan meal. Deliberately outside the shared app-shell layout (no top bar/tab bar) for an uncluttered, phone-in-the-kitchen reading experience. |
| **Notifications** (`NotificationStore`, Milestone 7) | A single household-wide flag ("a new plan is ready"), not a queue or a per-user inbox - matches the non-goal of per-person state. Set when the scheduler auto-generates a plan; shown as an in-app banner (top of `recipes.html`/other pages, not `plan.html` itself since that page IS what it points to) linking to `/plan`; cleared the moment `/plan` is viewed. No email/push/SMS - see the Scheduler entry above. |
| **Recipe store** | The recipe library as a directory of Markdown files, one file per recipe (YAML frontmatter for structured fields — cook time, classification, nutrition, ingredients, liked/disliked state — plus a Markdown body for the ordered steps). Directly readable and editable by the user with any text editor; the backend treats this directory as the source of truth rather than caching it in a database. |
| **Data store** | Persists everything that isn't a recipe: household preferences, meal plans, suggestions, and shopping lists (which reference recipes by filename/id in the recipe store). Shared by every device in the household — see "Remote access" below — not partitioned per user. |

## Technical decisions

| Decision | Choice | Rationale |
|---|---|---|
| Local LLM runtime | [Ollama](https://ollama.com), called over its local HTTP API | Required by the feature spec; keeps recipe text and preferences off third-party LLM APIs. Default model `qwen2.5-coder:14b` (overridable via `LITTLE_MEALS_OLLAMA_MODEL`) — chosen for structured/JSON-output reliability; not `llama3.1` since it isn't what's actually pulled on the reference dev machine. Called via `POST /api/generate` with `stream=false` and `format` set to the extraction JSON schema, falling back to plain `format="json"` mode if the server rejects the schema (older Ollama versions). |
| Backend language/framework | Python, FastAPI | Consistent with the rest of the `little-projects` ecosystem (Python + Bazel + wheel packaging, per the [build policy](../../docs/policies/build_policy.md)); FastAPI's typed request/response models are a natural fit for the structured recipe schema the LLM extraction step produces. |
| Recipe storage | Markdown files (YAML frontmatter + Markdown body), one per recipe, under a `recipes/` directory | Recipes are the artifact the user most wants to own, read, and edit directly — plain text keeps them portable, diffable, and version-controllable independent of the app, and lets the user hand-edit a recipe without going through the UI. Not a database, so no query/migration layer to keep in sync with a format the user can also touch by hand. |
| Other storage | SQLite, accessed via the backend only | Preferences, meal plans, suggestions, and shopping lists are app-managed, not meant for direct user editing, and are naturally relational (plan → recipe references, generation timestamps). One shared household dataset, single host (see `design.md` non-goals — no per-user partitioning) — no need for a client/server database. Kept a plain file so backup is trivial. |
| Frontend | Server-rendered Jinja2 templates progressively enhanced with vendored htmx (`src/little_meals/static/vendor/htmx.min.js`, committed — not CDN-linked) | Decided at Milestone 1, not a React/Vite SPA: htmx is one committed JS file, so the frontend adds no node/npm system dependency (which would otherwise become a new tier in the preflight check below); rendering stays server-side, so a phone on the tailnet gets a working page with no build step; and it reuses the exact same FastAPI route layer as the JSON API rather than a separate client build. |
| Visual design | `docs/ui_design.md`'s design system, applied at Milestone 9 | Cream/terracotta/sage palette, Fraunces + Inter typography, and the cookbook/fridge-door/pinned-paper metaphors, implemented as plain CSS (`static/app.css`, `static/fonts.css`) plus native HTML disclosure (`<details>`/`<summary>` for the ingredients fridge-door toggle, `<input type="radio">` + `<label>` for the settings day-picker pills) — no client-side JS framework, consistent with the Frontend decision above. Fonts are vendored (`static/vendor/fonts/*.woff2`, SIL OFL-licensed) rather than linked from Google Fonts, for the same no-third-party-CDN reasoning as htmx. |
| Online recipe search | `planning/suggestion.SearchProvider` protocol (`search(query) -> list[str]`), defaulting to `NullSearchProvider` (always returns no results) until a real provider is chosen | Milestone 4 built the dependency-injection seam (`create_app(search_provider=...)`) so the suggestion engine has somewhere to plug a real provider in without a code change to the engine itself, but the actual provider choice is still deferred - needs to weigh available web-search APIs against cost/rate limits, and picking one wasn't something the implementing session could authorize (needs an API key/credentials and a cost decision from the project owner). Until then, suggestions come entirely from combining stored recipes. |
| Weekly scheduling | In-process `apscheduler` `BackgroundScheduler` (a thread, not asyncio - matches the rest of the backend's synchronous style), a 60s interval job wrapping `WeeklyScheduler.check_and_maybe_generate` - see the Scheduler component entry above | Single-user, single-host — no need for an external job queue/broker at this scale. Interval polling over a precise cron-style trigger specifically so a household preferences change doesn't require rescheduling anything. |
| Remote access | [Tailscale](https://tailscale.com) private mesh network (WireGuard-based) | See "Remote access & network security" below. |

## Remote access & network security

The backend runs on one machine at home; it must be reachable from the household's
phones away from home, without exposing it to the public internet or routing its
data through a third party that could read it.

**Chosen approach: Tailscale, tailnet-only (`tailscale serve`, never `tailscale
funnel`).**

- Tailscale creates a private mesh network (a *tailnet*) of the household's
  devices, connected over direct, end-to-end encrypted WireGuard tunnels. There is
  no open inbound port on the home router and no public URL — a device that isn't
  a member of the tailnet cannot reach the app at all, at the network level. This
  is what satisfies the requirement to *stop*, not just gate, internet-originated
  access.
- Tailscale's coordination servers only help member devices discover each other
  (NAT traversal); they do not proxy or read application traffic in normal
  operation (occasional relay via Tailscale's DERP servers when a direct path
  can't be established is itself end-to-end encrypted, so DERP cannot read it
  either).
- **Free plan ("Personal") is sufficient**: up to 6 users per tailnet with
  unlimited devices per user, which covers the two household members plus all
  their devices, at no cost.
- **Authentication is handled by Tailscale, not a password shared over the wire**:
  each person joins the tailnet by signing in once through an identity provider
  (Google, Microsoft, GitHub, Apple, or passkey) — no separate Tailscale account
  password to manage, and no root/admin device access required, just the OS's
  standard "allow VPN configuration" permission when installing the app.
- **`tailscale serve`, not `tailscale funnel`**, exposes the app: `serve` makes a
  local port reachable only to other tailnet members over HTTPS; `funnel` would
  make it reachable to the public internet and must not be used here. The two are
  mutually exclusive per port, which makes the private-only choice explicit and
  easy to audit (`tailscale serve status` shows exactly what's exposed and to
  whom).
- **MagicDNS + `tailscale cert`** give the app a stable hostname
  (`little-meals.<tailnet-name>.ts.net`) with a real, browser-trusted HTTPS
  certificate (via Let's Encrypt), auto-renewed by `tailscaled` — so the phone
  browser gets a plain `https://` URL and a padlock, not a raw IP and a
  certificate warning. (Enabling this publishes the device's hostname, but not
  its contents, to the public Certificate Transparency log — a Tailscale-documented
  tradeoff, not a data leak.)
- **Tailnet ACLs** (`autogroup:member` restricted to a tag on the home server, or
  an explicit grant between the two users) further restrict which tailnet members
  can reach the app's port, so joining the tailnet for an unrelated reason
  wouldn't implicitly grant `little-meals` access.
- App-level login (a username/password inside `little-meals` itself) is not
  required for this to be secure, since tailnet membership is already the access
  gate for a two-person household, and is left as optional/deferred rather than a
  hard requirement.

Setup is host-machine configuration (installing/configuring `tailscaled` and
`tailscale serve`), not application code — it doesn't produce `src/` changes, but
is tracked as its own milestone (see `milestones.md`) since it has real setup
steps, a definition of done, and should be documented as it's done.

## Recipe storage format

Each recipe is one Markdown file under a `recipes/` directory (path configurable),
named for the recipe (e.g. `recipes/lemon-garlic-chicken.md`):

- **YAML frontmatter** holds the structured fields the app needs to query, filter,
  and combine recipes: title, estimated cook time, classification, nutrition
  estimate, the ingredient list with quantities, and the liked/disliked preference
  state.
- **Markdown body** holds the ordered cooking steps as free text (e.g. a numbered
  list), which cook-along mode walks through.

The backend parses this directory as the source of truth — it does not maintain a
separate cached copy. When the app changes a recipe (LLM extraction on submission,
a like/dislike from suggestion review or post-cook feedback, a servings edit), it
writes the change back to the file, not to a database row. The user is free to
hand-edit any recipe file directly (e.g. to fix a step or tweak an ingredient); the
app picks up the change the next time it reads that file.

## Household preferences storage

Household preferences (recipes-per-week count, recommendation day/time, food
preferences, AI suggestions per plan, default servings — see `design.md`'s
"Household preferences" concept) are a single row in SQLite (`household.db` under
the data directory), per the "Other storage" decision above — app-managed
configuration, not something the user is expected to hand-edit, and there is
exactly one of it per installation, not a collection. `HouseholdPreferencesStore`
(`store/household_store.py`) upserts that one row; reading before any write
returns built-in defaults rather than a not-found error, since "unconfigured" is a
normal, expected state, not an error condition. Exposed as a JSON API
(`GET`/`PUT`/`DELETE` on `/api/household-preferences` — `DELETE` resets to
defaults rather than leaving the household unconfigured) and a server-rendered
`/settings` form, both in `api/`.

## Build

Per the [build policy](../../docs/policies/build_policy.md), this project is built
and packaged with Bazel: hermetic `rules_python` 1.7.0 + a Python 3.12 toolchain,
dependencies resolved via `pip.parse` off a fully-hashed `requirements_lock.txt`
(regenerate with `bazel run //:requirements.update`). Canonical targets:

| Command | Purpose |
|---|---|
| `bazel build //:all` | Build every artifact (currently just the wheel). |
| `bazel build //:wheel` | Build the Python wheel. |
| `bazel run //:preflight` | Run the system-dependency check on its own. |
| `bazel run //:install` | Preflight-gated `pipx install` of the wheel. |
| `bazel run //:serve` | Run the web app (`uvicorn`). |
| `bazel test //...` | Run the unit test suite (hermetic, no network). |

The non-Bazel path (`pyproject.toml`, `pip install .`) exists for local/editable
development; Bazel is still the canonical build per the build policy.

## External dependencies

- **Ollama**, reachable over its HTTP API (`LITTLE_MEALS_OLLAMA_URL`, default
  `http://127.0.0.1:11434`) — not necessarily on the same host as the backend
  process, just reachable over the network (see "Local LLM runtime" above and the
  preflight check below). A host prerequisite: not pip-installable, so it can't be
  isolated by Bazel.
- An online search mechanism for new-recipe suggestions (provider TBD, see table
  above) — not needed until Milestone 4.

### Preflight dependency check

`src/little_meals/preflight.py` implements the build policy's "missing system
dependencies" requirements: tiered checks (core tools, then the local LLM
runtime), every missing dependency **within** a tier reported together with a
copy-pasteable install command, and evaluation stopping at the first tier with
anything missing (so it never claims Ollama's daemon is unreachable before
confirming the `ollama` binary itself is even installed). A soft, non-failing
check additionally probes whether Ollama's daemon actually answers, since that's
runtime state, not an install-time dependency. Exposed as `bazel run //:preflight`
and `lmeals preflight`, and run automatically as the first step of `bazel run
//:install`.

## Module boundaries

| Module | Responsibility |
|---|---|
| `config.py` | Runtime `Settings` (data dir, Ollama URL/model/timeout), all env-overridable. |
| `models.py` | Pydantic `Recipe`/`Ingredient`/`Nutrition`, the LLM-facing `ExtractedRecipe` subset, `HouseholdPreferences`, `MealPlan`/`PlanMeal`, and `ShoppingList`/`ShoppingListItem`. |
| `store/` | The Markdown+YAML-frontmatter recipe store (see "Recipe storage format" above), the SQLite-backed `HouseholdPreferencesStore` (see "Household preferences storage" above), the SQLite-backed `MealPlanStore` (plans + their meals), the SQLite-backed `ShoppingListStore` (one list per plan, keyed by `plan_id`), and the SQLite-backed `NotificationStore` (the single "new plan ready" flag) - all four app-managed for the same reason as household preferences. |
| `llm/` | The Ollama HTTP client, the extraction prompt, and the extraction service. |
| `planning/` | `selection.py` (Milestone 3) - the library-only selection engine, a pure function over recipes, no I/O. `suggestion.py` (Milestone 4) - `SearchProvider`/`NullSearchProvider` and the combination/search suggestion generators, each doing real I/O (LLM calls). `plan_builder.py` (Milestone 4) - orchestrates both into `build_weekly_plan`, `generate_single_replacement`, `list_controlled_reroll_candidates`, and `build_meal_specs` (the shared "generate a fresh plan's meals" call every generation path - initial, whole-plan reroll, and the Milestone 7 scheduler - uses). `shopping_list.py` (Milestone 5) - `build_shopping_list_items`, the ingredient merge/scale logic. |
| `scheduler.py` | `WeeklyScheduler` and `last_scheduled_occurrence` (Milestone 7) - see the Scheduler component entry above. |
| `api/` | The FastAPI app factory (including the scheduler's lifespan wiring), the JSON recipe-CRUD/household-preferences/meal-plan/shopping-list routes, and the server-rendered HTML routes (recipe library, settings, weekly plan, shopping list, cook-along - all in `routes_ui.py`). |
| `preflight.py` | The system-dependency check described above. |
| `cli.py` | `lmeals serve` / `lmeals preflight` / `lmeals --version`. |

## Project-specific notes (per project-structure policy)

No additional top-level folders beyond the ecosystem standard (`docs/`, `src/`,
`tests/`, `tools/`) exist. A `bin/`/`build/`/`output/` folder will be added if and
when the project ships a prebuilt artifact.

The runtime recipe/data directory (`$LITTLE_MEALS_DATA_DIR`, default
`~/.local/share/little-meals`) lives **outside** this repo — nothing under `src/`
is ever written to at runtime, keeping the Bazel source tree clean.

Per the [project structure policy](../../docs/policies/project_structure_policy.md#inter-project-independence-and-dependencies):
`little-meals` depends on `little-requirements` only as an installed dev-time tool
(the `lreq` CLI and its pytest plugin, consumed from its pipx-installed wheel),
never as a source or build dependency — it's deliberately absent from
`requirements.in`/`requirements_lock.txt` because it isn't published on PyPI, and
pointing `pip.parse` at a local wheel path would hardcode a cross-repo path the
build policy's portability rule forbids.
