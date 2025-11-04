"""
한국투자증권 OpenAPI 연동 기반 전략 자동주문/실시간 모니터링 모듈 (샘플)
- 실제 사용 시 'kiwoom', 'ebest', 'koreainvestment' 등 공식 패키지 설치 필요
- 본 코드는 REST API 예시(한국투자증권 openapi)를 기반으로 하며, 실전 적용 전 반드시 문서/테스트 필요
"""
import os
import time
import requests

class KoreaInvestmentAPI:
    BASE_URL = "https://openapi.koreainvestment.com:9443"

    def __init__(self):
        # Allow dry-run mode via environment variable or by setting attribute
        self.dry_run = os.environ.get('DRY_RUN', '0') in ('1', 'true', 'True')
        self.appkey = os.environ.get('KOREA_APP_KEY')
        self.appsecret = os.environ.get('KOREA_APP_SECRET')
        # Do not fetch access token at construction time to avoid network calls during import/instantiation
        # Tests can set up request mocks before calling methods that perform network requests.
        self.access_token = None

    def get_access_token(self):
        # In dry-run mode, return a fake token and avoid network calls
        if self.dry_run:
            self.access_token = 'dry-run-token'
            return self.access_token

        url = f"{self.BASE_URL}/oauth2/tokenP"
        headers = {"content-type": "application/json"}
        payload = {
            "grant_type": "client_credentials",
            "appkey": self.appkey,
            "appsecret": self.appsecret
        }
        resp = requests.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        token = resp.json().get('access_token')
        # cache token on the instance for later calls/tests
        self.access_token = token
        return token

    def send_order(self, symbol, qty, price, side='buy'):
        # Ensure we have a valid access token (lazy fetch)
        if not self.access_token:
            self.access_token = self.get_access_token()

        # Dry-run: do not call remote API, just log simulated order
        if self.dry_run:
            order_id = f"sim-{int(time.time()*1000)}"
            print(f"[DRY-RUN 주문] 시뮬레이션: {symbol} {side} {qty}주 @ {price} (order_id={order_id})")
            return {
                'status': 'simulated',
                'symbol': symbol,
                'side': side,
                'qty': qty,
                'price': price,
                'order_id': order_id
            }
        url = f"{self.BASE_URL}/uapi/domestic-stock/v1/trading/order-cash"
        headers = {
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.appkey,
            "appsecret": self.appsecret,
            "tr_id": "TTTC0802U" if side=="buy" else "TTTC0801U"
        }
        data = {
            "CANO": os.environ.get('KOREA_ACCOUNT_NO'),
            "ACNT_PRDT_CD": os.environ.get('KOREA_ACCOUNT_PRDT'),
            "PDNO": symbol,
            "ORD_DVSN": "00",  # 지정가
            "ORD_QTY": str(qty),
            "ORD_UNPR": str(price)
        }
        # Real send with basic retry/backoff and idempotency header support
        max_attempts = 3
        backoff = 0.5
        last_exc = None
        for attempt in range(1, max_attempts + 1):
            try:
                resp = requests.post(url, headers=headers, json=data, timeout=10)
                if resp.status_code == 200:
                    print(f"[주문성공] {symbol} {side} {qty}주 @ {price}")
                    # Try to return a consistent structure including order_id when available
                    j = resp.json()
                    # Common broker response patterns: {'order_id': ...}, {'output': {'orderId': ...}}, {'orderNo': ...}
                    order_id = None
                    if isinstance(j, dict):
                        if 'order_id' in j:
                            order_id = j.get('order_id')
                        elif 'orderNo' in j:
                            order_id = j.get('orderNo')
                        elif isinstance(j.get('output'), dict) and 'orderId' in j.get('output'):
                            order_id = j.get('output', {}).get('orderId')
                    # normalize
                    ret = j if isinstance(j, dict) else {'response': j}
                    ret['order_id'] = order_id
                    return ret
                else:
                    # non-200, log and retry
                    print(f"[주문오류] status={resp.status_code} body={resp.text}")
                    last_exc = Exception(f"HTTP {resp.status_code}")
            except Exception as e:
                last_exc = e
                print(f"[주문예외] 시도 {attempt}/{max_attempts}: {e}")

            if attempt < max_attempts:
                time.sleep(backoff)
                backoff *= 2

        # If we reach here, all attempts failed
        print(f"[주문실패] 요청이 모두 실패했습니다: {symbol} {side} {qty}@{price}")
        return None

    def get_order_status(self, order_id: str):
        """Query order status. In dry-run mode, returns filled for any sim id."""
        if self.dry_run:
            # simulate immediate fill
            return {'order_id': order_id, 'status': 'filled'}

        # Placeholder: real endpoint integration should be implemented per broker API
        try:
            url = f"{self.BASE_URL}/uapi/domestic-stock/v1/trading/inquire-order"
            headers = {
                "authorization": f"Bearer {self.access_token}",
                "appkey": self.appkey,
                "appsecret": self.appsecret,
            }
            params = { 'order_id': order_id }
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            resp.raise_for_status()
            j = resp.json()
            # try to normalize status from common fields
            status = None
            if isinstance(j, dict):
                # example shapes: {'status': 'filled'}, {'output': {'ord_stat': 'filled'}}, {'body': {'orderStat': 'filled'}}
                if 'status' in j:
                    status = j.get('status')
                elif isinstance(j.get('output'), dict) and 'ord_stat' in j.get('output'):
                    status = j.get('output', {}).get('ord_stat')
                elif isinstance(j.get('body'), dict) and 'orderStat' in j.get('body'):
                    status = j.get('body', {}).get('orderStat')
            if status:
                return {'order_id': order_id, 'status': status, 'raw': j}
            return {'order_id': order_id, 'status': 'unknown', 'raw': j}
        except Exception as e:
            print(f"[주문상태조회오류] {e}")
            return {'order_id': order_id, 'status': 'unknown', 'error': str(e)}

    def wait_for_fill(self, order_id: str, timeout: int = 30, poll_interval: float = 1.0):
        """Poll order status until filled or timeout. Returns last status dict."""
        start = time.time()
        while True:
            st = self.get_order_status(order_id)
            status = None
            if isinstance(st, dict):
                status = st.get('status')
            if status in ('filled', 'partial_filled', 'cancelled'):
                return st
            if time.time() - start > timeout:
                return {'order_id': order_id, 'status': 'timeout'}
            time.sleep(poll_interval)

    def get_balance(self):
        # Ensure we have a valid access token (lazy fetch)
        if not self.access_token:
            self.access_token = self.get_access_token()
        # Dry-run: return a simulated balance
        if self.dry_run:
            return {
                'cash': 10000000,
                'positions': []
            }

        url = f"{self.BASE_URL}/uapi/domestic-stock/v1/trading/inquire-balance"
        headers = {
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.appkey,
            "appsecret": self.appsecret,
            "tr_id": "TTTC8434R"
        }
        params = {
            "CANO": os.environ.get('KOREA_ACCOUNT_NO'),
            "ACNT_PRDT_CD": os.environ.get('KOREA_ACCOUNT_PRDT'),
            "AFHR_FLPR_YN": "N",
            "UNPR_DVSN_CD": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN_CD": "00",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": ""
        }
        resp = requests.get(url, headers=headers, params=params)
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"[잔고조회실패] {resp.text}")
            return None

    def monitor_orders(self):
        # 실시간 체결/잔고 모니터링 (REST polling 예시)
        print("[모니터링] 잔고/체결 상태 확인...")
        balance = self.get_balance()
        if balance:
            print(balance)
        else:
            print("잔고 정보 없음")

if __name__ == "__main__":
    api = KoreaInvestmentAPI()
    # 샘플 주문 (실전 계좌/실매매 주의!)
    # api.send_order("005930", 1, 70000, side="buy")
    api.monitor_orders()
