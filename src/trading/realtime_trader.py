"""
Realtime trader orchestrator for KoreaInvestmentAPI + OrderManager.

Features:
- Accepts signals (iterator or supplier) and places orders via KoreaInvestmentAPI
- Respects OrderManager idempotency and basic risk limits
- Dry-run / simulator fallback supported via KoreaInvestmentAPI.dry_run
- Simple blocking or background runner with graceful stop

This is intentionally lightweight and safe for local testing. For production
you should add stronger error handling, persistence, metrics, and broker
signature verification.
"""
from threading import Thread, Event
import time
import logging
from typing import Callable, Iterable, Optional

from .korea_investment_order import KoreaInvestmentAPI
from .order_manager import OrderManager
from .approval import ApprovalManager

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(message)s')


class RealtimeTrader:
    def __init__(self,
                 api: Optional[KoreaInvestmentAPI] = None,
                 order_manager: Optional[OrderManager] = None,
                 poll_interval: float = 1.0,
                 dry_run: Optional[bool] = None,
                 approval_callback: Optional[Callable[[dict], bool]] = None,
                 approval_manager: Optional[ApprovalManager] = None):
        """approval_callback: callable(signal) -> bool. If provided, used to approve
        each order before it is submitted to the broker. If None, the trader will
        require interactive confirmation for non-dry-run runs (when running
        `run_from_iterator`), and background runs must provide a callback or
        enable AUTO_APPROVE/OPERATOR_APPROVAL_FILE env toggles.
        """
        self.api = api or KoreaInvestmentAPI()
        if dry_run is not None:
            self.api.dry_run = bool(dry_run)
        self.order_manager = order_manager or OrderManager()
        self.poll_interval = poll_interval
        self.approval_callback = approval_callback
        # optional ApprovalManager for non-blocking approvals
        self.approval_manager = approval_manager
        if self.approval_manager:
            # register handler so approval manager will call us on approve
            try:
                self.approval_manager.register_handler(self._on_approved_record)
            except Exception:
                pass
        self._stop = Event()
        self._thread: Optional[Thread] = None

    def _require_approval(self, sig: dict) -> bool:
        """Return True if the order is approved to be sent to the broker.

        Rules:
        - If API is in dry_run mode, automatically approve.
        - If an explicit approval_callback is provided, call it.
        - If AUTO_APPROVE env var set to '1'/'true' or OPERATOR_APPROVAL_FILE exists, auto-approve.
        - Otherwise, prompt interactively (suitable for run_from_iterator blocking runs).
        """
        # auto approve in dry-run
        try:
            import os as _os
        except Exception:
            _os = None

        if self.api and getattr(self.api, 'dry_run', False):
            return True

        # explicit callback from caller (blocking semantics)
        if self.approval_callback:
            try:
                return bool(self.approval_callback(sig))
            except Exception:
                LOGGER.exception('approval_callback 호출 중 예외')
                return False

        # non-blocking approval manager: submit and return False (will be sent when approved)
        if self.approval_manager:
            try:
                req_id = self.approval_manager.submit(sig)
                LOGGER.info('주문을 승인 큐에 제출함 (req_id=%s)', req_id)
                return False
            except Exception:
                LOGGER.exception('승인 큐 제출 중 예외')
                return False

        # environment toggles
        if _os:
            if _os.environ.get('AUTO_APPROVE', '').lower() in ('1', 'true'):
                return True
            op_file = _os.environ.get('OPERATOR_APPROVAL_FILE')
            if op_file and _os.path.exists(op_file):
                return True

        # last resort: interactive confirmation
        try:
            prompt = ("주문 승인 필요: {side} {symbol} {qty}@{price} (idempotency={key}).\n"
                      "Approve and send to broker? (y/N): ").format(
                side=sig.get('side', 'buy'), symbol=sig.get('symbol'), qty=sig.get('qty'), price=sig.get('price'), key=sig.get('idempotency_key'))
            ans = input(prompt)
            return ans.strip().lower() in ('y', 'yes')
        except Exception:
            LOGGER.exception('인터랙티브 승인 중 예외 발생')
            return False

    def _process_signal(self, sig: dict):
        """Validate signal and attempt to place order.

        signal shape expected: {'symbol': '005930', 'qty': 1, 'price': 70000, 'side': 'buy', 'idempotency_key': 'k1'}
        """
        symbol = sig.get('symbol')
        try:
            qty = int(sig.get('qty', 0))
        except Exception:
            qty = 0
        try:
            price = float(sig.get('price', 0))
        except Exception:
            price = 0.0
        side = sig.get('side', 'buy')
        key = sig.get('idempotency_key')

        if not symbol or qty <= 0:
            LOGGER.warning('무효한 시그널 수신: %s', sig)
            return

        if self.order_manager.is_idempotent(key):
            LOGGER.info('이미 처리된 idempotency key, 건너뜀: %s', key)
            return

        if not self.order_manager.can_place_order(symbol, qty, price):
            LOGGER.warning('리스크 제한으로 주문 차단: %s', sig)
            return

        LOGGER.info('주문 시도 예정: %s %s %s@%s (key=%s)', side, symbol, qty, price, key)

        # Check approval before sending to broker (no-op in dry-run)
        approved = self._require_approval(sig)
        if not approved:
            LOGGER.info('주문이 승인되지 않아 전송하지 않음: %s', sig)
            # register as skipped for auditability
            try:
                self.order_manager.register_order(symbol, qty, price, side, key, {'status': 'skipped', 'reason': 'not_approved'})
            except Exception:
                LOGGER.exception('스킵된 주문 기록 실패')
            return

        try:
            result = self.api.send_order(symbol, qty, price, side=side)
        except Exception as e:
            LOGGER.exception('주문 호출 중 예외 발생: %s', e)
            result = {'error': str(e)}

        # Register order in manager (persists log, marks idempotency)
        try:
            self.order_manager.register_order(symbol, qty, price, side, key, result)
        except Exception:
            LOGGER.exception('주문 기록 등록 실패')

        # If broker returned an order_id, optionally wait for fill (short timeout)
        order_id = None
        if isinstance(result, dict):
            order_id = result.get('order_id')

        if order_id:
            try:
                status = self.api.wait_for_fill(order_id, timeout=10, poll_interval=1.0)
                LOGGER.info('주문 상태: %s', status)
            except Exception:
                LOGGER.exception('체결 대기 중 예외 발생')

    def _on_approved_record(self, rec: dict):
        """Called by ApprovalManager in a background thread when a request is approved.

        rec contains: {'id', 'signal', ...}
        """
        try:
            sig = rec.get('signal', {})
            symbol = sig.get('symbol')
            qty = int(sig.get('qty', 0))
            price = float(sig.get('price', 0) or 0)
            side = sig.get('side', 'buy')
            key = sig.get('idempotency_key')

            LOGGER.info('승인된 주문 실행: %s %s %s@%s (key=%s)', side, symbol, qty, price, key)
            result = self.api.send_order(symbol, qty, price, side=side)
            # persist via order_manager
            try:
                self.order_manager.register_order(symbol, qty, price, side, key, result)
            except Exception:
                LOGGER.exception('승인 주문 기록 등록 실패')
        except Exception:
            LOGGER.exception('승인된 주문 처리 중 예외')

    def run_from_iterator(self, signals: Iterable[dict]):
        """Blocking run: consume iterator of signals until exhausted or stop requested."""
        for sig in signals:
            if self._stop.is_set():
                LOGGER.info('중지 요청 수신, 루프 종료')
                break
            self._process_signal(sig)
            time.sleep(self.poll_interval)

    def start_background(self, supplier: Callable[[], Iterable[dict]]):
        """Start processing in background thread. supplier should be a callable returning an iterable of signals."""
        if self._thread and self._thread.is_alive():
            LOGGER.warning('이미 실행 중입니다')
            return

        def _target():
            try:
                for sig in supplier():
                    if self._stop.is_set():
                        LOGGER.info('중지 요청 감지, 백그라운드 루프 종료')
                        break
                    self._process_signal(sig)
                    time.sleep(self.poll_interval)
            except Exception:
                LOGGER.exception('백그라운드 실행 중 예외')

        self._thread = Thread(target=_target, daemon=True)
        self._thread.start()
        LOGGER.info('백그라운드 실시간 트레이더 시작')

    def stop(self):
        LOGGER.info('트레이더 중지 요청')
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
            LOGGER.info('백그라운드 스레드 종료 완료')


if __name__ == '__main__':
    # Demo: simulate a small set of signals for local testing.
    def demo_signals():
        sample = [
            {'symbol': '005930', 'qty': 1, 'price': 70000, 'side': 'buy', 'idempotency_key': 'demo-1'},
            {'symbol': '000660', 'qty': 1, 'price': 90000, 'side': 'buy', 'idempotency_key': 'demo-2'},
            {'symbol': '005930', 'qty': 1, 'price': 70000, 'side': 'sell', 'idempotency_key': 'demo-3'},
        ]
        for s in sample:
            yield s

    trader = RealtimeTrader(dry_run=True)
    trader.run_from_iterator(demo_signals())
