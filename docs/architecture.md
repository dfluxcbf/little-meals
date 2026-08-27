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
| **Suggestion engine** | Builds candidate recipes on demand: the configured number of new AI-suggested recipes for a fresh weekly plan (some by combining stored recipes, some via online search seeded by food preferences + library), plus on-demand reroll requests — replace every open slot in a draft plan, replace one slot with a single new suggestion, or replace one slot with a batch of 10 alternatives — each candidate passed through the recipe extraction service. Excludes disliked recipes from both the stored-recipe pool and the material it combines from. |
| **Scheduler** | Triggers weekly meal-plan generation at the user-configured day/time. |
| **Shopping list generator** | Merges ingredients across a finalized plan's recipes, scaling each recipe's quantities to its servings count, producing one deduplicated checklist. |
| **Recipe store** | The recipe library as a directory of Markdown files, one file per recipe (YAML frontmatter for structured fields — cook time, classification, nutrition, ingredients, liked/disliked state — plus a Markdown body for the ordered steps). Directly readable and editable by the user with any text editor; the backend treats this directory as the source of truth rather than caching it in a database. |
| **Data store** | Persists everything that isn't a recipe: household preferences, meal plans, suggestions, and shopping lists (which reference recipes by filename/id in the recipe store). Shared by every device in the household — see "Remote access" below — not partitioned per user. |

## Technical decisions

| Decision | Choice | Rationale |
|---|---|---|
| Local LLM runtime | [Ollama](https://ollama.com), called over its local HTTP API | Required by the feature spec; keeps recipe text and preferences off third-party LLM APIs. Specific model left open until Milestone 1, chosen for structured-output reliability at whatever hardware the project runs on. |
| Backend language/framework | Python, FastAPI | Consistent with the rest of the `little-projects` ecosystem (Python + Bazel + wheel packaging, per the [build policy](../../docs/policies/build_policy.md)); FastAPI's typed request/response models are a natural fit for the structured recipe schema the LLM extraction step produces. |
| Recipe storage | Markdown files (YAML frontmatter + Markdown body), one per recipe, under a `recipes/` directory | Recipes are the artifact the user most wants to own, read, and edit directly — plain text keeps them portable, diffable, and version-controllable independent of the app, and lets the user hand-edit a recipe without going through the UI. Not a database, so no query/migration layer to keep in sync with a format the user can also touch by hand. |
| Other storage | SQLite, accessed via the backend only | Preferences, meal plans, suggestions, and shopping lists are app-managed, not meant for direct user editing, and are naturally relational (plan → recipe references, generation timestamps). One shared household dataset, single host (see `design.md` non-goals — no per-user partitioning) — no need for a client/server database. Kept a plain file so backup is trivial. |
| Frontend | Server-rendered pages progressively enhanced with a small amount of client-side JS, framework TBD at Milestone 1 (candidates: htmx, or a minimal React/Vite SPA) | Deferred until the API shape from Milestone 1 (recipe CRUD) exists; no UI framework decision should predate the API it renders. |
| Online recipe search | Provider TBD at the milestone that implements AI suggestions | Needs to weigh available web-search APIs against cost/rate limits; deferred rather than picked speculatively. |
| Weekly scheduling | In-process scheduler (e.g. APScheduler) triggered by the backend process | Single-user, single-host — no need for an external job queue/broker at this scale. |
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
