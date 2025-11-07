"""Reconciliation script: compare local order log with broker and optionally
attempt corrective actions (report, cancel, or re-submit).

Usage:
  python scripts/reconcile_orders.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from src.trading.order_manager import OrderManager
from src.trading.broker_adapter import DryRunAdapter


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--dry-run', action='store_true', help='Do not perform corrective actions')
    args = p.parse_args(argv)

    base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    log_path = os.path.join(base, 'results', 'order_log.jsonl')
    om = OrderManager(log_path=log_path)
    broker = DryRunAdapter()

    report = om.sync_with_broker(broker)
    print('Reconciliation report:')
    print(json.dumps(report, indent=2, ensure_ascii=False))

    if report.get('mismatches'):
        print('Found mismatches:')
        for m in report['mismatches']:
            print(' -', m)
        if args.dry_run:
            print('Dry-run mode: no corrective actions executed')
            return 0
        # corrective action example: log for operator review; advanced: cancel/retry
        print('No automatic corrective actions implemented in MVP. Please review mismatches in operator console.')
    else:
        print('No mismatches found.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
