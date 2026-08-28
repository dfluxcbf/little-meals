# Version policy

This project follows the super-repo's
[version policy](../../docs/policies/version_policy.md). Branching and version
bumps are managed exclusively through **little-versions** (`lvx` /
`mcp__little-versions__lvx_*`) — never by hand.

## Project-specific notes

- `.lvx/config.json` branch names: production = `master`, integration = `dev`.
- Current version: see `VERSION` at the project root.
- Version hook: `tools/on_version_bump.py` (registered via `lvx config add-hook`).
  It propagates a version bump into `pyproject.toml`'s `[project]` version,
  `MODULE.bazel`'s `module(version=...)`, `src/little_meals/BUILD.bazel`'s
  `py_wheel(version=...)`, and `src/little_meals/__init__.py`'s `__version__` —
  raising loudly if any of those patterns can't be found, rather than silently
  leaving a file out of sync.
