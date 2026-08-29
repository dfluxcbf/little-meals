# little-meals

Meal planning facilitator and recipe book. See [`docs/design.md`](docs/design.md)
for purpose and concepts, [`docs/ui_design.md`](docs/ui_design.md) for the
visual design system, [`docs/architecture.md`](docs/architecture.md) for
technical decisions, and [`docs/milestones.md`](docs/milestones.md) for the
implementation roadmap.

Status: Milestones 1-7 and 9 implemented (recipe ingestion, household
preferences, visual design system, weekly plan generation, AI suggestions +
reroll, shopping list, cook-along, weekly scheduling). Milestone 8 (Tailscale
remote access) is host/network setup, not application code - see
`docs/milestones.md`.

## Quickstart

```
bazel run //:preflight   # check system dependencies (ollama, pipx)
bazel run //:install     # preflight-gated pipx install of the CLI
lmeals serve              # or: bazel run //:serve
```

`lmeals import-spoonacular [--count N]` bulk-imports recipes straight into the
library from Spoonacular, sized to N (or the household's `recipes_per_week`
setting if `--count` is omitted), searching with the household's saved
Spoonacular query (`/settings` → "Edit recipe search preferences" → its own
dedicated page covering every `/recipes/complexSearch` parameter as text
fields and single/multi-select pill groups, no JSON required; see
`docs/spoonacular_api.md`/`docs/spoonacular_schema.yaml` for what each
parameter means; the command errors out if none has been
saved yet). Safe to run while
`lmeals serve` is already running. Needs the same Spoonacular API key
configuration as the AI-suggestion search source below. Add `--reset` to
delete every existing recipe first (prompts for confirmation with the count
to be deleted, unless `--yes` is also passed) -
useful for replacing a library wholesale rather than adding to it.

`lmeals settings --reset` resets the general household settings (recipes per
week, recommendation day/time, AI suggestions per plan, default servings) back
to their defaults, and permanently deletes every meal plan and shopping list -
useful for starting a fresh planning cycle without losing what the household
already set up. It deliberately leaves the food preferences text, the saved
Spoonacular query, and the recipe library untouched. Prompts for confirmation with the
counts to be deleted, unless `--yes` is also passed.

Runtime configuration is via environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `LITTLE_MEALS_DATA_DIR` | `~/.local/share/little-meals` | Where the `recipes/` Markdown library lives. |
| `LITTLE_MEALS_OLLAMA_URL` | `http://127.0.0.1:11434` | Ollama's HTTP API base URL. |
| `LITTLE_MEALS_OLLAMA_MODEL` | `qwen2.5-coder:14b` | Model used for recipe extraction. |
| `LITTLE_MEALS_OLLAMA_TIMEOUT` | `120` | HTTP timeout (seconds) for a single Ollama extraction call. Raise this if imports/suggestions fail with "didn't respond within Ns" - a cold model load or an unusually long/verbose recipe (many ingredients, long instructions) on slower hardware can exceed the default. |
| `LITTLE_MEALS_SPOONACULAR_API_KEY` | unset | [Spoonacular](https://spoonacular.com/food-api) API key for AI-suggested recipes' online search source (Milestone 4). Unset means suggestions come from combining stored recipes only - see `docs/architecture.md`'s "Online recipe search" row. Ignored if `LITTLE_MEALS_SPOONACULAR_KEY_FILE` is also set. |
| `LITTLE_MEALS_SPOONACULAR_KEY_FILE` | unset | Path to an `openssl enc -aes-256-cbc -pbkdf2`-encrypted file holding the Spoonacular API key - the recommended way to configure it, over the plaintext env var above. `lmeals serve` prompts for the vault passphrase on startup and decrypts it in-memory - see `docs/architecture.md`'s "Spoonacular API key storage" row. Encrypt a key with e.g. `openssl enc -aes-256-cbc -pbkdf2 -salt -in key.txt -out spoonacular.enc && chmod 600 spoonacular.enc`. |
| `LITTLE_MEALS_SPOONACULAR_BASE_URL` | `https://api.spoonacular.com` | Override for testing against a different Spoonacular-API-compatible endpoint. |
| `LITTLE_MEALS_SPOONACULAR_TIMEOUT` | `15` | HTTP timeout (seconds) for Spoonacular requests. |
