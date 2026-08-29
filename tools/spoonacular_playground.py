"""spoonacular_playground.py - fire ad hoc requests at the Spoonacular API
and inspect the raw response, to explore what a given endpoint/parameter
combination actually returns before committing to a search design.

Not wired into Bazel (`bazel run //:...`) on purpose - this is a throwaway
exploration tool, not a build artifact. Run it directly from the repo's venv,
pasting a full request line exactly as Spoonacular's own docs show it
(quote it - the URL contains `&`, which the shell would otherwise treat as
"run in background"):

    python tools/spoonacular_playground.py \\
        "GET https://api.spoonacular.com/recipes/complexSearch?query=pasta&cuisine=italian&sort=random&number=5"

    python tools/spoonacular_playground.py \\
        "https://api.spoonacular.com/recipes/716429/information"

    python tools/spoonacular_playground.py \\
        "GET https://api.spoonacular.com/food/ingredients/autocomplete?query=beetroot"

Do not include `&apiKey=...` - leave it off entirely. The tool always adds
the real key itself (see below), so a request line copy-pasted straight out
of Spoonacular's docs (which shows `apiKey=YOUR-API-KEY` as a placeholder)
works unedited: any `apiKey` value that IS present in the pasted URL is
ignored and overwritten. The leading method (GET/POST/PUT/DELETE) is
optional and defaults to GET. For POST/PUT, pass a JSON body with --body.

Endpoint/parameter reference: docs/spoonacular_api.md

The real key is never typed on the command line. This tool resolves it the
same way `lmeals serve`/`import-spoonacular` do: LITTLE_MEALS_SPOONACULAR_API_KEY,
or LITTLE_MEALS_SPOONACULAR_KEY_FILE - an encrypted vault file, in which case
the tool prompts for the vault's decryption passphrase and decrypts the key
in memory for just this one request.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any
from urllib.parse import parse_qsl, urlsplit, urlunsplit

import httpx

from little_meals.cli import _load_spoonacular_api_key
from little_meals.config import Settings

_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH"}


def _parse_request_line(request_line: str) -> tuple[str, str, dict[str, str]]:
    """Splits a pasted "METHOD URL" (or bare URL) into (method, url-without-query, params)."""
    parts = request_line.strip().split(None, 1)
    if len(parts) == 2 and parts[0].upper() in _METHODS:
        method, raw_url = parts[0].upper(), parts[1]
    else:
        method, raw_url = "GET", request_line.strip()

    split = urlsplit(raw_url)
    params = dict(parse_qsl(split.query, keep_blank_values=True))
    base_url = urlunsplit((split.scheme or "https", split.netloc, split.path, "", ""))
    return method, base_url, params


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "request",
        help='a request line, e.g. \'GET https://api.spoonacular.com/recipes/complexSearch?query=pasta&number=5\'',
    )
    parser.add_argument(
        "--body", default=None, metavar="JSON", help="raw JSON request body, for POST/PUT endpoints"
    )
    args = parser.parse_args(argv)

    method, url, params = _parse_request_line(args.request)

    body: Any = None
    if args.body is not None:
        try:
            body = json.loads(args.body)
        except json.JSONDecodeError as exc:
            print(f"error: --body is not valid JSON: {exc}", file=sys.stderr)
            return 2

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

    params["apiKey"] = settings.spoonacular_api_key

    redacted_params = {**params, "apiKey": "***"}
    print(f"--> {method} {url}")
    print(f"    params: {redacted_params}")
    if body is not None:
        print(f"    body: {json.dumps(body)}")
    print()

    started = time.monotonic()
    with httpx.Client(timeout=settings.spoonacular_timeout_s) as client:
        try:
            response = client.request(method, url, params=params, json=body)
        except httpx.HTTPError as exc:
            print(f"error: request failed: {exc}", file=sys.stderr)
            return 1
    elapsed_ms = (time.monotonic() - started) * 1000

    print(f"<-- {response.status_code} {response.reason_phrase} ({elapsed_ms:.0f}ms)")
    quota_used = response.headers.get("x-api-quota-used")
    quota_left = response.headers.get("x-api-quota-left")
    if quota_used or quota_left:
        print(f"    quota used this request: {quota_used}, remaining today: {quota_left}")
    print()

    try:
        payload = response.json()
    except ValueError:
        print(response.text)
        return 0 if response.is_success else 1

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if response.is_success else 1


if __name__ == "__main__":
    raise SystemExit(main())
