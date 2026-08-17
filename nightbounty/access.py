"""Small, testable helpers for the hackathon owner-console access gate."""

from __future__ import annotations

import hmac

OWNER_ACCESS_CODE_MIN_LENGTH = 12
_EXAMPLE_CODES = frozenset(
    {
        "replace-with-a-long-random-owner-code",
        "replace-with-long-random-code-before-running",
    }
)


def normalize_owner_access_code(value: object | None) -> str | None:
    """Return a configured access code, rejecting empty/example/weak values."""
    code = str(value or "").strip()
    if len(code) < OWNER_ACCESS_CODE_MIN_LENGTH or code in _EXAMPLE_CODES:
        return None
    return code


def matches_owner_access_code(submitted: str, configured: str | None) -> bool:
    """Compare access codes without leaking matching-prefix timing information."""
    if not submitted or not configured:
        return False
    return hmac.compare_digest(submitted.encode("utf-8"), configured.encode("utf-8"))
