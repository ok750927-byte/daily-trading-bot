import os
import time
from src.trading.approval import ApprovalManager
from src.trading.realtime_trader import RealtimeTrader
from src.trading.order_manager import OrderManager


class FakeAPI:
    def __init__(self):
        self.sent = []

    def send_order(self, symbol, qty, price, side='buy'):
        self.sent.append({'symbol': symbol, 'qty': qty, 'price': price, 'side': side})
        return {'order_id': 'fake-1', 'status': 'sent'}


def cleanup_results():
    # remove test-generated files under results
    for name in ('order_log.jsonl', 'approval_queue.jsonl', 'pending_approvals.jsonl', 'approval_audit.jsonl'):
        p = os.path.join('results', name)
        try:
            if os.path.exists(p):
                os.remove(p)
        except Exception:
            pass


def test_realtime_trader_approval_flow():
    cleanup_results()
    approval_mgr = ApprovalManager()
    fake_api = FakeAPI()
    order_mgr = OrderManager(log_path=os.path.join('results', 'order_log.jsonl'))

    trader = RealtimeTrader(api=fake_api, order_manager=order_mgr, poll_interval=0.01, approval_manager=approval_mgr)

    sig = {'symbol': 'TST', 'qty': 1, 'price': 100.0, 'side': 'buy', 'idempotency_key': 'k-test-1'}

    # process signal: should submit to approval queue and not send immediately
    trader._process_signal(sig)
    pend = approval_mgr.list_pending()
    assert len(pend) == 1
    aid = pend[0].get('approval_id')

    # approve and ensure handler executes and API send_order is called
    res = approval_mgr.approve(aid, approver='test')
    assert res is True

    # allow tiny time for any async activity (handler is called synchronously by manager)
    time.sleep(0.05)
    assert len(fake_api.sent) == 1
    sent = fake_api.sent[0]
    assert sent['symbol'] == 'TST'
    assert sent['qty'] == 1

    cleanup_results()
