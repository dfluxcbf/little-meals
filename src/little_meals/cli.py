from __future__ import annotations

import argparse
import getpass
import sys
from dataclasses import replace
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
        settings = replace(settings, data_dir=args.data_dir)

    settings, error_code = _load_spoonacular_api_key(settings)
    if error_code is not None:
        return error_code

    app = create_app(settings, enable_scheduler=True)
    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload, log_level="info")
    return 0


def _cmd_import_spoonacular(args: argparse.Namespace) -> int:
    from little_meals.llm.extraction import RecipeExtractionService
    from little_meals.llm.ollama_client import OllamaClient
    from little_meals.planning.spoonacular_import import build_search_query, import_recipes
    from little_meals.planning.suggestion import SpoonacularSearchProvider
    from little_meals.store.household_store import HouseholdPreferencesStore
    from little_meals.store.recipe_store import RecipeStore

    settings = Settings.from_env()
    if args.data_dir:
        settings = replace(settings, data_dir=args.data_dir)

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

    household_store = HouseholdPreferencesStore(settings.household_db_path)
    preferences = household_store.get()
    count = args.count if args.count is not None else preferences.recipes_per_week
    query = build_search_query(preferences.food_preferences)

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
        summary += f" ({result.skipped} skipped)"
    print(summary + ".")
    return 0 if result.requested == 0 or result.imported else 1


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
