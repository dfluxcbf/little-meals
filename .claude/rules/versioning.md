---
paths:
  - "VERSION"
  - "pyproject.toml"
  - "MODULE.bazel"
  - "src/little_meals/__init__.py"
  - "src/little_meals/BUILD.bazel"
  - "tools/on_version_bump.py"
  - ".lvx/**"
  - "docs/version_policy.md"
---
# Versions

- little-workshop writes `VERSION` (the pre-commit hook on `feature/` and `improvement/` branches, the finish and
  release commands elsewhere), and `tools/on_version_bump.py` copies it into `pyproject.toml`, `MODULE.bazel`,
  `src/little_meals/BUILD.bazel` and `src/little_meals/__init__.py`: never edit the version in any of them by hand.
- `.lvx/config.json` is the branch model little-workshop's Version pillar reads: production `master`, integration
  `dev`, and the version hook above.
- `docs/version_policy.md` still describes `lvx`, which little-workshop replaced (`workshop_version_*`). Follow
  the live system, and correct the doc where you touch it.
