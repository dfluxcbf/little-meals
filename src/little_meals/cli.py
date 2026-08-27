from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

from little_meals import __version__
from little_meals.config import Settings


def _cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    from little_meals.api.app import create_app

    settings = Settings.from_env()
    if args.data_dir:
        settings = Settings(
            data_dir=args.data_dir,
            ollama_base_url=settings.ollama_base_url,
            ollama_model=settings.ollama_model,
            ollama_timeout_s=settings.ollama_timeout_s,
        )

    app = create_app(settings)
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
