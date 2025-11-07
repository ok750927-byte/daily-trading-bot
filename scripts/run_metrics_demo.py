"""Run a simple Prometheus metrics demo for the trading bot.

This starts the metrics HTTP server and increments counters periodically.
"""
from __future__ import annotations

import time
from src.trading.metrics import Metrics


def main():
    m = Metrics(port=8001)
    m.start()
    print('Metrics server started on port 8001. Ctrl-C to stop.')
    try:
        n = 0
        while True:
            m.inc_order(failed=(n % 5 == 0))
            m.set_open_positions(n % 10)
            n += 1
            time.sleep(1)
    except KeyboardInterrupt:
        print('Stopping metrics demo')


if __name__ == '__main__':
    main()
