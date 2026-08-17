"""Small, honest integration boundary for Midnight PreProd deployment evidence.

The Streamlit app never fabricates on-chain activity. A contract becomes marked
as deployed only after the team copies verified PreProd references from
midnight/deployment.json.example into an untracked deployment.json file.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEPLOYMENT_PATH = ROOT / "midnight" / "deployment.json"


def get_deployment() -> dict[str, Any]:
    """Read verified deployment metadata from environment or local config."""
    deployment: dict[str, Any] = {
        "network": os.getenv("NIGHTBOUNTY_NETWORK", "PreProd"),
        "contract_address": os.getenv("NIGHTBOUNTY_CONTRACT_ADDRESS", "").strip(),
        "deployment_transaction": os.getenv("NIGHTBOUNTY_DEPLOYMENT_TX", "").strip(),
    }

    if DEPLOYMENT_PATH.exists():
        try:
            saved = json.loads(DEPLOYMENT_PATH.read_text(encoding="utf-8"))
            deployment.update({key: value for key, value in saved.items() if value})
        except json.JSONDecodeError:
            deployment["config_error"] = "deployment.json is not valid JSON"

    deployment["is_deployed"] = bool(
        deployment.get("contract_address") and deployment.get("deployment_transaction")
    )
    return deployment


def contract_label() -> str:
    deployment = get_deployment()
    if not deployment["is_deployed"]:
        return "PreProd pack ready — deployment pending"
    address = str(deployment["contract_address"])
    return f"PreProd verified · {address[:12]}…{address[-6:]}"


def lifecycle_chain_note(action: str) -> str:
    """Return a status note without falsely reporting a transaction."""
    deployment = get_deployment()
    if deployment["is_deployed"]:
        return f"{action} is mapped to the deployed Midnight contract lifecycle."
    return f"{action} is recorded locally until the PreProd contract reference is configured."
