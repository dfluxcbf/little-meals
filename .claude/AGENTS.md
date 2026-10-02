# little-meals

A meal-planning facilitator and recipe book for a two-person household. Python 3.12, FastAPI, Bazel
(`rules_python`), packaged as a wheel and run as `lmeals serve`. Read `README.md` and `docs/architecture.md` for the
full picture; this file is what Claude should know before poking around.

This file is `.claude/AGENTS.md` on purpose: Claude Code reads `AGENTS.md` (also as `.claude/AGENTS.md`) only
where a project has no `CLAUDE.md`, so never add a `CLAUDE.md` here, or this file stops being loaded.

## Requirements and versions: little-workshop

Requirements and test coverage are managed through little-workshop's Requirements pillar
(`workshop_requirements_*`, `lws requirements`), never by hand-editing requirement docs. Tests are tagged
`@pytest.mark.requirement("REQ-XXXXXXXXX")`; per-milestone requirement id ranges and the `.reqs/` setup are in
`docs/requirements_policy.md`. Branching and version bumps go through `workshop_version_*` / `lws version`, never by
hand: production branch `master`, integration branch `dev` (`.lvx/config.json`). The version hook
`tools/on_version_bump.py` propagates `VERSION` into `pyproject.toml`, `MODULE.bazel`,
`src/little_meals/BUILD.bazel` and `src/little_meals/__init__.py`.

`docs/requirements_policy.md` and `docs/version_policy.md` still say requirements and versions are managed
exclusively through `lreq` and `lvx` and a `bundle-littles` database. Those tools were uninstalled on 2026-09-22 and
absorbed by little-workshop, whose pillars are the system of record: follow the live system and correct the stale doc.

## Running the app

The server is managed by little-workshop's Deployment pillar: `workshop_deployment_status`, `_deploy` and `_stop`
(or `lws deployment status|deploy|stop --project-id little-meals`). It runs on demand; down is normal, so do not
restart it unless asked.

Canonical Bazel targets (header of `BUILD.bazel`): `//:preflight`, `//:install`, `//:serve`, `//:deploy`,
`//:relaunch`, `//:test`, `//:requirements.update`. `bazel run //:relaunch` (`tools/relaunch_main.py`) was written
for a `little-termstyle` mux supervisor that is no longer installed (`lterm` is gone), so do not use it to restart
the server; redeploy with `workshop_deployment_deploy` instead. `//:deploy` is the older systemd `--user` path.
`docs/first_run.md` ("Remote deployment") and `docs/architecture.md` ("Deployment") still describe the termstyle
setup: verify before relying on them, and correct what is stale.

## Lifecycle goes through little-workshop

This project is registered in little-workshop as `little-meals`. Branch finishes, releases, deploys and publishes go
through the `little-workshop` MCP server (tools `workshop_<pillar>_*`, registered at user scope as `lws mcp serve`)
or the `lws` CLI, because that is where the project's policies are checked. `.claude/settings.json` denies the raw
git, systemd and twine forms.

| To do this | Use |
|---|---|
| Start / finish a feature, improvement, hotfix | `workshop_version_<type>_start` / `_finish` (never `git merge`) |
| Cut or finish a release, tag | `workshop_version_release_*`, `workshop_version_release_candidate_*` |
| Deploy, stop or inspect a server | `workshop_deployment_*` |
| Publish a package | `workshop_build_publish_*` |
| Record requirements and test runs | `workshop_requirements_*` |
| See what a gated action would hit, and why | the `policy-preflight` skill (`workshop_policy_evaluate`) |
| Push / create the GitHub repository | `workshop_project_connect_github` |

## What enforces the rules

The project's rules are Policy & Compliance policies, checked by code rather than remembered:

- On every commit, `.githooks/commit-msg` runs the policies that gate `commit` (VERSION bumps and format,
  requirement citations) and refuses a commit that breaks one, printing the rule and how to fix it. Fix it and
  commit again (`--no-verify` is denied). On `feature/` and `improvement/` branches `.githooks/pre-commit` writes
  `VERSION` for you.
- Before a gated action (finish, release, deploy, publish) little-workshop runs the policies gating it, and a
  failure holds the action in `pending_confirmation`. Run the `policy-preflight` skill first and fix what it
  reports; if an action is still held, report it rather than working around it.
- Decisions that stand in for a human (`workshop_policy_confirm`, `workshop_agent_finish_task`/`skip_task`,
  scheduling, project registration) always prompt.

## Scope: this project only

This session belongs to `little-meals`. Name it in every call: `project_id` `little-meals` for a tool, `--project-id little-meals`
for `lws`. `.claude/settings.json` pre-allows only those forms, and the hook `.claude/hooks/lws_scope_guard.py`
denies a call that names another project or leaves the id out where that would mean every project. Registering
or removing projects, authoring policies, scheduling and other cross-project work belong in a session started
from `little-projects`, which allows all of little-workshop.
