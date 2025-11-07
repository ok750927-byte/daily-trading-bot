import time
import threading
from typing import Dict, Any
import os

class ExecutionGateway:
    """Minimal execution gateway supporting SIM and LIVE modes.
    - In SIM mode the gateway simulates fills and returns a simulated execution report.
    - In LIVE mode this is a stub that will only run if environment variable ALLOW_LIVE=1 is set.
    """
    def __init__(self, mode: str = 'SIM'):
        self.mode = mode.upper()

    def set_mode(self, mode: str):
        self.mode = mode.upper()

    def send_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        # Basic validation
        symbol = order.get('symbol')
        qty = int(order.get('qty', 0))
        side = order.get('side')
        otype = order.get('type', 'MARKET')
        price = order.get('price') or None

        if not symbol or qty <= 0 or side not in ('BUY', 'SELL'):
            return {'status': 'error', 'reason': 'invalid order'}

        if self.mode == 'SIM':
            # simulate latency
            time.sleep(0.5)
            report = {
                'status': 'filled',
                'symbol': symbol,
                'side': side,
                'qty': qty,
                'avg_price': float(price) if price else 100.0,  # placeholder price
                'execution_id': f'sim-{int(time.time()*1000)}'
            }
            return {'status': 'ok', 'report': report}

        # LIVE mode
        if self.mode == 'LIVE':
            if os.environ.get('ALLOW_LIVE') != '1':
                return {'status': 'error', 'reason': 'LIVE mode disabled (set ALLOW_LIVE=1 to enable)'}
            # Here you'd integrate with broker API; this is a placeholder
            try:
                # TODO: implement real broker integration
                time.sleep(0.5)
                report = {
                    'status': 'filled',
                    'symbol': symbol,
                    'side': side,
                    'qty': qty,
                    'avg_price': float(price) if price else 100.0,
                    'execution_id': f'live-{int(time.time()*1000)}'
                }
                return {'status': 'ok', 'report': report}
            except Exception as e:
                return {'status': 'error', 'reason': str(e)}

        return {'status': 'error', 'reason': 'unknown mode'}
