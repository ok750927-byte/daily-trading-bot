"""Broker adapter interface and a safe dry-run adapter for development.

Design: RealtimeTrader will depend on a broker adapter implementing the
place_order / cancel_order / get_order_status API. A DryRunAdapter simulates
orders and writes them to `results/order_log.jsonl` for traceability.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from typing import Dict, Optional


class BrokerAdapter:
    """Abstract interface for broker adapters."""

    def place_order(self, symbol: str, qty: int, price: float, side: str, idempotency_key: Optional[str] = None) -> Dict:
        raise NotImplementedError()

    def cancel_order(self, order_id: str) -> Dict:
        raise NotImplementedError()

    def get_order_status(self, order_id: str) -> Dict:
        raise NotImplementedError()


class DryRunAdapter(BrokerAdapter):
    """Simulate broker behaviour; persist to `results/order_log.jsonl`."""

    def __init__(self, results_dir: Optional[str] = None):
        base = results_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), '..')
        # normalize
        self.results_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'results'))
        os.makedirs(self.results_dir, exist_ok=True)
        self.log_path = os.path.join(self.results_dir, 'order_log.jsonl')

    def _write(self, payload: Dict) -> None:
        payload.setdefault('timestamp', time.time())
        with open(self.log_path, 'a', encoding='utf-8') as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + '\n')

    def place_order(self, symbol: str, qty: int, price: float, side: str, idempotency_key: Optional[str] = None) -> Dict:
        order_id = str(uuid.uuid4())
        rec = {
            'order_id': order_id,
            'symbol': symbol,
            'qty': qty,
            'price': price,
            'side': side,
            'idempotency_key': idempotency_key,
            'status': 'filled',
        }
        self._write({'action': 'place', 'order': rec})
        return rec

    def cancel_order(self, order_id: str) -> Dict:
        rec = {'order_id': order_id, 'status': 'cancelled'}
        self._write({'action': 'cancel', 'order': rec})
        return rec

    def get_order_status(self, order_id: str) -> Dict:
        # dry-run: return a filled status
        return {'order_id': order_id, 'status': 'filled'}
