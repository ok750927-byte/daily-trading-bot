"""Prometheus metrics exporter helpers for the trading bot.

This module exposes a small helper to start an HTTP metrics endpoint using
prometheus_client. It's optional and safe to import even if prometheus_client
is not installed (it will no-op).
"""
from __future__ import annotations

import threading
import time
from typing import Optional

try:
    from prometheus_client import start_http_server, Counter, Gauge
except Exception:  # pragma: no cover - optional dependency
    start_http_server = None  # type: ignore
    Counter = None  # type: ignore
    Gauge = None  # type: ignore


class Metrics:
    def __init__(self, port: int = 8001):
        self.port = port
        if Counter is not None:
            self.orders_total = Counter('orders_total', 'Total orders processed')
            self.orders_failed = Counter('orders_failed', 'Total orders failed')
            self.open_positions = Gauge('open_positions', 'Number of open positions')
        else:
            self.orders_total = None
            self.orders_failed = None
            self.open_positions = None

    def start(self):
        if start_http_server is None:
            return
        # start in separate thread to avoid blocking
        t = threading.Thread(target=lambda: start_http_server(self.port), daemon=True)
        t.start()

    def inc_order(self, failed: bool = False) -> None:
        if self.orders_total is not None:
            self.orders_total.inc()
        if failed and self.orders_failed is not None:
            self.orders_failed.inc()

    def set_open_positions(self, n: int) -> None:
        if self.open_positions is not None:
            self.open_positions.set(n)
