"""Generate a NightBounty owner X25519 report-encryption key pair."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from nightbounty.crypto import generate_owner_keypair


keypair = generate_owner_keypair()
print("Add this private value to Streamlit Cloud App settings → Secrets:")
print()
print(f'owner_x25519_private_key_b64 = "{keypair["private_key_b64"]}"')
print()
print("Public owner encryption profile (safe to show on the bounty board):")
print(f'public_key_b64 = "{keypair["public_key_b64"]}"')
print(f'key_id = "{keypair["key_id"]}"')
print()
print("Never commit, share, or paste the private key into the public bounty description.")
