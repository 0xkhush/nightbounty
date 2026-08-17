"""Client-side style encryption and commitment helpers for NightBounty reports."""

from __future__ import annotations

import base64
import hashlib
import json
import os
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

KDF_ITERATIONS = 480_000


def canonical_payload(payload: dict[str, Any]) -> bytes:
    """Create a stable representation so commitments are reproducible."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    if len(passphrase.strip()) < 8:
        raise ValueError("Use a collaboration key with at least 8 characters.")

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=KDF_ITERATIONS,
    )
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))


def encrypt_report(payload: dict[str, Any], collaboration_key: str) -> dict[str, str]:
    """Encrypt report content and generate a salted commitment.

    Only ciphertext, a random salt, and non-sensitive digests are persisted.
    In production, the collaboration key is replaced by the project's public
    encryption key; this hackathon MVP keeps the exchange explicit and local.
    """
    payload_bytes = canonical_payload(payload)
    encryption_salt = os.urandom(16)
    commitment_salt = os.urandom(32)
    encrypted = Fernet(_derive_key(collaboration_key, encryption_salt)).encrypt(payload_bytes)

    return {
        "ciphertext": encrypted.decode("utf-8"),
        "encryption_salt": base64.urlsafe_b64encode(encryption_salt).decode("ascii"),
        "commitment": hashlib.sha256(payload_bytes + commitment_salt).hexdigest(),
        "payload_digest": hashlib.sha256(payload_bytes).hexdigest(),
    }


def decrypt_report(ciphertext: str, encryption_salt: str, collaboration_key: str) -> dict[str, Any]:
    """Decrypt a report only when the owner supplies the correct key."""
    try:
        salt = base64.urlsafe_b64decode(encryption_salt.encode("ascii"))
        plaintext = Fernet(_derive_key(collaboration_key, salt)).decrypt(ciphertext.encode("utf-8"))
        return json.loads(plaintext.decode("utf-8"))
    except (InvalidToken, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("Unable to decrypt this report. Check the collaboration key.") from exc


def short_commitment(commitment: str) -> str:
    return f"{commitment[:12]}…{commitment[-8:]}" if commitment else "—"
