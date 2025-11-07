"""
실시간 자동매매 엔진
- 실시간 데이터 기반 매매 신호 생성
- 리스크 관리 및 포지션 관리  
- 자동 주문 실행
"""
import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
import pandas as pd
import joblib

from .realtime_websocket import KoreaInvestmentWebSocket
from .korea_investment_order import KoreaInvestmentAPI
from .discord_alert import AlertManager

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealTimeTradingEngine:
    """실시간 자동매매 엔진"""
    
    def __init__(self, config_path: str = "config.json"):
        # 설정 로드
        self.config = self._load_config(config_path)
        
        # WebSocket 클라이언트
        self.ws_client = KoreaInvestmentWebSocket()
        
        # REST API 클라이언트  
        self.api_client = KoreaInvestmentAPI()
        
        # 알림 시스템
        self.alert_manager = AlertManager()
        
        # 모델 및 스케일러
        self.model = None
        self.scaler = None
        self._load_models()
        
        # 포지션 관리
        self.positions = {}  # {stock_code: {quantity, avg_price, unrealized_pnl}}
        self.orders = {}     # {order_id: order_info}
        
        # 실시간 데이터 저장
        self.realtime_data = {}  # {stock_code: latest_data}
        self.price_history = {}  # {stock_code: [price_list]}
        
        # 거래 통계
        self.total_trades = 0
        self.total_pnl = 0.0
        self.daily_pnl = 0.0
        
        # 리스크 관리 설정
        self.max_position_size = self.config.get("max_position_size", 10000000)  # 1천만원
        self.max_daily_loss = self.config.get("max_daily_loss", -500000)        # -50만원
        self.stop_loss_rate = self.config.get("stop_loss_rate", -0.03)          # -3%
        self.take_profit_rate = self.config.get("take_profit_rate", 0.05)       # +5%
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """설정 파일 로드"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"설정 파일 없음: {config_path}, 기본 설정 사용")
            return {
                "target_stocks": ["005930", "000660", "207940"],
                "max_position_size": 10000000,
                "max_daily_loss": -500000,
                "stop_loss_rate": -0.03,
                "take_profit_rate": 0.05
            }
    
    def _load_models(self):
        """ML 모델 및 스케일러 로드"""
        try:
            model_path = "models/random_forest_model.joblib"
            scaler_path = "models/scaler.joblib"
            
            if os.path.exists(model_path) and os.path.exists(scaler_path):
                self.model = joblib.load(model_path)
                self.scaler = joblib.load(scaler_path)
                logger.info("ML 모델 로드 완료")
            else:
                logger.warning("ML 모델 파일이 없습니다. 수동 전략만 사용됩니다.")
                
        except Exception as e:
            logger.error(f"모델 로드 실패: {e}")
    
    async def start(self):
        """실시간 거래 엔진 시작"""
        logger.info("실시간 자동매매 엔진 시작...")
        
        try:
            # WebSocket 연결
            await self.ws_client.connect()
            
            # 핸들러 설정
            self.ws_client.set_price_handler(self._handle_price_data)
            self.ws_client.set_orderbook_handler(self._handle_orderbook_data)
            
            # 대상 종목 구독
            target_stocks = self.config.get("target_stocks", ["005930"])
            for stock_code in target_stocks:
                await self.ws_client.subscribe_price(stock_code)
                await self.ws_client.subscribe_orderbook(stock_code)
                logger.info(f"구독 시작: {stock_code}")
            
            # 백그라운드 작업 시작
            await asyncio.gather(
                self.ws_client.listen(),           # 실시간 데이터 수신
                self._risk_management_loop(),      # 리스크 관리
                self._position_monitoring_loop(),  # 포지션 모니터링
            )
            
        except Exception as e:
            logger.error(f"거래 엔진 오류: {e}")
            raise
        finally:
            await self.ws_client.disconnect()
    
    async def _handle_price_data(self, price_data: Dict[str, Any]):
        """실시간 시세 데이터 처리"""
        stock_code = price_data["stock_code"]
        current_price = price_data["current_price"]
        
        # 데이터 저장
        self.realtime_data[stock_code] = price_data
        
        # 가격 히스토리 업데이트
        if stock_code not in self.price_history:
            self.price_history[stock_code] = []
        self.price_history[stock_code].append(current_price)
        
        # 최근 100개 가격만 유지
        if len(self.price_history[stock_code]) > 100:
            self.price_history[stock_code].pop(0)
        
        # 매매 신호 생성
        await self._generate_trading_signal(stock_code, price_data)
        
        logger.debug(f"[{stock_code}] {current_price:,}원 "
                    f"({price_data['change']:+,}, {price_data['change_rate']:+.2f}%)")
    
    async def _handle_orderbook_data(self, orderbook_data: Dict[str, Any]):
        """실시간 호가 데이터 처리"""
        stock_code = orderbook_data["stock_code"]
        
        # 스프레드 계산
        best_ask = orderbook_data["ask_prices"][0]
        best_bid = orderbook_data["bid_prices"][0]
        spread = best_ask - best_bid
        spread_rate = (spread / best_bid) * 100 if best_bid > 0 else 0
        
        logger.debug(f"[{stock_code}] 매도1호가: {best_ask:,}원, "
                    f"매수1호가: {best_bid:,}원, 스프레드: {spread_rate:.2f}%")
    
    async def _generate_trading_signal(self, stock_code: str, price_data: Dict[str, Any]):
        """매매 신호 생성"""
        try:
            # 충분한 데이터가 있는지 확인
            if len(self.price_history.get(stock_code, [])) < 20:
                return
            
            # 기술적 분석 기반 신호
            signal_strength = await self._calculate_technical_signal(stock_code)
            
            # ML 모델 기반 신호 (모델이 있는 경우)
            ml_signal = await self._calculate_ml_signal(stock_code, price_data)
            
            # 종합 신호 생성
            final_signal = self._combine_signals(signal_strength, ml_signal)
            
            # 신호 강도가 임계값을 넘으면 주문 실행
            if final_signal > 0.7:  # 매수 신호
                await self._execute_buy_order(stock_code, price_data["current_price"])
            elif final_signal < -0.7:  # 매도 신호  
                await self._execute_sell_order(stock_code, price_data["current_price"])
                
        except Exception as e:
            logger.error(f"신호 생성 오류 ({stock_code}): {e}")
    
    async def _calculate_technical_signal(self, stock_code: str) -> float:
        """기술적 분석 기반 신호 계산"""
        prices = self.price_history[stock_code]
        
        if len(prices) < 20:
            return 0.0
        
        # 단순 이동평균
        ma5 = sum(prices[-5:]) / 5
        ma20 = sum(prices[-20:]) / 20
        current_price = prices[-1]
        
        signal = 0.0
        
        # 이평선 돌파
        if current_price > ma5 > ma20:
            signal += 0.3
        elif current_price < ma5 < ma20:
            signal -= 0.3
        
        # 단기 모멘텀
        if len(prices) >= 5:
            momentum = (current_price - prices[-5]) / prices[-5]
            signal += momentum * 2  # 모멘텀에 가중치
        
        # RSI (간단 버전)
        if len(prices) >= 14:
            gains = []
            losses = []
            for i in range(1, 14):
                change = prices[-i] - prices[-i-1]
                if change > 0:
                    gains.append(change)
                else:
                    losses.append(-change)
            
            if gains and losses:
                avg_gain = sum(gains) / len(gains) if gains else 0
                avg_loss = sum(losses) / len(losses) if losses else 0
                
                if avg_loss > 0:
                    rs = avg_gain / avg_loss
                    rsi = 100 - (100 / (1 + rs))
                    
                    if rsi < 30:  # 과매도
                        signal += 0.2
                    elif rsi > 70:  # 과매수
                        signal -= 0.2
        
        return max(-1.0, min(1.0, signal))  # -1.0 ~ 1.0 범위로 제한
    
    async def _calculate_ml_signal(self, stock_code: str, price_data: Dict[str, Any]) -> float:
        """ML 모델 기반 신호 계산"""
        if not self.model or not self.scaler:
            return 0.0
        
        try:
            # 피쳐 생성 (간단 버전)
            prices = self.price_history[stock_code]
            if len(prices) < 20:
                return 0.0
            
            features = [
                sum(prices[-5:]) / 5,     # MA5
                sum(prices[-20:]) / 20,   # MA20
                price_data.get("volume", 0) / 1000000,  # Volume (백만주 단위)
                price_data.get("change_rate", 0),       # 등락률
            ]
            
            # 예측
            features_scaled = self.scaler.transform([features])
            prediction_proba = self.model.predict_proba(features_scaled)[0]
            
            # 상승 확률이 높으면 양수, 하락 확률이 높으면 음수
            signal = (prediction_proba[1] - prediction_proba[0])  # 클래스 1(상승) - 클래스 0(하락)
            
            return signal
            
        except Exception as e:
            logger.error(f"ML 신호 계산 오류 ({stock_code}): {e}")
            return 0.0
    
    def _combine_signals(self, technical_signal: float, ml_signal: float) -> float:
        """기술적 분석과 ML 신호를 결합"""
        # 가중 평균 (기술적 분석 70%, ML 30%)
        combined = technical_signal * 0.7 + ml_signal * 0.3
        return max(-1.0, min(1.0, combined))
    
    async def _execute_buy_order(self, stock_code: str, current_price: int):
        """매수 주문 실행"""
        try:
            # 리스크 관리 체크
            if not self._check_risk_limits(stock_code, "buy"):
                return
            
            # 포지션 크기 계산
            position_value = self.max_position_size // 2  # 최대 포지션의 50%
            quantity = position_value // current_price
            
            if quantity < 1:
                logger.warning(f"매수 수량이 너무 적음: {stock_code}")
                return
            
            # 주문 실행
            order_result = self.api_client.send_order(
                symbol=stock_code,
                qty=quantity,
                price=current_price,
                side='buy'
            )
            
            if order_result.get('success'):
                # 포지션 업데이트
                if stock_code not in self.positions:
                    self.positions[stock_code] = {
                        'quantity': 0,
                        'avg_price': 0,
                        'unrealized_pnl': 0
                    }
                
                pos = self.positions[stock_code]
                total_quantity = pos['quantity'] + quantity
                total_value = (pos['quantity'] * pos['avg_price']) + (quantity * current_price)
                pos['avg_price'] = total_value // total_quantity
                pos['quantity'] = total_quantity
                
                self.total_trades += 1
                
                logger.info(f"[매수체결] {stock_code}: {quantity:,}주 @ {current_price:,}원")
                
                # 거래 로그 저장
                trade_data = self._save_trade_log(stock_code, "buy", quantity, current_price)
                
                # 디스코드 알림 전송
                self.alert_manager.notify_trade(trade_data)
                
        except Exception as e:
            logger.error(f"매수 주문 실행 오류 ({stock_code}): {e}")
    
    async def _execute_sell_order(self, stock_code: str, current_price: int):
        """매도 주문 실행"""
        try:
            # 보유 포지션 확인
            if stock_code not in self.positions or self.positions[stock_code]['quantity'] <= 0:
                return
            
            position = self.positions[stock_code]
            sell_quantity = position['quantity'] // 2  # 보유 수량의 50% 매도
            
            if sell_quantity < 1:
                return
            
            # 주문 실행
            order_result = self.api_client.send_order(
                symbol=stock_code,
                qty=sell_quantity,
                price=current_price,
                side='sell'
            )
            
            if order_result.get('success'):
                # 포지션 업데이트
                position['quantity'] -= sell_quantity
                
                # 손익 계산
                pnl = (current_price - position['avg_price']) * sell_quantity
                self.total_pnl += pnl
                self.daily_pnl += pnl
                
                self.total_trades += 1
                
                logger.info(f"[매도체결] {stock_code}: {sell_quantity:,}주 @ {current_price:,}원 "
                           f"(손익: {pnl:+,.0f}원)")
                
                # 거래 로그 저장  
                trade_data = self._save_trade_log(stock_code, "sell", sell_quantity, current_price, pnl)
                
                # 디스코드 알림 전송
                self.alert_manager.notify_trade(trade_data)
                
        except Exception as e:
            logger.error(f"매도 주문 실행 오류 ({stock_code}): {e}")
    
    def _check_risk_limits(self, stock_code: str, side: str) -> bool:
        """리스크 한도 체크"""
        # 일일 손실 한도 체크
        if self.daily_pnl <= self.max_daily_loss:
            logger.warning(f"일일 손실 한도 도달: {self.daily_pnl:,.0f}원")
            return False
        
        # 최대 포지션 크기 체크 (매수의 경우)
        if side == "buy":
            total_position_value = sum(
                pos['quantity'] * pos['avg_price'] 
                for pos in self.positions.values()
            )
            if total_position_value >= self.max_position_size:
                logger.warning(f"최대 포지션 크기 도달: {total_position_value:,.0f}원")
                return False
        
        return True
    
    async def _risk_management_loop(self):
        """리스크 관리 루프"""
        while True:
            try:
                await asyncio.sleep(10)  # 10초마다 실행
                
                for stock_code, position in self.positions.items():
                    if position['quantity'] <= 0:
                        continue
                    
                    current_data = self.realtime_data.get(stock_code)
                    if not current_data:
                        continue
                    
                    current_price = current_data['current_price']
                    avg_price = position['avg_price']
                    
                    # 손익률 계산
                    pnl_rate = (current_price - avg_price) / avg_price
                    
                    # 손절 체크
                    if pnl_rate <= self.stop_loss_rate:
                        logger.warning(f"[손절] {stock_code}: {pnl_rate:.2%}")
                        await self._execute_sell_order(stock_code, current_price)
                    
                    # 익절 체크
                    elif pnl_rate >= self.take_profit_rate:
                        logger.info(f"[익절] {stock_code}: {pnl_rate:.2%}")
                        await self._execute_sell_order(stock_code, current_price)
                        
            except Exception as e:
                logger.error(f"리스크 관리 오류: {e}")
    
    async def _position_monitoring_loop(self):
        """포지션 모니터링 루프"""
        while True:
            try:
                await asyncio.sleep(30)  # 30초마다 실행
                
                # 포지션 현황 출력
                total_unrealized_pnl = 0
                
                for stock_code, position in self.positions.items():
                    if position['quantity'] <= 0:
                        continue
                    
                    current_data = self.realtime_data.get(stock_code)
                    if not current_data:
                        continue
                    
                    current_price = current_data['current_price']
                    unrealized_pnl = (current_price - position['avg_price']) * position['quantity']
                    position['unrealized_pnl'] = unrealized_pnl
                    total_unrealized_pnl += unrealized_pnl
                
                logger.info(f"[포지션현황] 실현손익: {self.total_pnl:+,.0f}원, "
                           f"평가손익: {total_unrealized_pnl:+,.0f}원, "
                           f"총거래: {self.total_trades}회")
                
            except Exception as e:
                logger.error(f"포지션 모니터링 오류: {e}")
    
    def _save_trade_log(self, stock_code: str, side: str, quantity: int, price: int, pnl: float = 0):
        """거래 로그 저장"""
        trade_data = {
            'timestamp': datetime.now().isoformat(),
            'stock_code': stock_code,
            'side': side,
            'quantity': quantity,
            'price': price,
            'pnl': pnl
        }
        
        # JSON 파일에 추가
        log_file = "results/realtime_trade_log.jsonl"
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(trade_data, ensure_ascii=False) + '\n')
        
        return trade_data  # 알림 시스템에서 사용할 수 있도록 반환
    
    async def stop(self):
        """거래 엔진 중지"""
        logger.info("실시간 자동매매 엔진 중지...")
        await self.ws_client.disconnect()


if __name__ == "__main__":
    async def main():
        engine = RealTimeTradingEngine()
        
        try:
            await engine.start()
        except KeyboardInterrupt:
            print("사용자 중단")
        finally:
            await engine.stop()
    
    asyncio.run(main())