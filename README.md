# little-meals

Meal planning facilitator and recipe book. See [`docs/design.md`](docs/design.md)
for purpose and concepts, [`docs/ui_design.md`](docs/ui_design.md) for the
visual design system, [`docs/architecture.md`](docs/architecture.md) for
technical decisions, and [`docs/milestones.md`](docs/milestones.md) for the
implementation roadmap.

Status: Milestone 1 (recipe ingestion) implemented.

## Quickstart

```
bazel run //:preflight   # check system dependencies (ollama, pipx)
bazel run //:install     # preflight-gated pipx install of the CLI
lmeals serve              # or: bazel run //:serve
```

Runtime configuration is via environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `LITTLE_MEALS_DATA_DIR` | `~/.local/share/little-meals` | Where the `recipes/` Markdown library lives. |
| `LITTLE_MEALS_OLLAMA_URL` | `http://127.0.0.1:11434` | Ollama's HTTP API base URL. |
| `LITTLE_MEALS_OLLAMA_MODEL` | `qwen2.5-coder:14b` | Model used for recipe extraction. |
