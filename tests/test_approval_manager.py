import os
import time
from src.trading.approval import ApprovalManager, AUDIT_FILE, QUEUE_FILE, PENDING_FILE


def cleanup_files():
    for p in (AUDIT_FILE, QUEUE_FILE, PENDING_FILE):
        try:
            if os.path.exists(p):
                os.remove(p)
        except Exception:
            pass


def test_submit_list_approve_reject():
    cleanup_files()
    mgr = ApprovalManager()
    payload = {'symbol': 'TEST', 'order_type': 'buy', 'quantity': 1}
    aid = mgr.submit(payload)
    pend = mgr.list_pending()
    assert any(r.get('approval_id') == aid for r in pend)
    assert mgr.check_approval(aid) == 'pending'

    # approve
    ok = mgr.approve(aid, approver='unittest')
    assert ok is True
    # after approval, pending should not contain it
    pend2 = mgr.list_pending()
    assert not any(r.get('approval_id') == aid for r in pend2)

    # submit again and reject
    aid2 = mgr.submit({'symbol': 'X', 'order_type': 'sell'})
    ok2 = mgr.reject(aid2, operator='unittest')
    assert ok2 is True
    pend3 = mgr.list_pending()
    assert not any(r.get('approval_id') == aid2 for r in pend3)

    cleanup_files()


def test_handler_called_on_approve():
    cleanup_files()
    mgr = ApprovalManager()
    called = []

    def handler(rec):
        called.append(rec.get('approval_id'))

    mgr.register_handler(handler)
    aid = mgr.submit({'symbol': 'H', 'order_type': 'buy'})
    mgr.approve(aid, approver='unittest')
    # handler is called asynchronously; wait briefly (up to 1s)
    waited = 0.0
    while waited < 1.0 and aid not in called:
        time.sleep(0.05)
        waited += 0.05
    assert aid in called

    cleanup_files()
