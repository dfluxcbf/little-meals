# little-meals — Claude Code notes

Meal planning facilitator and recipe book for a 2-person household. See
[`README.md`](README.md) and [`docs/architecture.md`](docs/architecture.md)
for the full picture. This file is just the things Claude should already know
before poking around.

## Requirements tracking: little-requirements

Requirements and test coverage are tracked exclusively through
**little-requirements** (`lreq` CLI / `mcp__little-requirements__*` tools),
against a project database at `bundle-littles/req_db/little-meals_reqs.db`
(project id `little-meals-reqs`) — **never** by hand-editing requirement docs.
Tests get tagged `@pytest.mark.requirement("REQ-XXXXXXXXX")`. Full details,
per-milestone requirement ID ranges, and the `.reqs/` workspace setup:
[`docs/requirements_policy.md`](docs/requirements_policy.md).

## Git lifecycle: little-versions

Branching and version bumps are managed exclusively through
**little-versions** (`lvx` CLI / `mcp__little-versions__*` tools) — never by
hand. Production branch is `master`, integration branch is `dev`
(`.lvx/config.json`). A version bump hook
(`tools/on_version_bump.py`) propagates the version into `pyproject.toml`,
`MODULE.bazel`, `src/little_meals/BUILD.bazel`, and
`src/little_meals/__init__.py`. Full details:
[`docs/version_policy.md`](docs/version_policy.md).

## Relaunching the running app: `bazel run //:relaunch`

The app runs as a `little-meals.service` systemd `--user` service on this
host, reachable over Tailscale (`tailscale serve`) — see "Deployment" and
"Remote access & network security" in `docs/architecture.md`. When you need
to pick up a code change, or something's just stuck, use:

```
bazel run //:relaunch
```

This is the one command that gets the app from "edited on disk" to "actually
running and reachable" — it stops the service (and kills any stray,
manually-started `lmeals serve` holding port 8765), rebuilds + reinstalls the
wheel (same as `//:install`), restarts the service, and makes sure both
`tailscaled` and `tailscale serve` are up (self-healing a lost `tailscale
serve` config). Every step is non-interactive, so it's safe to run from a
remote session (e.g. Claude Remote Control) unattended. `bazel run //:deploy`
is the lighter-weight version of the same idea (no stray-process cleanup, no
tailscale checks) — reach for `//:relaunch` unless you know the service is
already in a known-good state. Full details: `docs/first_run.md`'s "Remote
deployment" section and `docs/architecture.md`'s "Deployment" section.

## Other canonical Bazel targets

See the header comment in [`BUILD.bazel`](BUILD.bazel) for the full list
(`//:preflight`, `//:install`, `//:serve`, `//:deploy`, `//:relaunch`,
`//:test`, `//:requirements.update`).
