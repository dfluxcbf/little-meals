---
paths:
  - "tools/**"
  - "BUILD.bazel"
  - "docs/first_run.md"
  - "docs/architecture.md"
  - "src/little_meals/cli.py"
  - "src/little_meals/config.py"
---
# Running and deploying

- little-workshop's Deployment pillar runs the household's server (`workshop_deployment_deploy`, `_stop`,
  `_status`, or `lws deployment ... --project-id little-meals`): `lmeals serve` on port 8765, with the data in
  `~/.local/share/little-meals` (`LITTLE_MEALS_DATA_DIR` overrides it; `src/little_meals/config.py`).
- `bazel run //:relaunch` (`tools/relaunch_main.py`) kills `lmeals serve` so that a little-termstyle supervisor
  restarts it; that supervisor is no longer installed, so nothing does: do not use it. `bazel run //:deploy`
  (`tools/deploy_main.py`, `tools/little-meals.service`) is the older systemd `--user` path the Deployment pillar
  superseded.
- `docs/first_run.md` ("Remote deployment") still describes that systemd unit, and `docs/architecture.md`
  ("Deployment") describes `little-runner`'s `lrun server up` as current. Verify before relying on either, and
  correct what is stale.
- To try a change, run a separate server from source on port 8766 with a scratch data dir: the `try-the-app`
  skill.
