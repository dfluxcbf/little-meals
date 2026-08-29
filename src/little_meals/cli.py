from __future__ import annotations

import argparse
import getpass
import sys
from dataclasses import replace
from pathlib import Path
from typing import Optional, Sequence

from little_meals import __version__
from little_meals.config import Settings


def _load_spoonacular_api_key(settings: Settings) -> tuple[Settings, Optional[int]]:
    """If a vault key file is configured, prompts for its passphrase and
    decrypts it into `settings.spoonacular_api_key`. Returns the (possibly
    updated) settings and an exit code to return immediately (decryption
    failed), or None to continue - shared by `serve` and
    `import-spoonacular`, the two commands that talk to Spoonacular.
    """
    if not settings.spoonacular_key_file:
        return settings, None

    from little_meals.vault import VaultError, decrypt_key_file

    passphrase = getpass.getpass("Spoonacular vault passphrase: ")
    try:
        api_key = decrypt_key_file(settings.spoonacular_key_file, passphrase)
    except VaultError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return settings, 1
    finally:
        del passphrase
    settings = replace(settings, spoonacular_api_key=api_key)
    del api_key
    return settings, None


def _cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    from little_meals.api.app import create_app

    settings = Settings.from_env()
    if args.data_dir:
        settings = replace(settings, data_dir=Path(args.data_dir))

    settings, error_code = _load_spoonacular_api_key(settings)
    if error_code is not None:
        return error_code

    app = create_app(settings, enable_scheduler=True)
    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload, log_level="info")
    return 0


def _cmd_import_spoonacular(args: argparse.Namespace) -> int:
    from little_meals.llm.extraction import RecipeExtractionService
    from little_meals.llm.ollama_client import OllamaClient
    from little_meals.planning.spoonacular_import import import_recipes
    from little_meals.planning.suggestion import SpoonacularSearchProvider
    from little_meals.store.household_store import HouseholdPreferencesStore
    from little_meals.store.recipe_store import RecipeStore

    settings = Settings.from_env()
    if args.data_dir:
        settings = replace(settings, data_dir=Path(args.data_dir))

    settings, error_code = _load_spoonacular_api_key(settings)
    if error_code is not None:
        return error_code

    if not settings.spoonacular_api_key:
        print(
            "error: no Spoonacular API key configured "
            "(set LITTLE_MEALS_SPOONACULAR_API_KEY or LITTLE_MEALS_SPOONACULAR_KEY_FILE)",
            file=sys.stderr,
        )
        return 1

    household_store = HouseholdPreferencesStore(settings.household_db_path)
    preferences = household_store.get()
    query = preferences.food_filter
    if query is None:
        print(
            "error: no food preferences saved yet - describe your household's tastes on the "
            "Settings page and save first",
            file=sys.stderr,
        )
        return 1
    count = args.count if args.count is not None else preferences.recipes_per_week

    store = RecipeStore(settings.recipes_dir)

    if args.reset:
        existing_count = store.count()
        if existing_count == 0:
            print("No recipes to delete.")
        else:
            if not args.yes:
                answer = input(
                    f"This will permanently delete all {existing_count} recipe(s) in "
                    f"{settings.recipes_dir}. Continue? [y/N] "
                )
                if answer.strip().lower() not in ("y", "yes"):
                    print("Aborted - no recipes were deleted.", file=sys.stderr)
                    return 1
            deleted = store.delete_all()
            print(f"Deleted {deleted} recipe(s) from {settings.recipes_dir}.")

    provider = SpoonacularSearchProvider(
        settings.spoonacular_api_key,
        base_url=settings.spoonacular_base_url,
        timeout_s=settings.spoonacular_timeout_s,
    )
    client = OllamaClient(settings.ollama_base_url, settings.ollama_model, settings.ollama_timeout_s)
    extractor = RecipeExtractionService(client)

    try:
        result = import_recipes(provider, extractor, store, query=query, count=count)
    finally:
        provider.close()
        client.close()

    summary = f"Imported {len(result.imported)} of {result.requested} requested recipe(s) from Spoonacular into {settings.recipes_dir}"
    if result.skipped:
        summary += f" ({result.skipped} skipped - failed extraction)"
    print(summary + ".")
    if result.found < result.requested:
        print(
            f"Note: Spoonacular only had {result.found} matching recipe(s) for your saved search "
            f"preferences, not {result.requested} - this isn't an error, your filter (cuisine/diet/"
            "nutrition ranges/etc. on the recipe search preferences page) is just narrow enough that "
            "fewer recipes qualify. Widen it there if you want more results per import.",
            file=sys.stderr,
        )
    return 0 if result.requested == 0 or result.imported else 1


def _cmd_settings(args: argparse.Namespace) -> int:
    from little_meals.store.household_store import HouseholdPreferencesStore
    from little_meals.store.plan_store import MealPlanStore
    from little_meals.store.shopping_list_store import ShoppingListStore

    if not args.reset:
        print("error: no action given (did you mean --reset?)", file=sys.stderr)
        return 1

    settings = Settings.from_env()
    if args.data_dir:
        settings = replace(settings, data_dir=Path(args.data_dir))

    plan_store = MealPlanStore(settings.plan_db_path)
    shopping_list_store = ShoppingListStore(settings.shopping_list_db_path)

    plan_count = plan_store.count()
    shopping_list_count = shopping_list_store.count()

    if not args.yes:
        answer = input(
            "This will reset your general settings (recipes per week, recommendation "
            "day/time, AI suggestions per plan, default servings) to their defaults, and "
            f"permanently delete all {plan_count} meal plan(s) and {shopping_list_count} "
            "shopping list(s). Your food preferences/query and saved recipes are kept. "
            "Continue? [y/N] "
        )
        if answer.strip().lower() not in ("y", "yes"):
            print("Aborted - nothing was reset.", file=sys.stderr)
            return 1

    household_store = HouseholdPreferencesStore(settings.household_db_path)
    household_store.reset_general_settings()
    deleted_plans = plan_store.delete_all()
    deleted_shopping_lists = shopping_list_store.delete_all()

    print(
        "Settings reset to defaults (food preferences and recipes kept). "
        f"Deleted {deleted_plans} meal plan(s) and {deleted_shopping_lists} shopping list(s)."
    )
    return 0


def _cmd_preflight(args: argparse.Namespace) -> int:
    from little_meals.preflight import format_report
    from little_meals.preflight import check as run_check

    result = run_check()
    print(format_report(result))
    return 0 if result.ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lmeals")
    parser.add_argument("--version", action="version", version=f"little-meals {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    serve_parser = subparsers.add_parser("serve", help="run the web app")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8765)
    serve_parser.add_argument("--reload", action="store_true")
    serve_parser.add_argument("--data-dir", default=None)
    serve_parser.set_defaults(func=_cmd_serve)

    preflight_parser = subparsers.add_parser("preflight", help="check system dependencies")
    preflight_parser.set_defaults(func=_cmd_preflight)

    settings_parser = subparsers.add_parser("settings", help="manage household settings")
    settings_parser.add_argument(
        "--reset",
        action="store_true",
        help=(
            "reset general settings (recipes per week, recommendation day/time, AI "
            "suggestions per plan, default servings) to defaults, and delete all meal "
            "plans and shopping lists - keeps food preferences/query and saved recipes "
            "(asks to confirm)"
        ),
    )
    settings_parser.add_argument("--yes", "-y", action="store_true", help="skip the --reset confirmation prompt")
    settings_parser.add_argument("--data-dir", default=None)
    settings_parser.set_defaults(func=_cmd_settings)

    import_parser = subparsers.add_parser(
        "import-spoonacular", help="bulk-import recipes from Spoonacular into the library"
    )
    import_parser.add_argument(
        "--count", "-n", type=int, default=None, help="how many recipes to import (default: recipes_per_week)"
    )
    import_parser.add_argument(
        "--reset", action="store_true", help="delete all existing recipes before importing (asks to confirm)"
    )
    import_parser.add_argument("--yes", "-y", action="store_true", help="skip the --reset confirmation prompt")
    import_parser.add_argument("--data-dir", default=None)
    import_parser.set_defaults(func=_cmd_import_spoonacular)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
