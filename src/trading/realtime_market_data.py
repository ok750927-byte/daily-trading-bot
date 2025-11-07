"""
실시간 시장 데이터 수신 시스템
WebSocket을 통한 실시간 가격/호가 데이터 처리
"""
import os
import sys
import json
import time
import logging
import asyncio
import websocket
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Callable, Tuple
import requests
import queue

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MarketDataReceiver:
    """실시간 시장 데이터 수신기"""
    
    def __init__(self):
        self.project_root = project_root
        self.secrets = self.load_secrets()
        
        # WebSocket 연결
        self.ws = None
        self.ws_url = "ws://ops.koreainvestment.com:21000"  # 모의투자용
        
        # 데이터 저장소
        self.real_time_data = {}
        self.price_callbacks = []
        
        # 구독 종목
        self.subscribed_symbols = set()
        
        # 데이터 큐
        self.data_queue = queue.Queue()
        
        # 상태
        self.is_connected = False
        self.reconnect_count = 0
        
    def load_secrets(self) -> Dict:
        """인증 정보 로드"""
        try:
            secrets_file = self.project_root / "secrets.json"
            with open(secrets_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"인증 정보 로드 실패: {e}")
            return {}
    
    def add_price_callback(self, callback: Callable):
        """가격 변동 콜백 추가"""
        self.price_callbacks.append(callback)
    
    def on_message(self, ws, message):
        """WebSocket 메시지 수신"""
        try:
            # 실제 메시지 파싱 (KIS API 문서 참조)
            if message.startswith('0|'):
                # 실시간 체결가 데이터
                parts = message.split('|')
                if len(parts) >= 4:
                    symbol = parts[1]
                    price = float(parts[2]) if parts[2] else 0
                    volume = int(parts[3]) if parts[3] else 0
                    
                    # 데이터 저장
                    data = {
                        'symbol': symbol,
                        'price': price,
                        'volume': volume,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    self.real_time_data[symbol] = data
                    
                    # 콜백 실행
                    for callback in self.price_callbacks:
                        try:
                            callback(data)
                        except Exception as e:
                            logger.error(f"콜백 실행 오류: {e}")
                    
                    # 큐에 추가
                    self.data_queue.put(data)
                    
        except Exception as e:
            logger.error(f"메시지 처리 오류: {e}")
    
    def on_error(self, ws, error):
        """WebSocket 오류"""
        logger.error(f"WebSocket 오류: {error}")
        self.is_connected = False
    
    def on_close(self, ws, close_status_code, close_msg):
        """WebSocket 연결 종료"""
        logger.info("WebSocket 연결 종료")
        self.is_connected = False
        
        # 자동 재연결
        if self.reconnect_count < 5:
            logger.info(f"재연결 시도 {self.reconnect_count + 1}/5")
            time.sleep(5)
            self.connect()
    
    def on_open(self, ws):
        """WebSocket 연결 성공"""
        logger.info("WebSocket 연결 성공")
        self.is_connected = True
        self.reconnect_count = 0
        
        # 기존 구독 종목 재구독
        for symbol in self.subscribed_symbols:
            self.subscribe_symbol(symbol)
    
    def connect(self):
        """WebSocket 연결"""
        try:
            # 접속키 발급
            access_token = self.get_websocket_access_key()
            if not access_token:
                logger.error("WebSocket 접속키 발급 실패")
                return False
            
            # WebSocket 연결
            websocket.enableTrace(True)
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close,
                on_open=self.on_open
            )
            
            # 별도 스레드에서 실행
            wst = threading.Thread(target=self.ws.run_forever)
            wst.daemon = True
            wst.start()
            
            return True
            
        except Exception as e:
            logger.error(f"WebSocket 연결 실패: {e}")
            return False
    
    def get_websocket_access_key(self) -> Optional[str]:
        """WebSocket 접속키 발급"""
        try:
            url = "https://openapi.koreainvestment.com:9443/oauth2/Approval"
            
            headers = {
                "content-type": "application/json; charset=utf-8"
            }
            
            data = {
                "grant_type": "client_credentials",
                "appkey": self.secrets.get("KIS_APP_KEY", ""),
                "secretkey": self.secrets.get("KIS_APP_SECRET", "")
            }
            
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                result = response.json()
                access_key = result.get("approval_key")
                logger.info("WebSocket 접속키 발급 성공")
                return access_key
            else:
                logger.error(f"접속키 발급 실패: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"접속키 발급 중 오류: {e}")
            return None
    
    def subscribe_symbol(self, symbol: str, tr_type: str = "1"):
        """종목 구독"""
        try:
            if not self.is_connected:
                logger.warning("WebSocket 연결되지 않음")
                return False
            
            # 구독 메시지 생성
            subscribe_msg = {
                "header": {
                    "approval_key": self.get_websocket_access_key(),
                    "custtype": "P",
                    "tr_type": tr_type,  # 1: 등록, 2: 해제
                    "content-type": "utf-8"
                },
                "body": {
                    "input": {
                        "tr_id": "H0STCNT0",  # 실시간 체결통보
                        "tr_key": symbol
                    }
                }
            }
            
            # 메시지 전송
            self.ws.send(json.dumps(subscribe_msg))
            
            if tr_type == "1":
                self.subscribed_symbols.add(symbol)
                logger.info(f"종목 구독: {symbol}")
            else:
                self.subscribed_symbols.discard(symbol)
                logger.info(f"종목 구독 해제: {symbol}")
            
            return True
            
        except Exception as e:
            logger.error(f"종목 구독 실패 {symbol}: {e}")
            return False
    
    def unsubscribe_symbol(self, symbol: str):
        """종목 구독 해제"""
        return self.subscribe_symbol(symbol, tr_type="2")
    
    def get_latest_price(self, symbol: str) -> Optional[Dict]:
        """최신 가격 데이터 조회"""
        return self.real_time_data.get(symbol)
    
    def start_data_processor(self):
        """데이터 처리기 시작"""
        def process_data():
            while True:
                try:
                    # 큐에서 데이터 가져오기
                    data = self.data_queue.get(timeout=1)
                    
                    # 데이터 저장
                    self.save_market_data(data)
                    
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"데이터 처리 오류: {e}")
        
        # 별도 스레드에서 실행
        processor_thread = threading.Thread(target=process_data)
        processor_thread.daemon = True
        processor_thread.start()
    
    def save_market_data(self, data: Dict):
        """시장 데이터 저장"""
        try:
            # 일별 파일로 저장
            date_str = datetime.now().strftime("%Y%m%d")
            data_file = self.project_root / "data" / "realtime" / f"market_data_{date_str}.jsonl"
            data_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(data_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
                
        except Exception as e:
            logger.error(f"시장 데이터 저장 실패: {e}")

class AdvancedTradingSignals:
    """고급 거래 신호 생성기"""
    
    def __init__(self, market_receiver: MarketDataReceiver):
        self.market_receiver = market_receiver
        self.price_history = {}  # {symbol: [prices...]}
        self.signals = {}
        
        # 기술적 지표 설정
        self.ma_periods = [5, 10, 20]  # 이동평균 기간
        self.rsi_period = 14
        self.bb_period = 20
        
        # 신호 콜백
        self.signal_callbacks = []
    
    def add_signal_callback(self, callback: Callable):
        """신호 콜백 추가"""
        self.signal_callbacks.append(callback)
    
    def on_price_update(self, data: Dict):
        """가격 업데이트 처리"""
        try:
            symbol = data['symbol']
            price = data['price']
            
            # 가격 히스토리 업데이트
            if symbol not in self.price_history:
                self.price_history[symbol] = []
            
            self.price_history[symbol].append(price)
            
            # 최대 1000개 데이터만 유지
            if len(self.price_history[symbol]) > 1000:
                self.price_history[symbol] = self.price_history[symbol][-1000:]
            
            # 기술적 분석 수행
            signal = self.analyze_technical_indicators(symbol)
            
            if signal:
                # 신호 콜백 실행
                for callback in self.signal_callbacks:
                    try:
                        callback(signal)
                    except Exception as e:
                        logger.error(f"신호 콜백 오류: {e}")
                        
        except Exception as e:
            logger.error(f"가격 업데이트 처리 오류: {e}")
    
    def analyze_technical_indicators(self, symbol: str) -> Optional[Dict]:
        """기술적 지표 분석"""
        try:
            prices = self.price_history.get(symbol, [])
            if len(prices) < 20:  # 최소 20개 데이터 필요
                return None
            
            current_price = prices[-1]
            
            # 이동평균 계산
            ma5 = sum(prices[-5:]) / 5 if len(prices) >= 5 else current_price
            ma10 = sum(prices[-10:]) / 10 if len(prices) >= 10 else current_price
            ma20 = sum(prices[-20:]) / 20 if len(prices) >= 20 else current_price
            
            # RSI 계산 (단순화된 버전)
            rsi = self.calculate_rsi(prices)
            
            # 볼린저 밴드
            bb_upper, bb_lower = self.calculate_bollinger_bands(prices)
            
            # 신호 생성
            signal_strength = 0.5  # 중립
            
            # 이동평균 신호
            if current_price > ma5 > ma10 > ma20:
                signal_strength += 0.2  # 상승 신호
            elif current_price < ma5 < ma10 < ma20:
                signal_strength -= 0.2  # 하락 신호
            
            # RSI 신호
            if rsi < 30:
                signal_strength += 0.15  # 과매도
            elif rsi > 70:
                signal_strength -= 0.15  # 과매수
            
            # 볼린저 밴드 신호
            if current_price < bb_lower:
                signal_strength += 0.1  # 매수 신호
            elif current_price > bb_upper:
                signal_strength -= 0.1  # 매도 신호
            
            # 신호 강도 정규화
            signal_strength = max(0, min(1, signal_strength))
            
            # 신뢰도 계산 (데이터 양과 신호 일관성 기반)
            confidence = min(0.9, len(prices) / 100)
            
            signal = {
                'symbol': symbol,
                'signal_strength': signal_strength,
                'confidence': confidence,
                'current_price': current_price,
                'ma5': ma5,
                'ma10': ma10,
                'ma20': ma20,
                'rsi': rsi,
                'bb_upper': bb_upper,
                'bb_lower': bb_lower,
                'timestamp': datetime.now().isoformat()
            }
            
            return signal
            
        except Exception as e:
            logger.error(f"기술적 분석 오류 {symbol}: {e}")
            return None
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """RSI 계산"""
        try:
            if len(prices) < period + 1:
                return 50  # 중립값
            
            gains = []
            losses = []
            
            for i in range(1, len(prices)):
                change = prices[i] - prices[i-1]
                if change > 0:
                    gains.append(change)
                    losses.append(0)
                else:
                    gains.append(0)
                    losses.append(abs(change))
            
            if len(gains) < period:
                return 50
            
            avg_gain = sum(gains[-period:]) / period
            avg_loss = sum(losses[-period:]) / period
            
            if avg_loss == 0:
                return 100
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
            
        except Exception:
            return 50
    
    def calculate_bollinger_bands(self, prices: List[float], period: int = 20, std_dev: float = 2.0) -> Tuple[float, float]:
        """볼린저 밴드 계산"""
        try:
            if len(prices) < period:
                current_price = prices[-1] if prices else 0
                return current_price * 1.02, current_price * 0.98
            
            recent_prices = prices[-period:]
            mean = sum(recent_prices) / period
            
            # 표준편차 계산
            variance = sum((p - mean) ** 2 for p in recent_prices) / period
            std = variance ** 0.5
            
            upper_band = mean + (std_dev * std)
            lower_band = mean - (std_dev * std)
            
            return upper_band, lower_band
            
        except Exception:
            current_price = prices[-1] if prices else 0
            return current_price * 1.02, current_price * 0.98

class RealTimeTrader:
    """실시간 거래 통합 시스템"""
    
    def __init__(self):
        self.market_receiver = MarketDataReceiver()
        self.signal_generator = AdvancedTradingSignals(self.market_receiver)
        
        # 거래 엔진 (실제로는 live_trading_engine.py에서 가져와야 함)
        self.trading_engine = None
        
        # 감시 종목
        self.watch_list = ['005930', '000660', '035420', '035720', '051910']  # 대형주 5개
        
    def start(self):
        """실시간 거래 시작"""
        logger.info("실시간 거래 시스템 시작")
        
        # 콜백 등록
        self.market_receiver.add_price_callback(self.signal_generator.on_price_update)
        self.signal_generator.add_signal_callback(self.on_trading_signal)
        
        # 시장 데이터 수신 시작
        if self.market_receiver.connect():
            # 데이터 처리기 시작
            self.market_receiver.start_data_processor()
            
            # 감시 종목 구독
            for symbol in self.watch_list:
                self.market_receiver.subscribe_symbol(symbol)
            
            logger.info(f"감시 종목 구독 완료: {self.watch_list}")
            
            # 메인 루프
            self.main_loop()
        else:
            logger.error("시장 데이터 연결 실패")
    
    def on_trading_signal(self, signal: Dict):
        """거래 신호 처리"""
        try:
            symbol = signal['symbol']
            signal_strength = signal['signal_strength']
            confidence = signal['confidence']
            
            logger.info(f"거래 신호 - {symbol}: 강도={signal_strength:.3f}, 신뢰도={confidence:.3f}")
            
            # 강한 신호만 처리
            if confidence > 0.7:
                if signal_strength > 0.7:
                    logger.info(f"매수 신호: {symbol}")
                    # 실제 거래 실행은 주의 깊게 처리
                    # self.trading_engine.execute_buy_order(symbol, signal_strength, confidence)
                elif signal_strength < 0.3:
                    logger.info(f"매도 신호: {symbol}")
                    # self.trading_engine.execute_sell_order(symbol, signal_strength, confidence)
                    
        except Exception as e:
            logger.error(f"거래 신호 처리 오류: {e}")
    
    def main_loop(self):
        """메인 실행 루프"""
        try:
            while True:
                # 상태 체크
                if not self.market_receiver.is_connected:
                    logger.warning("시장 데이터 연결 끊어짐")
                    time.sleep(5)
                    continue
                
                # 주기적 상태 출력
                logger.info("실시간 거래 시스템 동작 중...")
                
                time.sleep(30)  # 30초마다 상태 체크
                
        except KeyboardInterrupt:
            logger.info("시스템 종료 신호 받음")
        except Exception as e:
            logger.error(f"메인 루프 오류: {e}")

def main():
    """메인 실행"""
    print("📊 실시간 시장 데이터 거래 시스템")
    print("=" * 50)
    
    trader = RealTimeTrader()
    
    try:
        trader.start()
    except KeyboardInterrupt:
        print("\n시스템 종료")
    except Exception as e:
        print(f"시스템 오류: {e}")

if __name__ == "__main__":
    main()