# First run

A step-by-step guide to getting `little-meals` running from a clean checkout
and using it for the first time. See [`design.md`](design.md) for what the
app actually does and [`architecture.md`](architecture.md) for why it's built
this way — this doc is just the "how do I get it up" walkthrough.

## What you'll need

- Linux (including WSL2) with `python3`, `pipx`, and Bazel already usable.
- [Ollama](https://ollama.com) installed, with a model pulled (default:
  `qwen2.5-coder:14b`). This is the only hard dependency `bazel run
  //:install` checks for — see `preflight.py`.
- Optionally, a [Spoonacular](https://spoonacular.com/food-api) API key, if
  you want AI suggestions to pull from a real recipe search instead of just
  recombining recipes already in your library. Not required to run the app.

## 1. Build and install

From the repo root:

```
bazel run //:preflight   # checks python3, pipx, and ollama are present
bazel run //:install     # runs preflight, then pipx-installs the CLI
```

`//:install` refuses to continue if preflight finds something missing, and
tells you exactly what to install. Once it succeeds, `lmeals` is on your
`PATH`.

**WSL note**: if Ollama is installed on the Windows side rather than inside
WSL, `ollama` won't be on the WSL `PATH` — preflight detects WSL and checks
reachability over HTTP (`curl http://127.0.0.1:11434/api/tags`) instead of
looking for the binary, so this works without extra setup as long as Ollama
is actually running on the Windows host.

## 2. Make sure Ollama is actually serving

```
curl http://127.0.0.1:11434/api/tags
```

Should return JSON listing your pulled models. If it doesn't:

```
ollama serve                        # start the daemon (foreground)
ollama pull qwen2.5-coder:14b       # pull the default model, if you haven't
```

If you want a different model, set `LITTLE_MEALS_OLLAMA_MODEL` before
starting the server (step 4).

## 3. (Optional) Configure Spoonacular

Skip this the first time through — the app works fully without it, just
without one of the two AI-suggestion sources (see `architecture.md`'s
"Online recipe search" row). Come back to it once you want that.

Two ways to configure the key, pick one:

- **Quick, for testing**: `export LITTLE_MEALS_SPOONACULAR_API_KEY=<your key>`
- **Recommended, for actual use**: encrypt it once, decrypt at server
  startup:

  ```
  openssl enc -aes-256-cbc -pbkdf2 -salt -in key.txt -out spoonacular.enc
  chmod 600 spoonacular.enc
  export LITTLE_MEALS_SPOONACULAR_KEY_FILE=~/.vault/spoonacular.enc  # wherever you put it
  ```

  `lmeals serve` will prompt for the passphrase on startup and hold the
  decrypted key in memory only — see `architecture.md`'s "Spoonacular API key
  storage" row for why.

## 4. Start the server

```
lmeals serve
```

- Prompts for the vault passphrase first, if `LITTLE_MEALS_SPOONACULAR_KEY_FILE`
  is set.
- Once you see `Uvicorn running on http://127.0.0.1:8765`, open that URL in a
  browser. On WSL2, this is normally reachable from a Windows browser at the
  same address without any extra port-forwarding.
- `lmeals serve --host 0.0.0.0` if you want it reachable from another device
  on the same network (e.g. a phone) instead of just `localhost`. For access
  from outside your home network entirely, see `architecture.md`'s "Remote
  access & network security" section (Tailscale) — not needed for a first
  run.

Leave this running in its own terminal — it's the whole app (frontend and
API in one process). `Ctrl+C` to stop it.

## 5. Walk through the app once

The recipe library starts empty. A sensible first pass:

1. **`/settings`** — review the household preferences (recipes per week, AI
   suggestions per plan, recommendation day/time, food preferences, default
   servings). Sane defaults are already in effect even if you skip this —
   5 recipes/week, 2 of them AI-suggested, Sundays at 09:00 — but it's worth
   a look before your first plan generates.

2. **`/recipes/new`** — add 2-3 recipes by pasting in free text (a copied
   recipe, or just plain description of how you make something). Each
   submission goes through the local LLM for extraction (cook time,
   classification, nutrition estimate, ingredients, steps) — this is the
   slowest step in the app, give it a few seconds. Add at least two you'd
   mark "liked" (the default) — the AI suggestion engine needs at least two
   liked recipes in the library to generate a combination suggestion if
   Spoonacular isn't configured, so a plan generated against an empty
   library will come back short (see `plan_builder.py`: "a shorter plan
   beats no plan," it won't error, just skip what it can't fill).

3. **`/recipes`** — confirm they extracted sensibly. You can edit or delete
   any of them here, or open one to check the parsed ingredients/steps.

4. **`/plan`** — generate a weekly plan. It fills the library-drawn slots
   from what you just added, then tops up with AI suggestions (search, if
   configured, else combining two liked recipes). Like/dislike each meal,
   adjust servings, or reroll (whole plan, one meal, or a controlled reroll
   offering ten alternatives for a single slot) if something doesn't land.
   Finalize the plan once you're happy — this locks it and unblocks the
   shopping list.

5. **`/shopping`** — generate the shopping list for the finalized plan.
   Ingredients are merged and scaled across all the week's recipes. Check
   things off as you shop, and record the actual cost once you're done.

6. **`/recipes/{id}/cook`** (a "Cook along" link from a recipe page or a plan
   meal) — walk through a recipe step by step. Finishing prompts you to
   like/dislike based on how it actually turned out, and marks the meal
   cooked if it's in the current plan.

## Running it day to day

`lmeals serve` (or `bazel run //:serve`) is the whole thing — run it
whenever you want to use the app, no separate build step needed afterward
unless the code changes (then `bazel run //:install` again to pick up a new
wheel). The weekly scheduler inside the server checks every 60 seconds
whether it's past your configured recommendation day/time and the current
plan predates it, auto-generating a fresh one and flagging an in-app
notification banner when it does — no cron job or separate process needed.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `bazel run //:install` stops at "local LLM runtime" | Ollama isn't installed/reachable — see step 2. |
| `lmeals: command not found` after install | pipx's bin dir isn't on `PATH` in this shell — check `pipx list` shows `little-meals`, then add `~/.local/bin` to `PATH` (or open a new shell). |
| Recipe extraction hangs or times out | Ollama isn't actually serving, or the configured model isn't pulled — recheck step 2. `LITTLE_MEALS_OLLAMA_TIMEOUT` (seconds, default 120) if it's just slow on your hardware. |
| A plan generates with fewer meals than configured | Not enough liked library recipes and no search provider configured — see step 5.2. Not a bug: a short plan beats a failed one. |
| Server prompts for a vault passphrase you don't want to enter right now | Unset `LITTLE_MEALS_SPOONACULAR_KEY_FILE` for that run, or set an empty `LITTLE_MEALS_SPOONACULAR_API_KEY`-free environment — Spoonacular is optional. |
| A recipe file you hand-edited (or dropped in from elsewhere) doesn't show up in the library | It's likely not valid Markdown+YAML-frontmatter — `RecipeStore.list()` normalizes it through the same LLM extraction pipeline automatically (see `architecture.md`'s "Recipe file normalization" row); if that also fails, it's skipped with a warning logged rather than crashing the page. |
