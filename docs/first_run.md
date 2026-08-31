# First run

A step-by-step guide to getting `little-meals` running from a clean checkout
and using it for the first time. See [`design.md`](design.md) for what the
app actually does and [`architecture.md`](architecture.md) for why it's built
this way — this doc is just the "how do I get it up" walkthrough.

## What you'll need

- Linux (including WSL2) with `python3`, `pipx`, and Bazel already usable.
  These are the only hard dependencies `bazel run //:install` checks for —
  see `preflight.py`.

## 1. Build and install

From the repo root:

```
bazel run //:preflight   # checks python3 and pipx are present
bazel run //:install     # runs preflight, then pipx-installs the CLI
```

`//:install` refuses to continue if preflight finds something missing, and
tells you exactly what to install. Once it succeeds, `lmeals` is on your
`PATH`.

## 2. Start the server

```
lmeals serve
```

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

## 3. Walk through the app once

The recipe library starts empty. A sensible first pass:

1. **`/settings`** — review the household preferences (recipes per week,
   recommendation day/time, default servings). Sane defaults are already in
   effect even if you skip this — 5 recipes/week, Sundays at 09:00 — but
   it's worth a look before your first plan generates.

2. **`/recipes/new`** — add a handful of recipes directly: name, nutrition
   (optional), an ingredients table, and cooking steps, each as its own
   add/remove-able row. A plan can only be built from recipes already in the
   library, so add at least as many as your `recipes_per_week` setting if
   you want a full plan on the first try - a smaller library just yields a
   shorter plan rather than an error (see `plan_builder.py`: "a shorter plan
   beats no plan").

3. **`/recipes`** — confirm they look right. You can edit or delete any of
   them here, or open one to check the ingredients/steps.

4. **`/plan`** — generate a weekly plan. It draws recipes from the library
   you just built, up to your configured `recipes_per_week` count. Adjust
   servings, or reroll (whole plan, one meal, or a controlled reroll offering
   ten alternatives for a single slot, always among your own library recipes)
   if something doesn't land. Finalize the plan once you're happy — this
   locks it and unblocks the shopping list.

5. **`/shopping`** — generate the shopping list for the finalized plan.
   Ingredients are merged and scaled across all the week's recipes. Check
   things off as you shop, and record the actual cost once you're done.

6. **`/recipes/{id}/cook`** (a "Cook along" link from a recipe page or a plan
   meal) — walk through a recipe step by step. Finishing prompts you to
   mark it cooked or leave it uncooked, and marks the meal cooked in the
   current plan if it's in it.

## Running it day to day

`lmeals serve` (or `bazel run //:serve`) is the whole thing — run it
whenever you want to use the app, no separate build step needed afterward
unless the code changes (then `bazel run //:install` again to pick up a new
wheel). The weekly scheduler inside the server checks every 60 seconds
whether it's past your configured recommendation day/time and the current
plan predates it, auto-generating a fresh one and flagging an in-app
notification banner when it does — no cron job or separate process needed.

## Remote deployment (Milestone 11)

If you're developing by sending prompts to a Claude Code session running
directly on the home server (e.g. via Claude Remote Control), you'll want
`lmeals serve` running as a background service you can redeploy in one
command, rather than a foreground process tied to a terminal session. This
is one-time setup; after it's done, every later change is just `bazel run
//:deploy`.

**One-time setup:**

```
mkdir -p ~/.config/systemd/user
cp tools/little-meals.service ~/.config/systemd/user/little-meals.service
systemctl --user daemon-reload
systemctl --user enable --now little-meals.service
loginctl enable-linger $(whoami)   # keeps it running after you log out
```

`enable --now` starts it immediately in addition to enabling it at boot. If
something (e.g. a manually-started `lmeals serve`) is already holding port
8765, stop that first (`kill <pid>`) or the service will fail to bind and
sit in an auto-restart loop — check with `systemctl --user status
little-meals.service`.

**Every later deploy**, once a change looks good:

```
bazel run //:deploy   # rebuild + pipx reinstall + systemctl --user restart
```

This is the same preflight-gated rebuild `//:install` does, followed by
`systemctl --user restart little-meals.service` — see `architecture.md`'s
"Deployment" section for why it's structured this way. It doesn't touch
`tailscale serve` (Milestone 8) — that keeps pointing at the same local port
across restarts, so nothing else needs to change on the tailnet side.

**If something's stuck** (a stray manually-started `lmeals serve` is holding
the port, `tailscaled` itself got stopped, or `tailscale serve` lost its
config), use the more defensive `bazel run //:relaunch` instead: it stops the
service *and* kills any `lmeals serve` process still holding port 8765,
reinstalls, starts the service back up, checks `tailscaled` is active
(starting it via `sudo systemctl start tailscaled` if not — see the note
below on passwordless sudo), and re-points `tailscale serve` at port 8765 if
`tailscale serve status` shows no config for it. Safe to reach for any time
`//:deploy` would also work; it just does a bit more. Every step is
non-interactive, so it's safe to run from a remote Claude Code session (e.g.
via Claude Remote Control) with nobody at the keyboard.

Starting `tailscaled` needs root. If `sudo` on this host requires a password,
`//:relaunch` will print a warning rather than hang waiting for one — grant
passwordless `sudo systemctl start tailscaled` (e.g. a `visudo` NOPASSWD rule
scoped to that one command) if you want a remote relaunch to be able to fix a
stopped `tailscaled` on its own; otherwise start it manually when needed.

Re-pointing `tailscale serve`, by contrast, does *not* need root, as long as
you've run `sudo tailscale set --operator=<you>` once (a one-time host
setup step — makes your user the operator of the local `tailscaled`, so
`tailscale serve`/`funnel` never need `sudo` again). Without that, a lost
`tailscale serve` config will fail to auto-heal and `//:relaunch` will print
a warning instead.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `lmeals: command not found` after install | pipx's bin dir isn't on `PATH` in this shell — check `pipx list` shows `little-meals`, then add `~/.local/bin` to `PATH` (or open a new shell). |
| A plan generates with fewer meals than configured | Not enough recipes in the library yet — see step 3.2. Not a bug: a short plan beats a failed one, and meal planning only ever draws from recipes already saved. |
| A recipe file you hand-edited (or dropped in from elsewhere) doesn't show up in the library | It's likely not valid Markdown+YAML-frontmatter — `RecipeStore.list()` skips anything it can't parse, with a warning logged, rather than crashing the page. Fix the file's frontmatter and it'll show up on the next read. |
| `bazel run //:deploy` fails at `systemctl restart` with "Unit little-meals.service not found" | The systemd unit hasn't been installed yet — see the "Remote deployment" setup steps above. |
