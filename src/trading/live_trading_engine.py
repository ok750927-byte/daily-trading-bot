"""
실제 모의거래 시스템 구축
- 한국투자증권 실제 API 연동
- 실시간 주문 처리
- 포지션 관리 시스템
"""
import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import threading
import asyncio
import websocket
import requests
from .approval import manager as approval_manager

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LiveTradingEngine:
    """실제 모의거래 엔진"""

    def __init__(self):
        self.project_root = project_root
        self.config = self.load_config()
        self.secrets = self.load_secrets()

        # 거래 상태
        self.is_trading_active = False
        self.positions = {}  # {종목코드: Position}
        self.orders = {}     # {주문번호: Order}

        # API 연결 상태
        self.access_token = None
        self.token_expires_at = None

        # 리스크 관리
        self.daily_loss_limit = -300000  # 일일 손실 한도 -30만원
        self.daily_profit_target = 500000  # 일일 수익 목표 50만원
        self.max_position_count = 5  # 최대 보유 종목 수

        # 거래 통계
        self.daily_stats = {
            'trades_count': 0,
            'profit_loss': 0,
            'win_trades': 0,
            'lose_trades': 0
        }

        # 실시간 데이터
        self.real_time_prices = {}
        self.market_data_ws = None

    def load_config(self) -> Dict:
        """설정 파일 로드"""
        try:
            config_file = self.project_root / "config.json"
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"설정 파일 로드 실패: {e}")
            return {}

    def load_secrets(self) -> Dict:
        """인증 정보 로드"""
        try:
            secrets_file = self.project_root / "secrets.json"
            with open(secrets_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"인증 정보 로드 실패: {e}")
            return {}

    def get_access_token(self) -> Optional[str]:
        """액세스 토큰 발급"""
        try:
            # 기존 토큰이 유효한지 확인
            if (self.access_token and self.token_expires_at and
                datetime.now() < self.token_expires_at - timedelta(minutes=5)):
                return self.access_token

            # 새 토큰 발급
            url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"

            headers = {
                "content-type": "application/json; charset=utf-8"
            }

            data = {
                "grant_type": "client_credentials",
                "appkey": self.secrets.get("KIS_APP_KEY", ""),
                "appsecret": self.secrets.get("KIS_APP_SECRET", "")
            }

            response = requests.post(url, headers=headers, json=data)

            if response.status_code == 200:
                result = response.json()
                self.access_token = result.get("access_token")

                # 토큰 만료 시간 설정 (24시간 - 5분)
                self.token_expires_at = datetime.now() + timedelta(hours=23, minutes=55)

                logger.info("액세스 토큰 발급 성공")
                return self.access_token
            else:
                logger.error(f"토큰 발급 실패: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"토큰 발급 중 오류: {e}")
            return None

    def get_balance(self) -> Dict:
        """계좌 잔고 조회"""
        try:
            token = self.get_access_token()
            if not token:
                return {}

            url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/trading/inquire-balance"

            headers = {
                "content-type": "application/json; charset=utf-8",
                "authorization": f"Bearer {token}",
                "appkey": self.secrets.get("KIS_APP_KEY", ""),
                "appsecret": self.secrets.get("KIS_APP_SECRET", ""),
                "tr_id": "TTTC8434R",  # 모의투자 잔고조회
                "custtype": "P"
            }

            params = {
                "CANO": self.secrets.get("ACCOUNT_NUMBER", "")[:8],
                "ACNT_PRDT_CD": self.secrets.get("ACCOUNT_NUMBER", "")[8:],
                "AFHR_FLPR_YN": "N",
                "OFL_YN": "",
                "INQR_DVSN": "02",
                "UNPR_DVSN": "01",
                "FUND_STTL_ICLD_YN": "N",
                "FNCG_AMT_AUTO_RDPT_YN": "N",
                "PRCS_DVSN": "01",
                "CTX_AREA_FK100": "",
                "CTX_AREA_NK100": ""
            }

            response = requests.get(url, headers=headers, params=params)

            if response.status_code == 200:
                result = response.json()
                logger.info("잔고 조회 성공")
                return result
            else:
                logger.error(f"잔고 조회 실패: {response.status_code} - {response.text}")
                return {}

        except Exception as e:
            logger.error(f"잔고 조회 중 오류: {e}")
            return {}

    def get_current_price(self, symbol: str) -> Optional[float]:
        """현재가 조회"""
        try:
            # 실시간 데이터가 있으면 사용
            if symbol in self.real_time_prices:
                return float(self.real_time_prices[symbol])

            token = self.get_access_token()
            if not token:
                return None

            url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-price"

            headers = {
                "content-type": "application/json; charset=utf-8",
                "authorization": f"Bearer {token}",
                "appkey": self.secrets.get("KIS_APP_KEY", ""),
                "appsecret": self.secrets.get("KIS_APP_SECRET", ""),
                "tr_id": "FHKST01010100"
            }

            params = {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": symbol
            }

            response = requests.get(url, headers=headers, params=params)

            if response.status_code == 200:
                result = response.json()
                output = result.get("output", {})
                current_price = float(output.get("stck_prpr", 0))

                # 실시간 데이터에 업데이트
                self.real_time_prices[symbol] = current_price

                return current_price
            else:
                logger.error(f"현재가 조회 실패 {symbol}: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"현재가 조회 중 오류 {symbol}: {e}")
            return None

    def place_order(self, symbol: str, order_type: str, quantity: int, price: Optional[float] = None) -> Optional[str]:
        """주문 실행"""
        try:
            # If operator approval is required by config, submit a pending approval
            require_approval = self.config.get('trading', {}).get('require_operator_approval', False)
            approval_timeout = int(self.config.get('trading', {}).get('approval_timeout_seconds', 300))

            if require_approval and not os.environ.get('DRY_RUN'):
                pending = {
                    'symbol': symbol,
                    'order_type': order_type,
                    'quantity': quantity,
                    'price': price,
                    'requested_at': datetime.now().isoformat()
                }
                approval_id = approval_manager.submit(pending)
                logger.info(f"주문 승인 요청 생성 (approval_id={approval_id}) - 운영자 승인이 필요합니다.")

                # Poll for approval until timeout
                start = time.time()
                while time.time() - start < approval_timeout:
                    status = approval_manager.check_approval(approval_id)
                    if status == 'approved':
                        logger.info(f"approval_id={approval_id} 승인됨. 주문 진행")
                        break
                    if status == 'rejected':
                        logger.warning(f"approval_id={approval_id} 거부됨. 주문 취소")
                        return None
                    time.sleep(1)
                else:
                    logger.warning(f"approval_id={approval_id} 승인 대기 시간 초과({approval_timeout}s). 주문 취소")
                    return None

            token = self.get_access_token()
            if not token:
                return None

            # 모의투자 주문 URL
            url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/trading/order-cash"

            # 주문 타입별 설정
            if order_type == "BUY":
                tr_id = "VTTC0802U"  # 모의투자 매수
                ord_dvsn = "01" if price else "01"  # 지정가 or 시장가
            elif order_type == "SELL":
                tr_id = "VTTC0801U"  # 모의투자 매도
                ord_dvsn = "01" if price else "01"  # 지정가 or 시장가
            else:
                logger.error(f"지원하지 않는 주문 타입: {order_type}")
                return None

            headers = {
                "content-type": "application/json; charset=utf-8",
                "authorization": f"Bearer {token}",
                "appkey": self.secrets.get("KIS_APP_KEY", ""),
                "appsecret": self.secrets.get("KIS_APP_SECRET", ""),
                "tr_id": tr_id,
                "custtype": "P",
                "hashkey": ""  # 실제로는 해시키 생성 필요
            }

            # 시장가 주문일 경우 현재가로 설정
            if not price:
                price = self.get_current_price(symbol)
                if not price:
                    logger.error(f"현재가 조회 실패로 주문 취소: {symbol}")
                    return None

            data = {
                "CANO": self.secrets.get("ACCOUNT_NUMBER", "")[:8],
                "ACNT_PRDT_CD": self.secrets.get("ACCOUNT_NUMBER", "")[8:],
                "PDNO": symbol,
                "ORD_DVSN": ord_dvsn,
                "ORD_QTY": str(quantity),
                "ORD_UNPR": str(int(price))
            }

            logger.info(f"주문 실행: {order_type} {symbol} {quantity}주 @ {price:,.0f}원")

            response = requests.post(url, headers=headers, json=data)

            if response.status_code == 200:
                result = response.json()
                rt_cd = result.get("rt_cd", "")

                if rt_cd == "0":
                    order_number = result.get("output", {}).get("KRX_FWDG_ORD_ORGNO", "")
                    logger.info(f"주문 성공: 주문번호 {order_number}")

                    # 주문 정보 저장
                    order_info = {
                        'order_number': order_number,
                        'symbol': symbol,
                        'order_type': order_type,
                        'quantity': quantity,
                        'price': price,
                        'timestamp': datetime.now().isoformat(),
                        'status': 'SUBMITTED'
                    }

                    self.orders[order_number] = order_info
                    self.save_order_log(order_info)

                    return order_number
                else:
                    error_msg = result.get("msg1", "Unknown error")
                    logger.error(f"주문 실패: {error_msg}")
                    return None
            else:
                logger.error(f"주문 API 호출 실패: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"주문 실행 중 오류: {e}")
            return None

    def check_order_status(self, order_number: str) -> Optional[Dict]:
        """주문 상태 확인"""
        try:
            token = self.get_access_token()
            if not token:
                return None

            url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/trading/inquire-daily-ccld"

            headers = {
                "content-type": "application/json; charset=utf-8",
                "authorization": f"Bearer {token}",
                "appkey": self.secrets.get("KIS_APP_KEY", ""),
                "appsecret": self.secrets.get("KIS_APP_SECRET", ""),
                "tr_id": "VTTC8001R",  # 모의투자 주문체결조회
                "custtype": "P"
            }

            params = {
                "CANO": self.secrets.get("ACCOUNT_NUMBER", "")[:8],
                "ACNT_PRDT_CD": self.secrets.get("ACCOUNT_NUMBER", "")[8:],
                "INQR_STRT_DT": datetime.now().strftime("%Y%m%d"),
                "INQR_END_DT": datetime.now().strftime("%Y%m%d"),
                "SLL_BUY_DVSN_CD": "00",  # 전체
                "INQR_DVSN": "00",
                "PDNO": "",
                "CCLD_DVSN": "00",  # 전체
                "ORD_GNO_BRNO": "",
                "ODNO": "",
                "INQR_DVSN_3": "00",
                "INQR_DVSN_1": "",
                "CTX_AREA_FK100": "",
                "CTX_AREA_NK100": ""
            }

            response = requests.get(url, headers=headers, params=params)

            if response.status_code == 200:
                result = response.json()
                # 특정 주문 찾기 (실제로는 더 정교한 매칭 필요)
                return result
            else:
                logger.error(f"주문 상태 조회 실패: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"주문 상태 확인 중 오류: {e}")
            return None

    def calculate_position_size(self, symbol: str, confidence: float, current_price: float) -> int:
        """포지션 크기 계산"""
        try:
            # 잔고 조회
            balance_info = self.get_balance()
            if not balance_info:
                return 0

            # 가용 현금 계산 (실제 API 응답 구조에 맞게 수정 필요)
            available_cash = 1000000  # 임시값 - 실제로는 API에서 파싱

            # 최대 투자 비율 (신뢰도에 따라 조정)
            max_investment_ratio = 0.2 * confidence  # 최대 20% * 신뢰도

            # 투자 가능 금액
            investment_amount = available_cash * max_investment_ratio

            # 수량 계산
            quantity = int(investment_amount / current_price)

            # 최소/최대 수량 제한
            min_quantity = 1
            max_quantity = 1000

            return max(min_quantity, min(quantity, max_quantity))

        except Exception as e:
            logger.error(f"포지션 크기 계산 오류: {e}")
            return 0

    def execute_trading_signal(self, signal: Dict):
        """거래 신호 실행"""
        try:
            symbol = signal.get('code', '')
            prediction = signal.get('prediction', 0.5)
            confidence = signal.get('confidence', 0.5)

            if not symbol:
                return

            # 현재가 조회
            current_price = self.get_current_price(symbol)
            if not current_price:
                logger.warning(f"현재가 조회 실패: {symbol}")
                return

            # 거래 신호 판단
            if prediction > 0.7 and confidence > 0.8:  # 강한 매수 신호
                # 이미 보유 중인지 확인
                if symbol in self.positions:
                    logger.info(f"이미 보유 중인 종목: {symbol}")
                    return

                # 최대 보유 종목 수 체크
                if len(self.positions) >= self.max_position_count:
                    logger.info("최대 보유 종목 수 도달")
                    return

                # 포지션 크기 계산
                quantity = self.calculate_position_size(symbol, confidence, current_price)

                if quantity > 0:
                    # 매수 주문 실행
                    order_number = self.place_order(symbol, "BUY", quantity, current_price)

                    if order_number:
                        # 포지션 정보 저장
                        position = {
                            'symbol': symbol,
                            'quantity': quantity,
                            'avg_price': current_price,
                            'entry_time': datetime.now().isoformat(),
                            'stop_loss': current_price * 0.97,  # 3% 손절
                            'take_profit': current_price * 1.05,  # 5% 익절
                            'confidence': confidence
                        }

                        self.positions[symbol] = position
                        self.save_position_log(position)

                        logger.info(f"포지션 진입: {symbol} {quantity}주 @ {current_price:,.0f}원")

            elif prediction < 0.3 and confidence > 0.8:  # 강한 매도 신호
                # 보유 중인 종목인지 확인
                if symbol in self.positions:
                    position = self.positions[symbol]
                    quantity = position['quantity']

                    # 매도 주문 실행
                    order_number = self.place_order(symbol, "SELL", quantity, current_price)

                    if order_number:
                        # 손익 계산
                        entry_price = position['avg_price']
                        pnl = (current_price - entry_price) * quantity

                        # 통계 업데이트
                        self.daily_stats['trades_count'] += 1
                        self.daily_stats['profit_loss'] += pnl

                        if pnl > 0:
                            self.daily_stats['win_trades'] += 1
                        else:
                            self.daily_stats['lose_trades'] += 1

                        logger.info(f"포지션 청산: {symbol} {quantity}주 @ {current_price:,.0f}원 (손익: {pnl:,.0f}원)")

                        # 포지션 제거
                        del self.positions[symbol]

        except Exception as e:
            logger.error(f"거래 신호 실행 중 오류: {e}")

    def monitor_positions(self):
        """포지션 모니터링 (손절/익절)"""
        try:
            positions_to_close = []

            for symbol, position in self.positions.items():
                current_price = self.get_current_price(symbol)
                if not current_price:
                    continue

                stop_loss = position['stop_loss']
                take_profit = position['take_profit']

                # 손절 체크
                if current_price <= stop_loss:
                    logger.info(f"손절 실행: {symbol} @ {current_price:,.0f}원")
                    positions_to_close.append((symbol, "STOP_LOSS"))

                # 익절 체크
                elif current_price >= take_profit:
                    logger.info(f"익절 실행: {symbol} @ {current_price:,.0f}원")
                    positions_to_close.append((symbol, "TAKE_PROFIT"))

            # 포지션 청산 실행
            for symbol, reason in positions_to_close:
                position = self.positions[symbol]
                quantity = position['quantity']
                current_price = self.get_current_price(symbol)

                if current_price:
                    order_number = self.place_order(symbol, "SELL", quantity, current_price)

                    if order_number:
                        # 손익 계산 및 통계 업데이트
                        entry_price = position['avg_price']
                        pnl = (current_price - entry_price) * quantity

                        self.daily_stats['trades_count'] += 1
                        self.daily_stats['profit_loss'] += pnl

                        if pnl > 0:
                            self.daily_stats['win_trades'] += 1
                        else:
                            self.daily_stats['lose_trades'] += 1

                        logger.info(f"포지션 청산 완료: {symbol} ({reason}) 손익: {pnl:,.0f}원")

                        # 포지션 제거
                        del self.positions[symbol]

        except Exception as e:
            logger.error(f"포지션 모니터링 중 오류: {e}")

    def check_risk_limits(self) -> bool:
        """리스크 한도 확인"""
        try:
            current_pnl = self.daily_stats['profit_loss']

            # 일일 손실 한도 체크
            if current_pnl <= self.daily_loss_limit:
                logger.warning(f"일일 손실 한도 도달: {current_pnl:,.0f}원")
                self.emergency_close_all_positions("DAILY_LOSS_LIMIT")
                return False

            # 일일 수익 목표 달성 체크
            if current_pnl >= self.daily_profit_target:
                logger.info(f"일일 수익 목표 달성: {current_pnl:,.0f}원")
                self.emergency_close_all_positions("DAILY_PROFIT_TARGET")
                return False

            return True

        except Exception as e:
            logger.error(f"리스크 한도 확인 중 오류: {e}")
            return True

    def emergency_close_all_positions(self, reason: str):
        """비상 시 모든 포지션 청산"""
        logger.warning(f"비상 청산 실행: {reason}")

        for symbol, position in list(self.positions.items()):
            try:
                quantity = position['quantity']
                current_price = self.get_current_price(symbol)

                if current_price:
                    order_number = self.place_order(symbol, "SELL", quantity, current_price)

                    if order_number:
                        logger.info(f"비상 청산: {symbol} {quantity}주")
                        del self.positions[symbol]

            except Exception as e:
                logger.error(f"비상 청산 실패 {symbol}: {e}")

        # 거래 중단
        self.is_trading_active = False

    def save_order_log(self, order_info: Dict):
        """주문 로그 저장"""
        try:
            log_file = self.project_root / "results" / "live_order_log.jsonl"
            log_file.parent.mkdir(exist_ok=True)

            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(order_info, ensure_ascii=False) + '\n')

        except Exception as e:
            logger.error(f"주문 로그 저장 실패: {e}")

    def save_position_log(self, position_info: Dict):
        """포지션 로그 저장"""
        try:
            log_file = self.project_root / "results" / "live_position_log.jsonl"
            log_file.parent.mkdir(exist_ok=True)

            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(position_info, ensure_ascii=False) + '\n')

        except Exception as e:
            logger.error(f"포지션 로그 저장 실패: {e}")

    def start_live_trading(self):
        """실시간 거래 시작"""
        logger.info("=== 실시간 모의거래 시작 ===")

        # 초기 설정 확인
        if not self.secrets.get("KIS_APP_KEY"):
            logger.error("API 키가 설정되지 않았습니다")
            return

        # 토큰 발급 확인
        if not self.get_access_token():
            logger.error("액세스 토큰 발급 실패")
            return

        # 잔고 확인
        balance = self.get_balance()
        if not balance:
            logger.error("잔고 조회 실패")
            return

        logger.info("실시간 거래 시스템 준비 완료")
        self.is_trading_active = True

        # 메인 거래 루프 시작
        self.main_trading_loop()

    def main_trading_loop(self):
        """메인 거래 루프"""
        logger.info("메인 거래 루프 시작")

        while self.is_trading_active:
            try:
                # 1. 리스크 한도 확인
                if not self.check_risk_limits():
                    break

                # 2. 포지션 모니터링
                self.monitor_positions()

                # 3. 새로운 거래 신호 처리 (ML 예측 결과 활용)
                # 실제로는 ML 모델에서 신호를 받아와야 함
                self.process_ml_signals()

                # 4. 상태 로깅
                self.log_trading_status()

                # 5. 잠시 대기
                time.sleep(10)  # 10초마다 실행

            except KeyboardInterrupt:
                logger.info("사용자 중단 신호 받음")
                break
            except Exception as e:
                logger.error(f"거래 루프 오류: {e}")
                time.sleep(30)  # 오류 시 30초 대기

        logger.info("실시간 거래 종료")

    def process_ml_signals(self):
        """ML 신호 처리"""
        try:
            # 실제로는 ML 모델에서 예측 결과를 가져와야 함
            # 여기서는 더미 신호 생성
            test_symbols = ['005930', '000660', '035420']  # 삼성전자, SK하이닉스, NAVER

            for symbol in test_symbols:
                # 더미 신호 (실제로는 ML 모델 결과 사용)
                dummy_signal = {
                    'code': symbol,
                    'prediction': 0.6,  # 중립적 신호
                    'confidence': 0.7,
                    'timestamp': datetime.now().isoformat()
                }

                # 거래 신호 실행은 주의해서 처리 (실제 돈이 움직임)
                # self.execute_trading_signal(dummy_signal)

        except Exception as e:
            logger.error(f"ML 신호 처리 중 오류: {e}")

    def log_trading_status(self):
        """거래 상태 로깅"""
        try:
            status = {
                'timestamp': datetime.now().isoformat(),
                'is_active': self.is_trading_active,
                'positions_count': len(self.positions),
                'daily_stats': self.daily_stats.copy(),
                'positions': {k: v for k, v in self.positions.items()}
            }

            # 상태 로그 저장
            status_file = self.project_root / "results" / "live_trading_status.jsonl"
            status_file.parent.mkdir(exist_ok=True)

            with open(status_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(status, ensure_ascii=False) + '\n')

            # 주기적 상태 출력
            if self.daily_stats['trades_count'] % 5 == 0 or len(self.positions) > 0:
                logger.info(f"거래 현황 - 포지션: {len(self.positions)}개, "
                           f"거래수: {self.daily_stats['trades_count']}건, "
                           f"손익: {self.daily_stats['profit_loss']:,.0f}원")

        except Exception as e:
            logger.error(f"상태 로깅 오류: {e}")

def main():
    """메인 실행 함수"""
    print("🚀 실시간 모의거래 엔진")
    print("=" * 50)

    engine = LiveTradingEngine()

    print("⚠️  주의: 이 시스템은 실제 모의거래 API를 사용합니다.")
    print("실제 거래 전에 충분한 테스트와 검증이 필요합니다.")
    print()

    confirm = input("모의거래를 시작하시겠습니까? (y/N): ").strip().lower()

    if confirm == 'y':
        try:
            engine.start_live_trading()
        except KeyboardInterrupt:
            print("\n거래 시스템 종료")
        except Exception as e:
            print(f"시스템 오류: {e}")
    else:
        print("거래 시스템 시작 취소")

if __name__ == "__main__":
    main()
