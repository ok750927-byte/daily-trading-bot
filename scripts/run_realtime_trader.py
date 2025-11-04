"""
Run the RealtimeTrader locally for development/demo.

Usage (Windows cmd):
    python scripts\run_realtime_trader.py

This will run in dry-run mode by default. To test with real API credentials,
set the environment variables (KOREA_APP_KEY, KOREA_APP_SECRET, KOREA_ACCOUNT_NO,
KOREA_ACCOUNT_PRDT) and unset DRY_RUN or set DRY_RUN=0.
"""
import os
import time
import argparse
from src.trading.realtime_trader import RealtimeTrader
# Keychain helper: attempt to populate env from OS keychain before starting
try:
    from src.trading.keychain import load_secrets_into_env
except Exception:
    load_secrets_into_env = None


def demo_signal_supplier():
    # This supplier yields a small stream of demo signals and then stops.
    symbols = ['005930', '000660', '035420']
    for i, sym in enumerate(symbols, start=1):
        yield {
            'symbol': sym,
            'qty': 1,
            'price': 100000 - i * 1000,
            'side': 'buy' if i % 2 == 1 else 'sell',
            'idempotency_key': f'demo-{int(time.time())}-{i}'
        }


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--auto-approve', action='store_true', help='Automatically approve orders (use with caution)')
    p.add_argument('--no-dry-run', action='store_true', help='Disable dry-run (will attempt real orders if env is configured)')
    args = p.parse_args()

    # Dry-run default for safety; allow override
    dry_run_env = os.environ.get('DRY_RUN', '1')
    dry_run = not args.no_dry_run and dry_run_env not in ('0', 'false', 'False')

    # If auto-approve flag is set, set AUTO_APPROVE env var for downstream use
    if args.auto_approve:
        os.environ['AUTO_APPROVE'] = '1'

    print(f"실행: RealtimeTrader (dry_run={dry_run}, auto_approve={os.environ.get('AUTO_APPROVE','0')})")
    # Try to populate secrets from OS keychain before instantiating API
    if load_secrets_into_env:
        load_secrets_into_env(['KOREA_APP_KEY','KOREA_APP_SECRET','KOREA_ACCOUNT_NO','KOREA_ACCOUNT_PRDT'])

    trader = RealtimeTrader(dry_run=dry_run)
    # For interactive blocking runs, run_from_iterator will prompt unless AUTO_APPROVE is set
    trader.run_from_iterator(demo_signal_supplier())


if __name__ == '__main__':
    main()
