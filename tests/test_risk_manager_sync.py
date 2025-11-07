import os
import json
import tempfile

from src.trading.risk_manager import RiskManager
from src.trading.order_manager import OrderManager
from src.trading.broker_adapter import DryRunAdapter


def test_risk_manager_blocks_large_order():
    rm = RiskManager(account_equity=1000000, config={'max_position_exposure': 0.1, 'min_cash_reserve': 10000})
    # attempting to buy 100k at price 100 -> 10M exposure -> should be blocked for 1M equity
    res = rm.check_order(symbol='TEST', qty=100000, price=100, side='buy', current_positions={}, cash=200000)
    assert not res.allowed


def test_order_manager_sync_detects_mismatch(tmp_path):
    # create a fake local order log with a status that differs from DryRunAdapter
    log_path = tmp_path / 'order_log.jsonl'
    rec = {'timestamp': 0, 'symbol': 'ABC', 'qty': 1, 'price': 100, 'side': 'buy', 'idempotency_key': 'k1', 'result': {'order_id': 'oid-1', 'status': 'pending'}}
    log_path.write_text(json.dumps(rec, ensure_ascii=False) + '\n')

    om = OrderManager(log_path=str(log_path))
    broker = DryRunAdapter()

    report = om.sync_with_broker(broker)
    # DryRunAdapter returns status 'filled' so mismatch should be reported
    assert report['checked'] >= 1
    assert any(m.get('remote') in ('filled', 'error') or m.get('local') == 'pending' for m in report.get('mismatches', []))
