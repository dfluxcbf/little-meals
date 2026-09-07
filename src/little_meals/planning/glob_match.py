from __future__ import annotations

import fnmatch
from typing import Optional


def matches_glob(text: str, pattern: Optional[str]) -> bool:
    """Case-insensitive glob match (`*`/`?`/`[...]`) - a blank/None pattern
    imposes no constraint and matches everything."""
    if pattern is None or not pattern.strip():
        return True
    return fnmatch.fnmatch(text.lower(), pattern.strip().lower())
