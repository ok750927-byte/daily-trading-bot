"""Staging E2E broker test script.

This script demonstrates how to run an end-to-end staging test against the
DryRunAdapter (local simulation) or swap in a real broker adapter if
credentials are available. It's intended as a template for operator-driven
staging verification before moving to production.

Usage:
  python scripts/staging_broker_test.py --dry-run
  python scripts/staging_broker_test.py --use-real-broker

The script will:
 - load a small set of test orders
 - submit them via OrderManager -> broker_adapter
 - perform a reconciliation and print the report

Note: Replace the `load_real_broker()` placeholder with your real adapter
factory (e.g. KoreaInvestmentAPI wrapper) when moving to staging.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from src.trading.order_manager import OrderManager
from src.trading.broker_adapter import DryRunAdapter


def load_test_orders():
    # simple test orders: list of dicts
    return [
        {"id": "test-1", "symbol": "0001", "side": "buy", "qty": 1, "price": 1000},
        {"id": "test-2", "symbol": "0002", "side": "buy", "qty": 2, "price": 500},
    ]


def load_real_broker():
    """Attempt to load a real broker adapter from existing code (KoreaInvestmentAPI).

    This function looks for required environment variables and returns a
    `KoreaInvestmentAPI` instance with `dry_run` disabled. It is intentionally
    permissive: if credentials are missing it raises a helpful error rather
    than attempting unsafe actions.
    """
    try:
        from src.trading.korea_investment_order import KoreaInvestmentAPI
    except Exception as e:
        raise RuntimeError("KoreaInvestmentAPI not available in this workspace") from e

    # prefer env vars; allow keyring fallback for appkey/appsecret if available
    appkey = os.environ.get('KOREA_APP_KEY')
    appsecret = os.environ.get('KOREA_APP_SECRET')
    account_no = os.environ.get('KOREA_ACCOUNT_NO')
    # try keyring fallback for sensitive values
    if not appkey or not appsecret:
        try:
            import keyring
            if not appkey:
                appkey = keyring.get_password('korea_investment', 'app_key')
            if not appsecret:
                appsecret = keyring.get_password('korea_investment', 'app_secret')
            if not account_no:
                account_no = keyring.get_password('korea_investment', 'account_no')
        except Exception:
            pass
    if not (appkey and appsecret and account_no):
        raise RuntimeError("Missing staging broker env vars. Required: KOREA_APP_KEY, KOREA_APP_SECRET, KOREA_ACCOUNT_NO")

    api = KoreaInvestmentAPI()
    api.dry_run = False
    # ensure credentials are loaded on the instance
    api.appkey = appkey
    api.appsecret = appsecret
    return api


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--dry-run', action='store_true', help='Use DryRunAdapter (default)')
    p.add_argument('--use-real-broker', action='store_true', help='Attempt to use a real broker adapter (requires implementation)')
    p.add_argument('--dry-log', default='results/order_log.jsonl', help='Path to local order log')
    args = p.parse_args(argv)

    base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    log_path = os.path.join(base, args.dry_log)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    om = OrderManager(log_path=log_path)

    if args.use_real_broker:
        try:
            broker = load_real_broker()
        except Exception as e:
            print('Failed to load real broker:', e)
            return 2
    else:
        broker = DryRunAdapter()

    orders = load_test_orders()
    print('Submitting test orders...')
    for o in orders:
        # place order via broker and register to order manager (idempotency enforced)
        try:
            res = broker.place_order(o['symbol'], o['qty'], o['price'], o.get('side', 'buy'), idempotency_key=o.get('id'))
        except TypeError:
            # older adapters might expect different signature
            try:
                res = broker.place_order(o)
            except Exception as e:
                print('Broker place_order failed:', e)
                res = {'status': 'error'}
        except Exception as e:
            print('Broker place_order failed:', e)
            res = {'status': 'error'}

        # register with OrderManager using normalized args
        try:
            om.register_order(o['symbol'], o['qty'], o['price'], o.get('side', 'buy'), o.get('id'), res)
        except Exception as e:
            print('OrderManager.register_order failed:', e)

    report = om.sync_with_broker(broker)
    print('Reconciliation report:')
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
