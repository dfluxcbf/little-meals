from __future__ import annotations

from typing import Any, Optional


class ApiError(Exception):
    """Structured API error - carries an HTTP status, a machine-readable code,
    a human message, and optional details (e.g. pydantic validation errors)."""

    def __init__(self, status_code: int, code: str, message: str, details: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details if details is not None else {}
