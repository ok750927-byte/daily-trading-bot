import os
from src.trading.signal_order_bridge import execute_signals
from src.trading.order_manager import OrderManager


def test_execute_signals_dry_run(tmp_path, capsys):
    # create a small signals file
    signals = tmp_path / "signals.json"
    signals.write_text('[{"symbol": "005930", "qty": 1, "price": 70000, "side": "buy", "idempotency_key": "k1"}]')

    logpath = tmp_path / "orders.log"
    om = OrderManager(log_path=str(logpath), max_position_per_symbol=10**9, max_total_exposure=10**9)

    execute_signals(str(signals), dry_run=True, order_manager=om)

    # check that order log was created and contains an entry
    assert logpath.exists()
    content = logpath.read_text()
    assert '005930' in content
