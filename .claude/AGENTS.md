# little-meals

<!-- A briefing, loaded into every session: what the project is, the commands Claude cannot guess, the gotchas
and where to start. Guidance for one part of the tree is in .claude/rules/ (`paths:` frontmatter: tests.md,
versioning.md, deployment.md), procedures are skills (.claude/skills/), and a rule that must hold every time is a
hook or a little-workshop policy. This file is .claude/AGENTS.md on purpose: Claude Code reads AGENTS.md only where
the project has no CLAUDE.md, .claude/CLAUDE.md or CLAUDE.local.md, and the guard refuses those. The last line
imports the section little-workshop generates for every project (.claude/little-workshop.md). -->

A meal-planning facilitator and recipe book for one two-person household: design for that scale, not for many
users or tenants. Python 3.12, FastAPI, Bazel (`rules_python`), packaged as a wheel and run as `lmeals serve`.
Read `README.md` and `docs/architecture.md` for the full picture, and `docs/ui_design.md` before changing a page.

## Commands

- Tests: `bazel test //...` (the unit suite), or one file from source with
  `PYTHONPATH=src python3 -m pytest tests/<file> -q`.
- Build and install: `bazel build //:all`; `bazel run //:install` runs the preflight, then pipx-installs `lmeals`.
- Try a change in the running app: the `try-the-app` skill serves this checkout on port 8766 with a scratch
  data dir.

## The household's server

little-workshop's Deployment pillar runs the real server on port 8765 against the household's data
(`workshop_deployment_status`, `_deploy`, `_stop`). It runs on demand and being down is normal: redeploy it only
when the user wants the live app updated, and never bind a test server to 8765. The older `bazel run //:relaunch`
and `//:deploy` paths are described in `.claude/rules/deployment.md`.

@little-workshop.md
