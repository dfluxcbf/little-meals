# Architecture

Nothing is implemented yet (see `milestones.md`) — this document records the
technical decisions made at bootstrap time and is expected to gain detail as each
milestone lands.

## Component breakdown

| Component | Responsibility |
|---|---|
| **Web frontend** | The sole user interface (per `design.md`): recipe library browsing/editing, weekly plan review (servings adjustment), shopping list with checkboxes and cost entry, cook-along view. |
| **Backend API** | HTTP API backing the frontend: recipe CRUD, preferences CRUD, meal-plan lifecycle, shopping-list generation, cost recording. |
| **Recipe extraction service** | Wraps the local Ollama LLM. Given free-text recipe input, returns structured output: estimated cooking time, classification (vegetarian/pescetarian/other), nutrition/calorie estimate, ingredient list, ordered steps. Used for the JSON API's `POST /api/recipes/extract` and to normalize an unparseable recipe file on read (see "Recipe store" below); the "New recipe" UI flow itself stopped using it in Milestone 12, in favor of directly editing the fields - see `milestones.md`'s M12 entry. |
| **Selection engine** (`planning/selection.py`, Milestone 3) | Fills a plan from the existing recipe library, randomly sampling up to the configured `recipes_per_week` count for variety week to week. A pure function over an in-memory recipe list - no I/O, no LLM call. `planning/plan_builder.py`'s `build_weekly_plan`/`build_meal_specs` wrap this as the single "generate a fresh plan's meals" call every generation path (initial `POST /plan/generate`, whole-plan reroll, and the scheduler) uses. Reroll: whole-plan (`replace_meals` - runs the selection engine again), single-meal (`generate_single_replacement` - swaps in an unused library recipe, or contributes nothing if none is left), and controlled reroll (`list_controlled_reroll_candidates` - up to 10 unused library recipes to pick from directly). All reroll/choose actions are blocked once a plan is finalized. A milestone that generated new recipes automatically (Milestone 4, an online-search provider plus a combination-of-stored-recipes generator) was implemented and then removed entirely - see `milestones.md`'s M10 entry - so a library smaller than `recipes_per_week` now simply yields a shorter plan rather than the software inventing anything to fill it. The engine originally only drew from recipes marked "liked"; that preference concept was removed in Milestone 13 (see its entry), so every library recipe is now eligible. |
| **Scheduler** (`scheduler.py`, Milestone 7, extended Milestone 14) | One APScheduler `BackgroundScheduler` interval job (started in `create_app`'s lifespan handler when `enable_scheduler=True` - the real server passes this via `cli.py`; test/library callers default it off so tests don't spin up background threads) polls every 60s and runs two independent `WeeklyScheduler` checks in sequence, each keyed off its own household-preferences enable toggle: `check_and_maybe_generate` (guarded by `recommendation_enabled`, default on) computes the most recent `recommendation_day`/`recommendation_time` occurrence (`last_scheduled_occurrence`) and, if the current plan predates it, force-finalizes that plan first (if it wasn't already confirmed) before generating a fresh draft - so a forgotten manual confirm doesn't leave an orphaned draft behind once superseded; `check_and_maybe_confirm` (guarded by `auto_confirm_enabled`, default off, M14) is the same "has the scheduled slot passed since this plan was created" check against its own independent `auto_confirm_day`/`auto_confirm_time`, but only finalizes the current plan if it's still a draft - it never generates anything. Polling means a mid-week change to either schedule takes effect on the very next check, with no job to reschedule. **Known limitation**: neither `recommendation_time` nor `auto_confirm_time` has a timezone field, so both are interpreted as UTC here - a household not on UTC needs to account for the offset when picking a time, until a timezone field is added to household preferences. Auto-generation (not auto-confirm) sets a `NotificationStore` flag (`mark_new_plan_ready`) surfaced as an in-app banner (see "Notifications" below) - there's no email/push channel, so "notifying the user" means that banner, not anything delivered outside the browser tab. |
| **Shopping list generator** (`planning/shopping_list.py`, Milestone 5) | `build_shopping_list_items` merges ingredients across a finalized plan's recipes into one flat, deduplicated list (no grocery-aisle grouping - see design.md), scaling each recipe's quantities from the recipe's own `servings` to that meal's actual servings count in the plan. Two ingredients merge into one line only when name AND unit match (case-insensitively); different units for the same name (e.g. "cups" vs "g" of flour) stay separate lines rather than being silently summed, since that would need unit conversion this doesn't attempt. Generation is on-demand (`POST /shopping/generate`, blocked until the plan is finalized) and idempotent - regenerating an already-generated list just returns the existing one rather than duplicating it. |
| **Cook-along view** (`cook_step.html`/`cook_finish.html`, Milestone 6) | Server-rendered, no client-side step state (per `ui_design.md`'s implementation notes): each step is its own page at `GET /recipes/{id}/cook/{step_number}`, Prev/Next are plain links to `step_number ± 1`, and stepping past the last step renders the post-cook cooked/left-uncooked prompt directly - no session or database state tracks "where you are" in a session. `POST /recipes/{id}/cook/finish` does not touch the recipe itself; if that recipe is in the current plan, it marks that meal cooked via the same `MealPlanStore.set_cooked` the pot-stamp toggle calls. Reachable for any recipe, not just ones in this week's plan - the plan-meal-cooked side effect is skipped (not an error) when there's no matching plan meal. Deliberately outside the shared app-shell layout (no top bar/tab bar) for an uncluttered, phone-in-the-kitchen reading experience. |
| **Notifications** (`NotificationStore`, Milestone 7) | A single household-wide flag ("a new plan is ready"), not a queue or a per-user inbox - matches the non-goal of per-person state. Set when the scheduler auto-generates a plan; shown as an in-app banner (top of `recipes.html`/other pages, not `plan.html` itself since that page IS what it points to) linking to `/plan`; cleared the moment `/plan` is viewed. No email/push/SMS - see the Scheduler entry above. |
| **Recipe store** | The recipe library as a directory of Markdown files, one file per recipe (YAML frontmatter for structured fields — cook time, classification, nutrition, ingredients — plus a Markdown body for the ordered steps). Directly readable and editable by the user with any text editor; the backend treats this directory as the source of truth rather than caching it in a database. `RecipeStore.list()` normalizes a file it can't parse (broken/missing frontmatter, or a recipe hand-pasted in with no frontmatter at all) by running its raw text through the same LLM extraction pipeline a manual submission uses, then rewriting it to canonical form on disk - see "Recipe file normalization" below. |
| **Data store** | Persists everything that isn't a recipe: household preferences, meal plans, suggestions, and shopping lists (which reference recipes by filename/id in the recipe store). Shared by every device in the household — see "Remote access" below — not partitioned per user. |

## Technical decisions

| Decision | Choice | Rationale |
|---|---|---|
| Local LLM runtime | [Ollama](https://ollama.com), called over its local HTTP API | Required by the feature spec; keeps recipe text and preferences off third-party LLM APIs. Default model `qwen2.5-coder:14b` (overridable via `LITTLE_MEALS_OLLAMA_MODEL`) — chosen for structured/JSON-output reliability; not `llama3.1` since it isn't what's actually pulled on the reference dev machine. A larger general-purpose model (`qwen3.8`, 27B) is also pulled on that machine and was empirically tested as a possible default for better food-domain reasoning, but it reliably OOMs on the reference machine's GPU (`cudaMalloc failed: out of memory`) - not viable there, so `qwen2.5-coder:14b` stays the default; see the classification-reconciliation note below for how its one reproducible weak spot is handled instead of switching models. Called via `POST /api/generate` with `stream=false` and `format` set to the extraction JSON schema, falling back to plain `format="json"` mode if the server rejects the schema (older Ollama versions). |
| Classification reconciliation | `llm/extraction.py`'s `_reconcile_classification`, applied after every extraction | Empirically, `qwen2.5-coder:14b` follows the meat/poultry rule reliably but is inconsistent on simple fish-only dishes - a plain "baked salmon" or "tuna sandwich" sometimes comes back "other" even when `llm/prompts.py`'s classification rule names that exact dish as a worked pescetarian example (verified directly against the real model, not assumed). Prompt-only fixes were tried first and hit diminishing returns, so a deterministic keyword check over ingredient names now corrects the result afterward: any meat/poultry keyword forces "other" (checked first, so meat+fish together still resolves to "other"), a fish/shellfish keyword with no meat forces "pescetarian". It never guesses "vegetarian" from an unrecognized protein name - a keyword miss is treated as no signal, not proof of absence, so the model's own classification is trusted in that case. |
| Backend language/framework | Python, FastAPI | Consistent with the rest of the `little-projects` ecosystem (Python + Bazel + wheel packaging, per the [build policy](../../docs/policies/build_policy.md)); FastAPI's typed request/response models are a natural fit for the structured recipe schema the LLM extraction step produces. |
| Recipe storage | Markdown files (YAML frontmatter + Markdown body), one per recipe, under a `recipes/` directory | Recipes are the artifact the user most wants to own, read, and edit directly — plain text keeps them portable, diffable, and version-controllable independent of the app, and lets the user hand-edit a recipe without going through the UI. Not a database, so no query/migration layer to keep in sync with a format the user can also touch by hand. |
| Recipe file normalization | `RecipeStore.list(extractor)`: a file that fails to parse as canonical frontmatter is run through `RecipeExtractionService.extract()` on its raw text and rewritten in place; falls back to the pre-existing skip-with-a-log-warning behavior if no extractor is given or extraction itself fails | Direct hand-editing (the point of the Recipe storage decision above) means a user can drop in a recipe copy-pasted from a website, with no frontmatter at all, or break a field while editing - previously `list()` just silently skipped anything it couldn't parse, so that recipe quietly vanished from the library, the weekly plan, and every other listing until someone noticed and manually reformatted it. Reusing the same extraction pipeline a manual `POST /recipes/extract` submission goes through means one code path handles both "the user typed free text into the submit box" and "the user pasted free text directly into a file" identically. Rewriting the file after a successful normalization (not just returning the parsed `Recipe` in memory) means the LLM is only called once per bad file, not on every subsequent `list()` - see `tests/test_ollama_client_real.py`'s `test_real_ollama_normalizes_a_hand_dropped_in_recipe_file` for the real-model validation pass. `get()` by id is deliberately left alone - normalization is scoped to bulk listing, where an unnoticed file going missing is the actual problem being solved. |
| Other storage | SQLite, accessed via the backend only | Preferences, meal plans, and shopping lists are app-managed, not meant for direct user editing, and are naturally relational (plan → recipe references, generation timestamps). One shared household dataset, single host (see `design.md` non-goals — no per-user partitioning) — no need for a client/server database. Kept a plain file so backup is trivial. |
| Frontend | Server-rendered Jinja2 templates progressively enhanced with vendored htmx (`src/little_meals/static/vendor/htmx.min.js`, committed — not CDN-linked) | Decided at Milestone 1, not a React/Vite SPA: htmx is one committed JS file, so the frontend adds no node/npm system dependency (which would otherwise become a new tier in the preflight check below); rendering stays server-side, so a phone on the tailnet gets a working page with no build step; and it reuses the exact same FastAPI route layer as the JSON API rather than a separate client build. |
| Visual design | `docs/ui_design.md`'s design system, applied at Milestone 9 | Cream/terracotta/sage palette, Fraunces + Inter typography, and the cookbook/fridge-door/pinned-paper metaphors, implemented as plain CSS (`static/app.css`, `static/fonts.css`) plus native HTML disclosure (`<details>`/`<summary>` for the ingredients fridge-door toggle, `<input type="radio">` + `<label>` for the settings day-picker pills) — no client-side JS framework, consistent with the Frontend decision above. Fonts are vendored (`static/vendor/fonts/*.woff2`, SIL OFL-licensed) rather than linked from Google Fonts, for the same no-third-party-CDN reasoning as htmx. |
| Weekly scheduling | In-process `apscheduler` `BackgroundScheduler` (a thread, not asyncio - matches the rest of the backend's synchronous style), a 60s interval job wrapping `WeeklyScheduler.check_and_maybe_generate` - see the Scheduler component entry above | Single-user, single-host — no need for an external job queue/broker at this scale. Interval polling over a precise cron-style trigger specifically so a household preferences change doesn't require rescheduling anything. |
| Remote access | [Tailscale](https://tailscale.com) private mesh network (WireGuard-based) | See "Remote access & network security" below. |
| Deployment | `systemd --user` service + `bazel run //:deploy` | See "Deployment" below. |

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

## Deployment

Development happens by sending prompts to a Claude Code session running directly
on the home server (via Claude Remote Control), rather than editing locally and
pushing/pulling. The remaining gap that closes with Milestone 11 is getting an
accepted change from "edited on disk" to "actually running" without babysitting a
terminal for it.

**Chosen approach: `lmeals serve` as a `systemd --user` service, redeployed by a
single Bazel target.**

- `lmeals serve` runs under a user-level systemd unit
  (`~/.config/systemd/user/little-meals.service`) instead of a foreground
  terminal/tmux process. `Restart=on-failure` recovers it if it crashes;
  `systemctl --user enable little-meals` plus `loginctl enable-linger
  <user>` makes it start at boot and keep running after the Remote Control
  session that configured it ends — a bare foreground process would die the
  moment its shell session does, which defeats "reachable whenever I'm away
  from home."
- `bazel run //:deploy` is the one command to redeploy a change: it runs
  `//:install` (preflight + rebuild the wheel + `pipx install --force`) and then
  `systemctl --user restart little-meals`. Triggering it is a manual step taken
  in the Remote Control session once a change looks good — no CI/webhook/auto-
  deploy-on-save, since a change mid-edit shouldn't bounce the household's app.
- `bazel run //:relaunch` is a more defensive variant of the same idea, for
  when the service, `tailscaled`, and/or `tailscale serve` are in an unknown
  state (e.g. after a host reboot, or a stray manually-started `lmeals serve`
  from before this unit existed is holding the port): it stops the service,
  kills any `lmeals serve` process still holding port 8765, runs the same
  install-the-wheel step as `//:deploy`, starts the service back up, checks
  `tailscaled` is active (starting it if not — see `first_run.md`'s "Remote
  deployment" section for the passwordless-sudo caveat on that last part),
  and re-runs `tailscale serve --bg 8765` if `tailscale serve status` shows
  no config pointed at the app's port. That last check makes `//:relaunch`
  self-healing against the serve config silently going missing (observed in
  practice, cause unconfirmed), which `//:deploy` does not attempt. Every
  step is non-interactive by design, since it's meant to be safely
  triggerable from a Remote Control session with nobody watching —
  `tailscale serve` specifically needs `sudo tailscale set
  --operator=<user>` run once beforehand so it doesn't need root either.
- `tailscale serve` (Milestone 8) points at the service's fixed local port
  (`127.0.0.1:8765`) once, at Milestone 8 setup time, and needs no
  reconfiguration on any later deploy — restarting the systemd unit doesn't
  change the port it binds, so the tailnet hostname keeps working across
  deploys with zero extra steps.
- No blue/green or zero-downtime handoff: `systemctl restart` has a brief
  (sub-second, typically) gap while the new process starts. Acceptable at
  household scale — a two-person household — where a deploy is a rare,
  deliberate action taken by the person driving it, not a live multi-user cutover.

## Recipe storage format

Each recipe is one Markdown file under a `recipes/` directory (path configurable),
named for the recipe (e.g. `recipes/lemon-garlic-chicken.md`):

- **YAML frontmatter** holds the structured fields the app needs to query, filter,
  and combine recipes: title, estimated cook time, classification, nutrition
  estimate, and the ingredient list with quantities.
- **Markdown body** holds the ordered cooking steps as free text (e.g. a numbered
  list), which cook-along mode walks through.

The backend parses this directory as the source of truth — it does not maintain a
separate cached copy. When the app changes a recipe (a save from the recipe edit
page, a servings edit), it writes the change back to the file, not to a database
row. The user is free to hand-edit any recipe file directly (e.g. to fix a step or
tweak an ingredient); the app picks up the change the next time it reads that
file.

## Household preferences storage

Household preferences (recipes-per-week count, recommendation day/time plus its
`recommendation_enabled` toggle, auto-confirm day/time plus its
`auto_confirm_enabled` toggle (Milestone 14), default servings — see `design.md`'s
"Household preferences" concept) are a single row in SQLite (`household.db` under
the data directory), per the "Other storage" decision above — app-managed
configuration, not something the user is expected to hand-edit, and there is
exactly one of it per installation, not a collection.
`HouseholdPreferencesStore` (`store/household_store.py`) upserts that one row;
reading before any write returns built-in defaults rather than a not-found error,
since "unconfigured" is a normal, expected state, not an error condition. The M14
columns are added to a pre-existing database via an `ALTER TABLE ... ADD COLUMN`
migration on open (mirroring the pattern the legacy-column-drop migration already
established), defaulting to today's always-on recommendation behavior and
auto-confirm off, so an existing installation's behavior doesn't change until the
household opts in.
`/settings` is one form/action for all of the fields: saving it writes
recipes-per-week, both schedules' enabled/day/time, and default servings together
via `put()`. Free-text food preferences and a Spoonacular search filter existed on
a separate `/settings/recipe-preferences` page while Milestone 4's AI-suggestion
feature was live; both were removed along with it - see `milestones.md`'s M10
entry.
Preferences are exposed as a JSON API (`GET`/`PUT`/`DELETE` on
`/api/household-preferences` — `DELETE` resets to defaults rather than leaving the
household unconfigured) and as a server-rendered form, both in `api/`.

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
| `bazel run //:serve` | Run the web app (`uvicorn`), foreground, for local development. |
| `bazel run //:deploy` | Milestone 11: rebuild + `pipx install` the wheel, then restart the `little-meals` systemd `--user` service — see "Deployment" below. |
| `bazel run //:relaunch` | Milestone 11: like `//:deploy`, but also kills any stray `lmeals serve` process and ensures `tailscaled` + `tailscale serve` are up — see "Deployment" below. |
| `bazel test //...` | Run the unit test suite (hermetic, no network). |

The non-Bazel path (`pyproject.toml`, `pip install .`) exists for local/editable
development; Bazel is still the canonical build per the build policy.

## External dependencies

- **Ollama**, reachable over its HTTP API (`LITTLE_MEALS_OLLAMA_URL`, default
  `http://127.0.0.1:11434`) — not necessarily on the same host as the backend
  process, just reachable over the network (see "Local LLM runtime" above and the
  preflight check below). A host prerequisite: not pip-installable, so it can't be
  isolated by Bazel.

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
| `planning/` | `selection.py` (Milestone 3) - the library-only selection engine, a pure function over recipes, no I/O. `plan_builder.py` - `build_weekly_plan`, `generate_single_replacement`, `list_controlled_reroll_candidates`, and `build_meal_specs` (the shared "generate a fresh plan's meals" call every generation path - initial, whole-plan reroll, and the Milestone 7 scheduler - uses), all drawing only from the library (Milestone 4's online-search/combination suggestion generators were removed - see `milestones.md`'s M10 entry). `shopping_list.py` (Milestone 5) - `build_shopping_list_items`, the ingredient merge/scale logic. |
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
