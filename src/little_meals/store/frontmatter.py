from __future__ import annotations

import re
import unicodedata

import yaml

_FENCE = "---"
_FRONTMATTER_RE = re.compile(r"\A---\n(.*?\n)---\n?(.*)\Z", re.DOTALL)


class FrontmatterError(ValueError):
    """Raised when a Markdown+YAML-frontmatter document is malformed."""


def split(text: str) -> tuple[str, str]:
    """Split a Markdown document into (yaml_str, body).

    Tolerates a document with no frontmatter at all (returns ("", text)).
    Raises FrontmatterError if a frontmatter block is opened but never closed.
    """
    if not text.startswith(f"{_FENCE}\n"):
        return "", text

    match = _FRONTMATTER_RE.match(text)
    if match is None:
        raise FrontmatterError("Unterminated '---' frontmatter block")

    yaml_str, body = match.groups()
    return yaml_str, body


def render(mapping: dict, body: str) -> str:
    """Render a mapping + Markdown body back into a frontmatter document."""
    yaml_str = yaml.safe_dump(mapping, sort_keys=False, allow_unicode=True)
    return f"{_FENCE}\n{yaml_str}{_FENCE}\n{body}"


def slugify(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
    return slug or "recipe"
