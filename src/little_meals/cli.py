from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path
from typing import Optional, Sequence

from little_meals import __version__
from little_meals.config import Settings


def _cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    from little_meals.api.app import create_app

    settings = Settings.from_env()
    if args.data_dir:
        settings = replace(settings, data_dir=Path(args.data_dir))

    app = create_app(settings, enable_scheduler=True)
    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload, log_level="info")
    return 0


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
            "day/time, default servings) to their defaults, and permanently delete all "
            f"{plan_count} meal plan(s) and {shopping_list_count} shopping list(s). Your "
            "saved recipes are kept. Continue? [y/N] "
        )
        if answer.strip().lower() not in ("y", "yes"):
            print("Aborted - nothing was reset.", file=sys.stderr)
            return 1

    household_store = HouseholdPreferencesStore(settings.household_db_path)
    household_store.reset_general_settings()
    deleted_plans = plan_store.delete_all()
    deleted_shopping_lists = shopping_list_store.delete_all()

    print(
        "Settings reset to defaults (recipes kept). "
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
            "reset general settings (recipes per week, recommendation day/time, default "
            "servings) to defaults, and delete all meal plans and shopping lists - keeps "
            "saved recipes (asks to confirm)"
        ),
    )
    settings_parser.add_argument("--yes", "-y", action="store_true", help="skip the --reset confirmation prompt")
    settings_parser.add_argument("--data-dir", default=None)
    settings_parser.set_defaults(func=_cmd_settings)

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
