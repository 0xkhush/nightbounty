"""Pseudonymous researcher account helpers for the NightBounty MVP."""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets

ALIAS_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,31}$")
MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_BYTES = 1024
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 32
SCRYPT_MAXMEM = 64 * 1024 * 1024


def normalize_alias(alias: str) -> str:
    """Validate and canonicalize a public researcher pseudonym."""
    normalized = alias.strip().lower()
    if not ALIAS_PATTERN.fullmatch(normalized):
        raise ValueError(
            "Use a 3–32 character alias beginning with a letter; use lowercase letters, numbers, and underscores only."
        )
    return normalized


def _password_bytes(password: str) -> bytes:
    encoded = password.encode("utf-8")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Use a password with at least {MIN_PASSWORD_LENGTH} characters.")
    if len(encoded) > MAX_PASSWORD_BYTES:
        raise ValueError("Password is too long.")
    return encoded


def _derive(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(
        _password_bytes(password),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_DKLEN,
        maxmem=SCRYPT_MAXMEM,
    )


def hash_password(password: str) -> str:
    """Return a versioned scrypt password hash with a fresh salt."""
    salt = secrets.token_bytes(16)
    digest = _derive(password, salt)
    return "$".join(
        (
            "scrypt-v1",
            str(SCRYPT_N),
            str(SCRYPT_R),
            str(SCRYPT_P),
            base64.urlsafe_b64encode(salt).decode("ascii"),
            base64.urlsafe_b64encode(digest).decode("ascii"),
        )
    )


def verify_password(password: str, encoded_hash: str) -> bool:
    """Verify a password against the only supported stored hash format."""
    try:
        version, n, r, p, encoded_salt, encoded_digest = encoded_hash.split("$")
        if (version, int(n), int(r), int(p)) != ("scrypt-v1", SCRYPT_N, SCRYPT_R, SCRYPT_P):
            return False
        salt = base64.b64decode(encoded_salt.encode("ascii"), altchars=b"-_", validate=True)
        expected = base64.b64decode(encoded_digest.encode("ascii"), altchars=b"-_", validate=True)
        if len(salt) != 16 or len(expected) != SCRYPT_DKLEN:
            return False
        actual = _derive(password, salt)
        return hmac.compare_digest(actual, expected)
    except (TypeError, ValueError):
        return False
