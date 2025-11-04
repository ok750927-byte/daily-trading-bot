"""CLI to register an operator credential into the OS keyring.

Usage:
    python scripts/operator_set_creds.py

It prompts for username and password and stores them under service 'daily_trading'.
"""
from __future__ import annotations

import getpass
import sys
from src.trading import operator_auth


def main() -> int:
    print("Operator credential registration")
    username = input("Operator username: ").strip()
    if not username:
        print("Username required")
        return 2
    password = getpass.getpass("Password: ")
    if not password:
        print("Password required")
        return 2

    ok = operator_auth.store_credentials(username, password)
    if ok:
        print("Stored credentials in OS keyring.")
        # also persist username to results/operator.txt for GUI convenience
        try:
            import os
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            os.makedirs(os.path.join(base, 'results'), exist_ok=True)
            with open(os.path.join(base, 'results', 'operator.txt'), 'w', encoding='utf-8') as fh:
                fh.write(username + "\n")
        except Exception:
            pass
        return 0
    else:
        print("Failed to store in keyring (is keyring available?).")
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
