"""Hybrid public-key encryption and commitment helpers for NightBounty reports."""

from __future__ import annotations

import base64
import hashlib
import json
import os
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

ENCRYPTION_SCHEME = "nightbounty/x25519-hkdf-sha256-aes-256-gcm/v2"
ENCRYPTION_INFO = b"nightbounty/report-envelope/v2"
OWNER_KEY_BYTES = 32
KDF_ITERATIONS = 480_000


def canonical_payload(payload: dict[str, Any]) -> bytes:
    """Create a stable representation so commitments are reproducible."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii")


def _decode(value: str, *, label: str, expected_length: int | None = None) -> bytes:
    try:
        decoded = base64.b64decode(value.encode("ascii"), altchars=b"-_", validate=True)
    except (UnicodeEncodeError, ValueError) as exc:
        raise ValueError(f"Invalid {label}.") from exc
    if expected_length is not None and len(decoded) != expected_length:
        raise ValueError(f"Invalid {label}.")
    return decoded


def generate_owner_keypair() -> dict[str, str]:
    """Create a raw X25519 key pair for one NightBounty owner."""
    private_key = X25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )
    public_bytes = private_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    public_key_b64 = _encode(public_bytes)
    return {
        "private_key_b64": _encode(private_bytes),
        "public_key_b64": public_key_b64,
        "key_id": owner_key_id(public_key_b64),
    }


def owner_public_key_from_private_key(owner_private_key_b64: str) -> str:
    """Derive a public key from a configured owner private key."""
    private_bytes = _decode(
        owner_private_key_b64.strip(),
        label="owner encryption private key",
        expected_length=OWNER_KEY_BYTES,
    )
    private_key = X25519PrivateKey.from_private_bytes(private_bytes)
    return _encode(
        private_key.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
    )


def owner_key_id(owner_public_key_b64: str) -> str:
    """Return a short, non-secret key identifier suitable for the UI and envelope."""
    public_bytes = _decode(
        owner_public_key_b64.strip(),
        label="owner encryption public key",
        expected_length=OWNER_KEY_BYTES,
    )
    return f"nb-x25519-{hashlib.sha256(public_bytes).hexdigest()[:16]}"


def _owner_public_key(owner_public_key_b64: str) -> X25519PublicKey:
    return X25519PublicKey.from_public_bytes(
        _decode(
            owner_public_key_b64.strip(),
            label="owner encryption public key",
            expected_length=OWNER_KEY_BYTES,
        )
    )


def _owner_private_key(owner_private_key_b64: str) -> X25519PrivateKey:
    return X25519PrivateKey.from_private_bytes(
        _decode(
            owner_private_key_b64.strip(),
            label="owner encryption private key",
            expected_length=OWNER_KEY_BYTES,
        )
    )


def _aad(*, bounty_id: str, recipient_key_id: str) -> bytes:
    if not bounty_id.strip():
        raise ValueError("A bounty ID is required for report encryption.")
    return canonical_payload(
        {
            "scheme": ENCRYPTION_SCHEME,
            "bounty_id": bounty_id,
            "recipient_key_id": recipient_key_id,
        }
    )


def _derive_aead_key(shared_secret: bytes, salt: bytes) -> bytes:
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=ENCRYPTION_INFO,
    ).derive(shared_secret)


def encrypt_report(
    payload: dict[str, Any],
    owner_public_key_b64: str,
    *,
    bounty_id: str,
) -> dict[str, str]:
    """Encrypt a report for an owner using an ephemeral X25519 key agreement.

    The public key is safe to publish. Each submission creates a new ephemeral
    key, KDF salt, and AES-GCM nonce, so reports are cryptographically separate.
    """
    owner_public_key = _owner_public_key(owner_public_key_b64)
    recipient_key_id = owner_key_id(owner_public_key_b64)
    ephemeral_private_key = X25519PrivateKey.generate()
    ephemeral_public_key = ephemeral_private_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    kdf_salt = os.urandom(32)
    nonce = os.urandom(12)
    aead_key = _derive_aead_key(ephemeral_private_key.exchange(owner_public_key), kdf_salt)
    payload_bytes = canonical_payload(payload)
    ciphertext = AESGCM(aead_key).encrypt(
        nonce,
        payload_bytes,
        _aad(bounty_id=bounty_id, recipient_key_id=recipient_key_id),
    )
    commitment_salt = os.urandom(32)
    envelope = {
        "scheme": ENCRYPTION_SCHEME,
        "recipient_key_id": recipient_key_id,
        "ephemeral_public_key": _encode(ephemeral_public_key),
        "kdf_salt": _encode(kdf_salt),
        "nonce": _encode(nonce),
    }

    return {
        "ciphertext": _encode(ciphertext),
        # The database column is retained for compatibility; v2 stores versioned envelope metadata here.
        "encryption_salt": json.dumps(envelope, sort_keys=True, separators=(",", ":")),
        "commitment": hashlib.sha256(payload_bytes + commitment_salt).hexdigest(),
        "payload_digest": hashlib.sha256(payload_bytes).hexdigest(),
    }


def is_public_key_envelope(encryption_metadata: str) -> bool:
    try:
        envelope = json.loads(encryption_metadata)
    except json.JSONDecodeError:
        return False
    return isinstance(envelope, dict) and envelope.get("scheme") == ENCRYPTION_SCHEME


def decrypt_report(
    ciphertext: str,
    encryption_metadata: str,
    owner_private_key_b64: str,
    *,
    bounty_id: str,
) -> dict[str, Any]:
    """Authenticate and decrypt a v2 report using the configured owner private key."""
    try:
        envelope = json.loads(encryption_metadata)
        if not isinstance(envelope, dict) or envelope.get("scheme") != ENCRYPTION_SCHEME:
            raise ValueError("Unsupported report encryption scheme.")
        recipient_key_id = envelope["recipient_key_id"]
        ephemeral_public_key = X25519PublicKey.from_public_bytes(
            _decode(envelope["ephemeral_public_key"], label="report envelope", expected_length=OWNER_KEY_BYTES)
        )
        kdf_salt = _decode(envelope["kdf_salt"], label="report envelope", expected_length=32)
        nonce = _decode(envelope["nonce"], label="report envelope", expected_length=12)
        if not isinstance(recipient_key_id, str) or recipient_key_id != owner_key_id(
            owner_public_key_from_private_key(owner_private_key_b64)
        ):
            raise ValueError("Recipient key does not match configured owner key.")
        plaintext = AESGCM(
            _derive_aead_key(_owner_private_key(owner_private_key_b64).exchange(ephemeral_public_key), kdf_salt)
        ).decrypt(
            nonce,
            _decode(ciphertext, label="report ciphertext"),
            _aad(bounty_id=bounty_id, recipient_key_id=recipient_key_id),
        )
        payload = json.loads(plaintext.decode("utf-8"))
        if not isinstance(payload, dict):
            raise TypeError("Decrypted report is not an object.")
        return payload
    except (InvalidTag, KeyError, TypeError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("This report cannot be authenticated or decrypted with the configured owner key.") from exc


def _derive_legacy_key(passphrase: str, salt: bytes) -> bytes:
    if len(passphrase.strip()) < 8:
        raise ValueError("Use a collaboration key with at least 8 characters.")
    return base64.urlsafe_b64encode(
        PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=KDF_ITERATIONS,
        ).derive(passphrase.encode("utf-8"))
    )


def decrypt_legacy_report(ciphertext: str, encryption_salt: str, collaboration_key: str) -> dict[str, Any]:
    """Allow existing v1 demo reports to be opened during the encryption migration."""
    try:
        salt = _decode(encryption_salt, label="legacy report salt", expected_length=16)
        plaintext = Fernet(_derive_legacy_key(collaboration_key, salt)).decrypt(ciphertext.encode("utf-8"))
        payload = json.loads(plaintext.decode("utf-8"))
        if not isinstance(payload, dict):
            raise TypeError("Legacy report is not an object.")
        return payload
    except (InvalidToken, TypeError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("Unable to decrypt this legacy report. Check the collaboration key.") from exc


def short_commitment(commitment: str) -> str:
    return f"{commitment[:12]}…{commitment[-8:]}" if commitment else "—"
