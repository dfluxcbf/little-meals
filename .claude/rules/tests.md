---
paths:
  - "tests/**"
  - "docs/requirements_policy.md"
---
# Tests and requirements

- Every test carries the requirement it covers: `@pytest.mark.requirement("REQ-nnnnnnnnn")`, or
  `pytestmark = pytest.mark.requirement(...)` for a whole module (`tests/conftest.py` registers the marker). The
  ids come from little-workshop's Requirements pillar (`workshop_requirements_list`, `_create`): never invent one.
  The per-milestone id ranges are in `docs/requirements_policy.md`.
- `docs/requirements_policy.md` still describes `lreq`, `mcp__little-requirements__*` and a `bundle-littles`
  database, which little-workshop replaced: requirements live in its Requirements pillar, and a
  Definition-of-Done run is recorded with `workshop_requirements_run_tests`. Follow the live system, and correct
  the doc where you touch it.
- Reuse the store fixtures in `tests/conftest.py` (each over a `tmp_path` data dir) before adding new ones.
