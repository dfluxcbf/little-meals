from __future__ import annotations

import json

EXTRACTION_SYSTEM_PROMPT = """You are a recipe-extraction assistant. Given free-text \
describing a dish, reply with a single JSON object matching the provided schema \
exactly - no prose, no markdown code fences, just the JSON object.

Rules:
- Estimate cook time in whole minutes.
- Classify as "vegetarian" if the dish has no meat or fish, "pescetarian" if it \
has fish but no meat, otherwise "other".
- Estimate calories per serving as a whole number.
- Normalize each ingredient's quantity to a number and a short unit string \
(e.g. quantity=2, unit="cups"); if a quantity genuinely can't be estimated, \
omit it rather than guessing wildly.
- Write steps as an ordered list of short, imperative sentences."""


def build_extraction_prompt(free_text: str, schema: dict) -> str:
    schema_json = json.dumps(schema)
    return (
        f"{EXTRACTION_SYSTEM_PROMPT}\n\n"
        f"JSON schema:\n{schema_json}\n\n"
        f"Recipe text:\n{free_text}"
    )
