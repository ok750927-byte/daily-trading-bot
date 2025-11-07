"""
실시간 자동매매 시뮬레이션
- 과거 데이터를 이용한 백테스팅
- 실시간 엔진의 동작 테스트
"""
import asyncio
import json
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import logging

# 프로젝트 루트 경로 설정
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.preprocessing.data_preprocessor import _safe_read_table

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TradingSimulator:
    """거래 시뮬레이터"""

    def __init__(self, initial_balance: int = 10000000):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.positions = {}
        self.trades = []
        self.total_pnl = 0.0

        # 거래 설정
        self.max_position_size = initial_balance // 5  # 최대 포지션: 총 자본의 20%
        self.stop_loss_rate = -0.03  # 손절: -3%
        self.take_profit_rate = 0.05  # 익절: +5%

    def get_technical_signal(self, prices: list) -> float:
        """기술적 분석 신호 생성 (간단 버전)"""
        if len(prices) < 20:
            return 0.0

        # 이동평균
        ma5 = np.mean(prices[-5:])
        ma20 = np.mean(prices[-20:])
        current_price = prices[-1]

        signal = 0.0

        # 이평선 돌파
        if current_price > ma5 > ma20:
            signal += 0.4
        elif current_price < ma5 < ma20:
            signal -= 0.4

        # 단기 모멘텀
        if len(prices) >= 3:
            momentum = (current_price - prices[-3]) / prices[-3]
            signal += momentum * 3

        # RSI
        if len(prices) >= 14:
            deltas = np.diff(prices[-14:])
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)

            avg_gain = np.mean(gains) if len(gains) > 0 else 0
            avg_loss = np.mean(losses) if len(losses) > 0 else 0

            if avg_loss > 0:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))

                if rsi < 30:  # 과매도
                    signal += 0.3
                elif rsi > 70:  # 과매수
                    signal -= 0.3

        return max(-1.0, min(1.0, signal))

    def execute_trade(self, stock_code: str, signal: float, current_price: int, timestamp: str):
        """거래 실행"""
        # 강한 매수 신호
        if signal > 0.6:
            if stock_code not in self.positions or self.positions[stock_code]['quantity'] <= 0:
                return self._buy(stock_code, current_price, timestamp)

        # 강한 매도 신호 또는 손익 관리
        elif signal < -0.6 or self._should_close_position(stock_code, current_price):
            if stock_code in self.positions and self.positions[stock_code]['quantity'] > 0:
                return self._sell(stock_code, current_price, timestamp)

        return None

    def _buy(self, stock_code: str, price: int, timestamp: str):
        """매수 실행"""
        position_value = min(self.balance, self.max_position_size)
        quantity = position_value // price

        if quantity < 1 or position_value > self.balance:
            return None

        total_cost = quantity * price
        self.balance -= total_cost

        if stock_code not in self.positions:
            self.positions[stock_code] = {
                'quantity': 0,
                'avg_price': 0
            }

        pos = self.positions[stock_code]
        total_quantity = pos['quantity'] + quantity
        total_value = (pos['quantity'] * pos['avg_price']) + total_cost

        pos['quantity'] = total_quantity
        pos['avg_price'] = total_value // total_quantity

        trade = {
            'timestamp': timestamp,
            'stock_code': stock_code,
            'side': 'buy',
            'quantity': quantity,
            'price': price,
            'total_value': total_cost
        }

        self.trades.append(trade)
        logger.info(f"[매수] {stock_code}: {quantity:,}주 @ {price:,}원 (잔고: {self.balance:,.0f}원)")

        return trade

    def _sell(self, stock_code: str, price: int, timestamp: str):
        """매도 실행"""
        if stock_code not in self.positions or self.positions[stock_code]['quantity'] <= 0:
            return None

        pos = self.positions[stock_code]
        quantity = pos['quantity']
        avg_price = pos['avg_price']

        total_revenue = quantity * price
        self.balance += total_revenue

        # 손익 계산
        pnl = (price - avg_price) * quantity
        self.total_pnl += pnl

        # 포지션 청산
        pos['quantity'] = 0
        pos['avg_price'] = 0

        trade = {
            'timestamp': timestamp,
            'stock_code': stock_code,
            'side': 'sell',
            'quantity': quantity,
            'price': price,
            'total_value': total_revenue,
            'pnl': pnl,
            'pnl_rate': (price - avg_price) / avg_price
        }

        self.trades.append(trade)
        logger.info(f"[매도] {stock_code}: {quantity:,}주 @ {price:,}원 "
                   f"(손익: {pnl:+,.0f}원, {trade['pnl_rate']:+.2%})")

        return trade

    def _should_close_position(self, stock_code: str, current_price: int) -> bool:
        """포지션 청산 여부 판단 (손절/익절)"""
        if stock_code not in self.positions or self.positions[stock_code]['quantity'] <= 0:
            return False

        pos = self.positions[stock_code]
        pnl_rate = (current_price - pos['avg_price']) / pos['avg_price']

        # 손절 또는 익절
        return pnl_rate <= self.stop_loss_rate or pnl_rate >= self.take_profit_rate

    def get_portfolio_status(self, current_prices: dict) -> dict:
        """포트폴리오 현황"""
        total_value = self.balance
        unrealized_pnl = 0

        for stock_code, pos in self.positions.items():
            if pos['quantity'] > 0 and stock_code in current_prices:
                position_value = pos['quantity'] * current_prices[stock_code]
                total_value += position_value

                position_pnl = (current_prices[stock_code] - pos['avg_price']) * pos['quantity']
                unrealized_pnl += position_pnl

        return {
            'balance': self.balance,
            'total_value': total_value,
            'realized_pnl': self.total_pnl,
            'unrealized_pnl': unrealized_pnl,
            'total_pnl': self.total_pnl + unrealized_pnl,
            'total_return': (total_value - self.initial_balance) / self.initial_balance,
            'positions': {k: v for k, v in self.positions.items() if v['quantity'] > 0}
        }

async def run_simulation():
    """시뮬레이션 실행"""
    logger.info("실시간 거래 시뮬레이션 시작...")

    # 데이터 로드
    data_path = "data/preprocessed_data.parquet"
    if not os.path.exists(data_path):
        logger.error(f"데이터 파일이 없습니다: {data_path}")
        return

    df = _safe_read_table(data_path)
    df.reset_index(inplace=True)

    # 날짜 컬럼 확인/생성
    if 'Date' not in df.columns and 'date' in df.columns:
        df['Date'] = df['date']

    # 최근 3개월 데이터만 사용
    df['Date'] = pd.to_datetime(df['Date'])
    cutoff_date = df['Date'].max() - timedelta(days=90)
    df = df[df['Date'] >= cutoff_date].copy()

    # 시뮬레이터 초기화
    simulator = TradingSimulator(initial_balance=10000000)  # 1천만원

    # 종목별 가격 히스토리
    price_history = {}

    # 시뮬레이션 진행
    for idx, row in df.iterrows():
        if pd.isna(row['Date']) or pd.isna(row['code']) or pd.isna(row['Close']):
            continue

        stock_code = str(row['code'])
        current_price = int(row['Close'])
        timestamp = row['Date'].isoformat()

        # 가격 히스토리 업데이트
        if stock_code not in price_history:
            price_history[stock_code] = []

        price_history[stock_code].append(current_price)

        # 최근 100개 가격만 유지
        if len(price_history[stock_code]) > 100:
            price_history[stock_code].pop(0)

        # 충분한 데이터가 있을 때만 신호 생성
        if len(price_history[stock_code]) >= 20:
            signal = simulator.get_technical_signal(price_history[stock_code])

            # 거래 실행
            trade = simulator.execute_trade(stock_code, signal, current_price, timestamp)

        # 실시간 속도 시뮬레이션 (옵션)
        if idx % 100 == 0:  # 100개 데이터마다 상태 출력
            current_prices = {code: prices[-1] for code, prices in price_history.items() if prices}
            status = simulator.get_portfolio_status(current_prices)

            logger.info(f"[{timestamp[:10]}] 잔고: {status['balance']:,.0f}원, "
                       f"평가액: {status['total_value']:,.0f}원, "
                       f"수익률: {status['total_return']:+.2%}")

            # 짧은 대기 (비동기 처리 시뮬레이션)
            await asyncio.sleep(0.01)

    # 최종 결과
    final_prices = {code: prices[-1] for code, prices in price_history.items() if prices}
    final_status = simulator.get_portfolio_status(final_prices)

    logger.info("=== 시뮬레이션 완료 ===")
    logger.info(f"초기 자본: {simulator.initial_balance:,.0f}원")
    logger.info(f"최종 평가액: {final_status['total_value']:,.0f}원")
    logger.info(f"총 수익률: {final_status['total_return']:+.2%}")
    logger.info(f"실현 손익: {final_status['realized_pnl']:+,.0f}원")
    logger.info(f"평가 손익: {final_status['unrealized_pnl']:+,.0f}원")
    logger.info(f"총 거래 횟수: {len(simulator.trades)}회")

    # 거래 결과 저장
    results_dir = "results"
    os.makedirs(results_dir, exist_ok=True)

    with open(f"{results_dir}/simulation_result.json", 'w', encoding='utf-8') as f:
        json.dump({
            'final_status': final_status,
            'trades': simulator.trades[-20:],  # 최근 20개 거래만 저장
            'simulation_date': datetime.now().isoformat()
        }, f, ensure_ascii=False, indent=2)

    logger.info(f"시뮬레이션 결과 저장: {results_dir}/simulation_result.json")

if __name__ == "__main__":
    asyncio.run(run_simulation())
