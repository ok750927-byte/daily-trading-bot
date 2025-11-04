"""
전략 신호와 자동주문 연동 샘플
- 예측/신호(json, dict 등) → 한국투자증권 주문 API 자동 실행
- 예외처리, 주문 결과 로깅 포함
"""
import json
import time
from typing import Optional
from src.trading.korea_investment_order import KoreaInvestmentAPI
from src.trading.order_manager import OrderManager

def load_signals(signal_path):
    with open(signal_path, encoding='utf-8') as f:
        return json.load(f)

def execute_signals(signal_path, dry_run=False, order_manager: Optional[OrderManager] = None):
    # Allow passing dry_run flag programmatically; default can also be set via env DRY_RUN
    api = KoreaInvestmentAPI()
    if dry_run:
        api.dry_run = True

    # order_manager: allow injection for testing/persistence; default simple manager
    if order_manager is None:
        order_manager = OrderManager()

    signals = load_signals(signal_path)
    for sig in signals:
        try:
            symbol = sig['symbol']
            qty = int(sig['qty'])
            price = float(sig['price'])
            side = sig.get('side', 'buy')
            idempotency_key = sig.get('idempotency_key')

            print(f"[신호] {symbol} {side} {qty}주 @ {price}")

            # Idempotency: skip if key already seen
            if order_manager.is_idempotent(idempotency_key):
                print(f"[중복건] idempotency_key={idempotency_key} 이미 처리됨. 스킵합니다.")
                continue

            # Risk checks
            if not order_manager.can_place_order(symbol, qty, price):
                print(f"[리스크차단] 주문 금액/포지션 한도 초과: {symbol} {qty}@{price}")
                continue

            # Send order (API may be dry-run)
            result = api.send_order(symbol, qty, price, side)

            # Register the initial order record regardless of simulated/real
            order_manager.register_order(symbol, qty, price, side, idempotency_key, result or {})

            # If a real order was placed (or even simulated with order_id), wait for fill/reconciliation
            order_id = None
            if isinstance(result, dict):
                order_id = result.get('order_id')

            if order_id and not api.dry_run:
                status = api.wait_for_fill(order_id, timeout=30)
                # register the final status update
                order_manager.register_order(symbol, qty, price, side, idempotency_key, status or {})

            if result:
                print(f"[주문완료] {symbol} {side} {qty}주")
            else:
                print(f"[주문실패] {symbol} {side} {qty}주")

            time.sleep(0.5)  # 주문간 딜레이
        except Exception as e:
            print(f"[예외] {sig}: {e}")

if __name__ == "__main__":
    # 예시: 'results/predictions.json' 신호 파일 사용
    execute_signals('results/predictions.json')
