"""Generates docs/spoonacular_api.md from the Spoonacular OpenAPI 3 spec.

Source spec: https://github.com/ddsky/spoonacular-api-clients (spoonacular-openapi-3.json),
a community-maintained repo referenced by Spoonacular's own docs site as the
source for its generated API clients. Not Spoonacular's own machine-readable
artifact, so a few field-level quirks (noted inline) are carried over as-is
rather than silently "corrected".
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

SPEC_PATH = Path(__file__).parent / "spoonacular-openapi-3.json"
OUT_PATH = Path(__file__).parent / "spoonacular_api.md"

MAX_DEPTH = 3


def resolve_param(spec: dict, param: dict) -> dict:
    if "$ref" in param:
        ref = param["$ref"]
        assert ref.startswith("#/components/parameters/")
        name = ref.rsplit("/", 1)[-1]
        return spec["components"]["parameters"][name]
    return param


def type_of(schema: dict) -> str:
    if not schema:
        return "any"
    if "$ref" in schema:
        return schema["$ref"].rsplit("/", 1)[-1]
    t = schema.get("type", "any")
    if t == "array":
        return f"array<{type_of(schema.get('items', {}))}>"
    return t


def render_schema(schema: dict, depth: int = 0, spec: dict | None = None) -> str:
    if not schema:
        return "`any`"
    if "$ref" in schema and spec is not None:
        name = schema["$ref"].rsplit("/", 1)[-1]
        target = spec["components"]["schemas"].get(name, {})
        return f"[`{name}`](#schema-{name.lower()})"
    t = schema.get("type", "object" if "properties" in schema else "any")
    if t == "object" and "properties" in schema:
        if depth >= MAX_DEPTH:
            return "`object{...}`"
        required = set(schema.get("required", []))
        lines = []
        for prop_name, prop_schema in schema["properties"].items():
            mark = "*" if prop_name in required else ""
            lines.append(f"{'  ' * (depth + 1)}- `{prop_name}`{mark}: {render_schema(prop_schema, depth + 1, spec)}")
        return "`object` {\n" + "\n".join(lines) + "\n" + "  " * depth + "}"
    if t == "array":
        items = schema.get("items", {})
        return f"`array<` {render_schema(items, depth, spec)} `>`"
    fmt = f" ({schema['format']})" if schema.get("format") else ""
    return f"`{t}`{fmt}"


def param_row(p: dict) -> str:
    name = p.get("name", "?")
    loc = p.get("in", "?")
    required = "yes" if p.get("required") else "no"
    schema = p.get("schema", {})
    typ = type_of(schema)
    example = schema.get("example", "")
    desc = (p.get("description") or "").replace("\n", " ").replace("|", "\\|")
    example_str = f" (e.g. `{example}`)" if example != "" else ""
    return f"| `{name}` | {loc} | {typ} | {required} | {desc}{example_str} |"


def main() -> None:
    spec = json.loads(SPEC_PATH.read_text())
    paths: dict = spec["paths"]
    tags_meta = {t["name"]: t.get("description") for t in spec.get("tags", [])}

    by_tag: dict[str, list[tuple[str, str, dict]]] = defaultdict(list)
    for path, methods in paths.items():
        for method, op in methods.items():
            if method not in ("get", "post", "put", "delete", "patch"):
                continue
            tags = op.get("tags") or ["untagged"]
            for tag in tags:
                by_tag[tag].append((path, method, op))

    lines: list[str] = []
    info = spec.get("info", {})
    lines.append("# Spoonacular API Reference")
    lines.append("")
    lines.append(
        "Locally mirrored reference for the Spoonacular Food API, generated from the "
        "community-maintained OpenAPI 3 spec at "
        "[ddsky/spoonacular-api-clients](https://github.com/ddsky/spoonacular-api-clients) "
        f"(spec version `{info.get('version', '?')}`), cross-checked against "
        "[spoonacular.com/food-api/docs](https://spoonacular.com/food-api/docs). "
        "Regenerate by re-running `gen_spoonacular_docs.py` against a freshly-downloaded "
        "copy of `spoonacular-openapi-3.json` if Spoonacular's API changes."
    )
    lines.append("")
    lines.append("## Caveats about this reference")
    lines.append("")
    lines.append(
        "- **No enum data.** Spoonacular does not publish machine-readable enum lists for "
        "`cuisine`, `excludeCuisine`, `diet`, `intolerances`, `type`, or `sort` - not even in "
        "this OpenAPI spec. Those parameters are typed as plain strings whose valid values are "
        "documented only as prose on the docs site. See the hand-copied lists in "
        "[\"Known enum values\"](#known-enum-values) below; treat them as best-effort, not authoritative."
    )
    lines.append(
        "- **`required` is occasionally wrong.** A handful of shared parameters (e.g. `query` on "
        "`/recipes/complexSearch`) are marked `required: true` in this spec via a reused "
        "`$ref` component even though Spoonacular's own docs describe them as optional there. "
        "This is a spec-authoring quirk in the community repo, not a live API constraint - verify "
        "against the prose docs before trusting `required` at face value."
    )
    lines.append(
        "- **Response schemas are best-effort.** Only 8 named schemas exist in "
        "`components/schemas`; most endpoint responses are defined inline and were unrolled here "
        f"up to {MAX_DEPTH} levels deep (deeper object/array bodies are shown as `object{{...}}`)."
    )
    lines.append(
        "- **Auth.** The spec declares an `apiKeyScheme` security scheme using the `x-api-key` "
        "header, but Spoonacular's docs and most examples pass the key as an `apiKey` query "
        "parameter instead - both work in practice."
    )
    lines.append("")

    lines.append("## Table of contents")
    lines.append("")
    for tag in sorted(by_tag):
        lines.append(f"- [{tag}](#{tag.replace(' ', '-')})")
        for path, method, op in sorted(by_tag[tag], key=lambda x: x[0]):
            anchor_text = f"{method.upper()} {path}"
            anchor = anchor_text.lower().replace(" ", "-").replace("/", "").replace("{", "").replace("}", "").replace(".", "")
            summary = op.get("summary", "")
            lines.append(f"  - [{anchor_text}](#{anchor}) - {summary}")
    lines.append("")

    for tag in sorted(by_tag):
        lines.append(f"## {tag}")
        if tags_meta.get(tag):
            lines.append("")
            lines.append(tags_meta[tag])
        lines.append("")
        for path, method, op in sorted(by_tag[tag], key=lambda x: x[0]):
            lines.append(f"### {method.upper()} {path}")
            lines.append("")
            if op.get("summary"):
                lines.append(f"**{op['summary']}**")
                lines.append("")
            if op.get("description") and op.get("description") != op.get("summary"):
                lines.append(op["description"])
                lines.append("")
            if op.get("deprecated"):
                lines.append("> **Deprecated.**")
                lines.append("")

            params = [resolve_param(spec, p) for p in op.get("parameters", [])]
            if params:
                lines.append("| Parameter | In | Type | Required | Description |")
                lines.append("|---|---|---|---|---|")
                for p in params:
                    lines.append(param_row(p))
                lines.append("")
            else:
                lines.append("_No parameters._")
                lines.append("")

            request_body = op.get("requestBody")
            if request_body:
                content = request_body.get("content", {})
                for ctype, cbody in content.items():
                    lines.append(f"**Request body** (`{ctype}`):")
                    lines.append("")
                    lines.append(render_schema(cbody.get("schema", {}), 0, spec))
                    lines.append("")

            responses = op.get("responses", {})
            ok = responses.get("200") or responses.get("201")
            if ok:
                content = ok.get("content", {})
                if content:
                    for ctype, cbody in content.items():
                        lines.append(f"**Response 200** (`{ctype}`):")
                        lines.append("")
                        lines.append(render_schema(cbody.get("schema", {}), 0, spec))
                        lines.append("")
                else:
                    lines.append(f"**Response 200**: {ok.get('description', '')}")
                    lines.append("")
            other_codes = sorted(c for c in responses if c not in ("200", "201"))
            if other_codes:
                lines.append("Other responses: " + ", ".join(f"`{c}`" for c in other_codes))
                lines.append("")

            lines.append("---")
            lines.append("")

    lines.append("## Named schemas")
    lines.append("")
    for name, schema in spec.get("components", {}).get("schemas", {}).items():
        lines.append(f"### Schema: {name}")
        lines.append("")
        lines.append(render_schema(schema, 0, spec))
        lines.append("")

    lines.append("## Known enum values")
    lines.append("")
    lines.append(
        "Hand-copied from [spoonacular.com/food-api/docs](https://spoonacular.com/food-api/docs) "
        "prose (not present in the OpenAPI spec - see caveats above). Verify against the live "
        "docs site before relying on these for validation, since Spoonacular can add values "
        "without updating the spec."
    )
    lines.append("")
    lines.append("**Cuisines** (`cuisine` / `excludeCuisine`): African, American, British, Cajun, "
                  "Caribbean, Chinese, Eastern European, European, French, German, Greek, Indian, "
                  "Irish, Italian, Japanese, Jewish, Korean, Latin American, Mediterranean, Mexican, "
                  "Middle Eastern, Nordic, Southern, Spanish, Thai, Vietnamese.")
    lines.append("")
    lines.append("**Diets** (`diet`): Gluten Free, Ketogenic, Vegetarian, Lacto-Vegetarian, "
                  "Ovo-Vegetarian, Vegan, Pescetarian, Paleo, Primal, Low FODMAP, Whole30.")
    lines.append("")
    lines.append("**Intolerances** (`intolerances`): Dairy, Egg, Gluten, Grain, Peanut, Seafood, "
                  "Sesame, Shellfish, Soy, Sulfite, Tree Nut, Wheat.")
    lines.append("")
    lines.append("**Meal types** (`type`): main course, side dish, dessert, appetizer, salad, "
                  "bread, breakfast, soup, beverage, sauce, marinade, fingerfood, snack, drink.")
    lines.append("")
    lines.append("**Sort** (`sort`): meta-score (default relevance), popularity, healthiness, "
                  "price, time, random, max-used-ingredients, min-missing-ingredients, plus most "
                  "nutrient names (e.g. calories, protein, carbs, fat). Pair with `sortDirection` "
                  "(`asc`/`desc`).")
    lines.append("")

    OUT_PATH.write_text("\n".join(lines))
    print(f"wrote {OUT_PATH} ({len(lines)} lines, {OUT_PATH.stat().st_size} bytes)")
    print(f"{len(paths)} paths, {sum(len(v) for v in by_tag.values())} tagged operations across {len(by_tag)} tags")


if __name__ == "__main__":
    main()
