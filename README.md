# little-meals

Meal planning facilitator and recipe book. See [`docs/design.md`](docs/design.md)
for purpose and concepts, [`docs/ui_design.md`](docs/ui_design.md) for the
visual design system, [`docs/architecture.md`](docs/architecture.md) for
technical decisions, and [`docs/milestones.md`](docs/milestones.md) for the
implementation roadmap.

Status: Milestones 1-3 and 5-11 implemented (recipe ingestion, household
preferences, visual design system, weekly plan generation from the recipe
library, reroll among library recipes, shopping list, cook-along, weekly
scheduling, Tailscale remote access, remote deployment). Milestone 4's
AI-suggestion/Spoonacular integration was removed entirely (see M10 in
`docs/milestones.md`) - meal planning now draws only from recipes already in
the cookbook. Milestone 1's Ollama-backed extraction pipeline was likewise
removed entirely (see M16) - recipes are entered/edited directly. Milestones
8 (Tailscale remote access) and 11 (remote deployment via a systemd service +
`bazel run //:deploy`) are host/network setup, not application code - see
`docs/milestones.md`.

## Quickstart

```
bazel run //:preflight   # check system dependencies (python3, pipx)
bazel run //:install     # preflight-gated pipx install of the CLI
lmeals serve              # or: bazel run //:serve
```

`lmeals settings --view` prints the current data directory and household
settings (recipes per week, recommendation/auto-confirm day/time, default
servings) and their values.

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
