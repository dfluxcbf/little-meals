# little-meals

Meal planning facilitator and recipe book. See [`docs/design.md`](docs/design.md)
for purpose and concepts, [`docs/ui_design.md`](docs/ui_design.md) for the
visual design system, [`docs/architecture.md`](docs/architecture.md) for
technical decisions, and [`docs/milestones.md`](docs/milestones.md) for the
implementation roadmap.

Status: Milestones 1-3 and 5-9 implemented (recipe ingestion, household
preferences, visual design system, weekly plan generation from the recipe
library, reroll among library recipes, shopping list, cook-along, weekly
scheduling). Milestone 4's AI-suggestion/Spoonacular integration was removed
entirely (see M10 in `docs/milestones.md`) - meal planning now draws only
from recipes already in the cookbook. Milestone 8 (Tailscale remote access)
is host/network setup, not application code - see `docs/milestones.md`.

## Quickstart

```
bazel run //:preflight   # check system dependencies (ollama, pipx)
bazel run //:install     # preflight-gated pipx install of the CLI
lmeals serve              # or: bazel run //:serve
```

`lmeals settings --reset` resets the general household settings (recipes per
week, recommendation day/time, default servings) back to their defaults, and
permanently deletes every meal plan and shopping list - useful for starting a
fresh planning cycle without losing what the household already set up. It
leaves the recipe library untouched. Prompts for confirmation with the counts
to be deleted, unless `--yes` is also passed.

Runtime configuration is via environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `LITTLE_MEALS_DATA_DIR` | `~/.local/share/little-meals` | Where the `recipes/` Markdown library lives. |
| `LITTLE_MEALS_OLLAMA_URL` | `http://127.0.0.1:11434` | Ollama's HTTP API base URL. |
| `LITTLE_MEALS_OLLAMA_MODEL` | `qwen2.5-coder:14b` | Model used for recipe extraction. |
| `LITTLE_MEALS_OLLAMA_TIMEOUT` | `120` | HTTP timeout (seconds) for a single Ollama extraction call. Raise this if a recipe submission fails with "didn't respond within Ns" - a cold model load or an unusually long/verbose recipe (many ingredients, long instructions) on slower hardware can exceed the default. |
