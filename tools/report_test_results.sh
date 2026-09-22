#!/usr/bin/env bash
# Runs the full pytest suite through a venv that has little-requirements
# installed, so its pytest11 plugin
# (little_requirements.tracing.pytest_plugin) can auto-record pass/fail
# results for every @pytest.mark.requirement(...)-tagged test into the
# project's requirements DB (resolved via .reqs/database.conf).
#
# This is a separate, manually/CI-run reporting step - NOT part of the
# hermetic `bazel test //...` path, which never sees little-requirements
# and must keep working unchanged.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# shellcheck disable=SC1091
source .venv/bin/activate

exec pytest "$@"
