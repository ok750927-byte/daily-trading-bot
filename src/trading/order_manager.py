import os
import json
import time
from typing import Optional


class OrderManager:
    """Simple in-repo order manager to enforce basic risk limits and idempotency.

    This is intentionally lightweight: it keeps an in-memory set of seen
    idempotency keys and appends orders to a local JSONL log for persistence.
    """

    def __init__(self, log_path=None, max_position_per_symbol=None, max_total_exposure=None):
        self.seen_keys = set()
        self.log_path = log_path or os.path.join('results', 'order_log.jsonl')
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        # simple risk limits (None = unlimited)
        self.max_position_per_symbol = max_position_per_symbol or 1000000000
        self.max_total_exposure = max_total_exposure or 1000000000

    def _persist(self, record: dict):
        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

    def is_idempotent(self, key: Optional[str]) -> bool:
        if not key:
            return False
        return key in self.seen_keys

    def mark_idempotent(self, key: Optional[str]):
        if key:
            self.seen_keys.add(key)

    def can_place_order(self, symbol: str, qty: int, price: float) -> bool:
        # naive exposure check: qty * price must be <= max_position_per_symbol
        if qty * price > self.max_position_per_symbol:
            return False
        # total exposure check: read log and sum existing exposures
        try:
            total = 0
            if os.path.exists(self.log_path):
                with open(self.log_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            r = json.loads(line)
                            total += r.get('qty', 0) * r.get('price', 0)
                        except Exception:
                            continue
            if total + qty * price > self.max_total_exposure:
                return False
        except Exception:
            # if any error, be conservative and allow (do not block on logging issues)
            return True
        return True

    def register_order(self, symbol: str, qty: int, price: float, side: str, idempotency_key: Optional[str], result: dict):
        rec = {
            'timestamp': int(time.time()),
            'symbol': symbol,
            'qty': qty,
            'price': price,
            'side': side,
            'idempotency_key': idempotency_key,
            'result': result
        }
        self._persist(rec)
        if idempotency_key:
            self.mark_idempotent(idempotency_key)

    def sync_with_broker(self, broker) -> dict:
        """Compare local order log statuses with the broker's reported status.

        Returns a dict with keys: 'checked' (int) and 'mismatches' (list).
        Each mismatch is a dict with 'order_id', 'local', and 'remote'.
        """
        report = {'checked': 0, 'mismatches': []}
        try:
            if not os.path.exists(self.log_path):
                return report
            with open(self.log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        rec = json.loads(line)
                    except Exception:
                        continue
                    # support multiple log shapes: {'result': {...}} or {'order': {...}}
                    res = rec.get('result') or rec.get('order') or {}
                    order_id = res.get('order_id')
                    local_status = res.get('status')
                    if not order_id:
                        continue
                    report['checked'] += 1
                    try:
                        remote = broker.get_order_status(order_id)
                    except Exception as e:
                        report['mismatches'].append({'order_id': order_id, 'local': local_status, 'remote': 'error'})
                        continue
                    remote_status = remote.get('status') if isinstance(remote, dict) else None
                    if local_status != remote_status:
                        report['mismatches'].append({'order_id': order_id, 'local': local_status, 'remote': remote_status})
        except Exception:
            # be tolerant: if sync fails, return what we have so caller can handle
            return report
        return report
"""
실전 자동매매 주문/예외처리 모듈 (샘플)
- 주문 실행, 예외처리, 실시간 체결/잔고 모니터링, 장애 복구 로직 포함
- 실제 증권사 API 연동 부분은 각 증권사별 패키지로 대체 필요
"""
import os
import time
import random

class TradingAPI:
    def __init__(self):
        self.api_key = os.environ.get('TRADING_API_KEY')
        self.api_secret = os.environ.get('TRADING_API_SECRET')
        # 민감정보 마스킹: print/log에서 절대 노출 금지
        # 실제 API 연결/로그인 코드 필요

    def send_order(self, symbol, qty, order_type='buy'):
        try:
            # 실제 주문 API 호출 코드로 대체
            print(f"[주문] {symbol} {order_type} {qty}주 요청...")
            # 예시: 랜덤 실패 시뮬레이션
            if random.random() < 0.1:
                raise ConnectionError("네트워크 오류: 주문 실패")
            # 체결 성공 시
            print(f"[체결] {symbol} {order_type} {qty}주 체결 완료!")
            return True
        except Exception as e:
            # 예외 메시지에 민감정보가 포함되지 않도록 마스킹
            err_msg = str(e)
            for secret in [self.api_key, self.api_secret]:
                if secret and secret in err_msg:
                    err_msg = err_msg.replace(secret, '***MASKED***')
            print(f"[오류] 주문 실패: {err_msg}")
            # 장애 복구/재시도 로직
            for retry in range(3):
                print(f"[재시도] {retry+1}회...")
                time.sleep(1)
                try:
                    # 실제 주문 재시도 코드
                    print(f"[주문 재시도] {symbol} {order_type} {qty}주...")
                    if random.random() < 0.2:
                        raise ConnectionError("네트워크 오류: 주문 실패")
                    print(f"[체결] {symbol} {order_type} {qty}주 체결 완료!")
                    return True
                except Exception as e2:
                    err_msg2 = str(e2)
                    for secret in [self.api_key, self.api_secret]:
                        if secret and secret in err_msg2:
                            err_msg2 = err_msg2.replace(secret, '***MASKED***')
                    print(f"[오류] 재시도 실패: {err_msg2}")
            print(f"[치명적 오류] {symbol} 주문 최종 실패!")
            return False

    def monitor_orders(self):
        # 실시간 체결/잔고 모니터링 (샘플)
        print("[모니터링] 실시간 체결/잔고 상태 확인...")
        # 실제 API polling/websocket 등 구현 필요
        return {"AAPL": {"qty": 10, "status": "filled"}}

if __name__ == "__main__":
    api = TradingAPI()
    # 샘플 주문 실행
    api.send_order("AAPL", 10, order_type="buy")
    api.send_order("TSLA", 5, order_type="sell")
    # 실시간 모니터링
    print(api.monitor_orders())
