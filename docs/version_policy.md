# Version policy

This project follows the super-repo's
[version policy](../../docs/policies/version_policy.md). Branching and version
bumps are managed exclusively through **little-versions** (`lvx` /
`mcp__little-versions__lvx_*`) — never by hand.

## Project-specific notes

- `.lvx/config.json` branch names: production = `master`, integration = `dev`.
- Current version: see `VERSION` at the project root (`0.1.0` — pre-implementation
  scaffold, no release cut yet).
- No version hooks are registered yet (`version_hooks: []`), since no
  version-bearing package metadata files (`BUILD.bazel`, `pyproject.toml`, etc.)
  exist yet. The first one to be added, once Milestone 1 introduces packaging, will
  need a corresponding hook script under `tools/`.
