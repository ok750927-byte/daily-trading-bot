"""Simple operator credential helpers using the OS keyring.

This module provides minimal helpers to store and verify an operator's
credentials using the `keyring` package. It intentionally keeps behavior
simple: operator usernames are stored as the key and their password stored
in the system keyring under the service name 'daily_trading'.

The GUI continues to persist `results/operator.txt` for convenience and
this module also exposes a helper to read that persisted name.
"""
from __future__ import annotations

import os
from typing import Optional

try:
    import keyring
except Exception:  # pragma: no cover - optional dependency
    keyring = None  # type: ignore


SERVICE_NAME = "daily_trading"


def store_credentials(username: str, password: str) -> bool:
    """Store operator credentials into the OS keyring.

    Returns True on success, False if keyring is unavailable or an error.
    """
    if keyring is None:
        return False
    try:
        keyring.set_password(SERVICE_NAME, username, password)
        return True
    except Exception:
        return False


def verify_credentials(username: str, password: str) -> bool:
    """Verify provided credentials against the keyring.

    Returns True if the stored password matches, False otherwise or if
    keyring is not available / credential not found.
    """
    if keyring is None:
        return False
    try:
        stored = keyring.get_password(SERVICE_NAME, username)
        return stored == password
    except Exception:
        return False


def get_persisted_operator_name() -> Optional[str]:
    """Return the persisted operator name from `results/operator.txt` if present."""
    base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    path = os.path.join(base, "results", "operator.txt")
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                name = fh.read().strip()
                return name or None
    except Exception:
        return None
    return None
