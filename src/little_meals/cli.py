from __future__ import annotations

import argparse
import getpass
import sys
from dataclasses import replace
from typing import Optional, Sequence

from little_meals import __version__
from little_meals.config import Settings


def _cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    from little_meals.api.app import create_app

    settings = Settings.from_env()
    if args.data_dir:
        settings = replace(settings, data_dir=args.data_dir)

    if settings.spoonacular_key_file:
        from little_meals.vault import VaultError, decrypt_key_file

        passphrase = getpass.getpass("Spoonacular vault passphrase: ")
        try:
            api_key = decrypt_key_file(settings.spoonacular_key_file, passphrase)
        except VaultError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        finally:
            del passphrase
        settings = replace(settings, spoonacular_api_key=api_key)
        del api_key

    app = create_app(settings, enable_scheduler=True)
    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload, log_level="info")
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
