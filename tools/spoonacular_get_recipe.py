"""spoonacular_get_recipe.py - look up one dish by name and print Spoonacular's
full recipe data for it (ingredients, instructions, nutrition, etc.), not just
a search-result summary.

Two requests under the hood: `/recipes/complexSearch?query=...&number=1` to
find the best-matching recipe's id, then `/recipes/{id}/information` (with
`includeNutrition=true`) for the full record.

Usage:
    python tools/spoonacular_get_recipe.py "chicken tikka masala"

Reads the API key the same way `lmeals serve` does: LITTLE_MEALS_SPOONACULAR_API_KEY,
or LITTLE_MEALS_SPOONACULAR_KEY_FILE (prompts for the vault passphrase).

Not wired into Bazel - a throwaway exploration tool, same as
spoonacular_playground.py.
"""

from __future__ import annotations

import argparse
import json
import sys

import httpx

from little_meals.cli import _load_spoonacular_api_key
from little_meals.config import Settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dish", help='the dish name to search for, e.g. "chicken tikka masala"')
    args = parser.parse_args(argv)

    settings = Settings.from_env()
    settings, error_code = _load_spoonacular_api_key(settings)
    if error_code is not None:
        return error_code
    if not settings.spoonacular_api_key:
        print(
            "error: no Spoonacular API key configured - set LITTLE_MEALS_SPOONACULAR_API_KEY "
            "or LITTLE_MEALS_SPOONACULAR_KEY_FILE",
            file=sys.stderr,
        )
        return 1

    base_url = settings.spoonacular_base_url
    api_key = settings.spoonacular_api_key

    with httpx.Client(timeout=settings.spoonacular_timeout_s) as client:
        print(f"--> searching for {args.dish!r}...")
        search_response = client.get(
            f"{base_url}/recipes/complexSearch",
            params={"query": args.dish, "number": 1, "apiKey": api_key},
        )
        try:
            search_response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            print(f"error: search failed: {exc}", file=sys.stderr)
            print(search_response.text, file=sys.stderr)
            return 1

        results = search_response.json().get("results", [])
        if not results:
            print(f"no results found for {args.dish!r}")
            return 1

        recipe_id = results[0]["id"]
        print(f"--> found id {recipe_id} ({results[0].get('title')!r}), fetching full recipe...\n")

        info_response = client.get(
            f"{base_url}/recipes/{recipe_id}/information",
            params={"includeNutrition": "true", "apiKey": api_key},
        )
        try:
            info_response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            print(f"error: fetching recipe information failed: {exc}", file=sys.stderr)
            print(info_response.text, file=sys.stderr)
            return 1

    print(json.dumps(info_response.json(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
