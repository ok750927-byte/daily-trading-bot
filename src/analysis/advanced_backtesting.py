"""
고급 백테스팅 시스템
- 실제 데이터를 활용한 정교한 백테스팅
- 다양한 전략 검증
- 리스크 분석
"""
import os
import sys
import json
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import matplotlib.pyplot as plt
import seaborn as sns
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Trade:
    """거래 정보"""
    entry_date: str
    exit_date: str
    symbol: str
    side: str  # 'BUY' or 'SELL'
    entry_price: float
    exit_price: float
    quantity: int
    pnl: float
    pnl_pct: float
    duration_days: int
    reason: str  # 'SIGNAL', 'STOP_LOSS', 'TAKE_PROFIT', 'TIME_LIMIT'

@dataclass
class BacktestResult:
    """백테스트 결과"""
    trades: List[Trade]
    portfolio_history: pd.DataFrame
    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_trades: int
    avg_trade_duration: float

    def to_dict(self) -> Dict:
        """결과를 딕셔너리로 변환 (GUI 표시용)"""
        return {
            "총 수익률": self.total_return,
            "연평균 수익률 (CAGR)": self.annual_return,
            "샤프 지수": self.sharpe_ratio,
            "최대 낙폭 (MDD)": self.max_drawdown,
            "승률": self.win_rate,
            "수익 팩터": self.profit_factor,
            "총 거래 수": self.total_trades,
            "평균 거래 기간 (일)": self.avg_trade_duration,
        }

class AdvancedBacktester:
    """고급 백테스팅 시스템"""

    def __init__(self):
        self.project_root = project_root

        # 백테스트 설정
        self.initial_capital = 10_000_000  # 초기 자본 1천만원
        self.transaction_cost = 0.0015  # 거래 비용 0.15%
        self.slippage = 0.001  # 슬리피지 0.1%

        # 리스크 관리
        self.max_position_size = 0.2  # 단일 종목 최대 투자 비율 20%
        self.stop_loss_pct = 0.05  # 손절 5%
        self.take_profit_pct = 0.10  # 익절 10%
        self.max_holding_days = 30  # 최대 보유 기간

        # 데이터
        self.price_data = {}
        self.ml_predictions = {}

        # 결과 저장
        self.results = {}

    def load_price_data(self, symbols: List[str], start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """가격 데이터 로드"""
        try:
            price_data = {}

            for symbol in symbols:
                # CSV 파일에서 데이터 로드
                data_file = self.project_root / "data" / "prices" / f"{symbol}.csv"

                if data_file.exists():
                    df = pd.read_csv(data_file)
                    df['date'] = pd.to_datetime(df['date'])

                    # 날짜 범위 필터링
                    mask = (df['date'] >= start_date) & (df['date'] <= end_date)
                    df = df[mask].copy()

                    df.set_index('date', inplace=True)
                    price_data[symbol] = df

                    logger.info(f"데이터 로드: {symbol} ({len(df)}일)")
                else:
                    logger.warning(f"데이터 파일 없음: {symbol}")

            return price_data

        except Exception as e:
            logger.error(f"가격 데이터 로드 실패: {e}")
            return {}

    def load_ml_predictions(self, symbols: List[str], start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """ML 예측 데이터 로드"""
        try:
            predictions = {}

            # ML 예측 결과 파일에서 로드
            pred_file = self.project_root / "results" / "predictions.json"

            if pred_file.exists():
                with open(pred_file, 'r', encoding='utf-8') as f:
                    pred_data = json.load(f)

                for symbol in symbols:
                    symbol_preds = []

                    for pred in pred_data:
                        if pred.get('code') == symbol:
                            pred_date = pred.get('date', '')
                            if start_date <= pred_date <= end_date:
                                symbol_preds.append({
                                    'date': pred_date,
                                    'prediction': pred.get('prediction', 0.5),
                                    'confidence': pred.get('confidence', 0.5)
                                })

                    if symbol_preds:
                        df = pd.DataFrame(symbol_preds)
                        df['date'] = pd.to_datetime(df['date'])
                        df.set_index('date', inplace=True)
                        predictions[symbol] = df

            return predictions

        except Exception as e:
            logger.error(f"ML 예측 데이터 로드 실패: {e}")
            return {}

    def generate_signals(self, price_df: pd.DataFrame, pred_df: pd.DataFrame) -> pd.DataFrame:
        """거래 신호 생성"""
        try:
            signals = pd.DataFrame(index=price_df.index)
            signals['signal'] = 0.0
            signals['confidence'] = 0.0

            # ML 예측 기반 신호
            for date in signals.index:
                if date in pred_df.index:
                    prediction = pred_df.loc[date, 'prediction']
                    confidence = pred_df.loc[date, 'confidence']

                    # 신호 생성 로직
                    if prediction > 0.7 and confidence > 0.8:
                        signals.loc[date, 'signal'] = 1.0  # 매수
                    elif prediction < 0.3 and confidence > 0.8:
                        signals.loc[date, 'signal'] = -1.0  # 매도
                    else:
                        signals.loc[date, 'signal'] = 0.0  # 대기

                    signals.loc[date, 'confidence'] = confidence

            # 기술적 지표 추가
            signals = self.add_technical_indicators(price_df, signals)

            return signals

        except Exception as e:
            logger.error(f"신호 생성 실패: {e}")
            return pd.DataFrame()

    def add_technical_indicators(self, price_df: pd.DataFrame, signals: pd.DataFrame) -> pd.DataFrame:
        """기술적 지표 추가"""
        try:
            # 이동평균
            price_df['ma5'] = price_df['close'].rolling(5).mean()
            price_df['ma20'] = price_df['close'].rolling(20).mean()

            # RSI
            delta = price_df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            price_df['rsi'] = 100 - (100 / (1 + rs))

            # 볼린저 밴드
            price_df['bb_middle'] = price_df['close'].rolling(20).mean()
            price_df['bb_std'] = price_df['close'].rolling(20).std()
            price_df['bb_upper'] = price_df['bb_middle'] + (price_df['bb_std'] * 2)
            price_df['bb_lower'] = price_df['bb_middle'] - (price_df['bb_std'] * 2)

            # 기술적 지표 기반 신호 조정 (예시)
            # 예: MA 크로스오버
            signals['ma_signal'] = 0.0
            signals.loc[price_df['ma5'] > price_df['ma20'], 'ma_signal'] = 1.0
            signals.loc[price_df['ma5'] < price_df['ma20'], 'ma_signal'] = -1.0

            return signals

        except Exception as e:
            logger.error(f"기술적 지표 추가 실패: {e}")
            return signals

    def run_backtest(self, symbols: List[str], start_date: str, end_date: str, strategy_name: str) -> Optional[BacktestResult]:
        """백테스트 실행"""
        try:
            logger.info(f"백테스트 시작: {symbols}, {start_date}~{end_date}, 전략: {strategy_name}")

            # 1. 데이터 로드
            self.price_data = self.load_price_data(symbols, start_date, end_date)
            self.ml_predictions = self.load_ml_predictions(symbols, start_date, end_date)

            if not self.price_data:
                logger.error("가격 데이터가 없어 백테스트를 중단합니다.")
                return None

            # 포트폴리오 및 거래 기록 초기화
            portfolio = self._initialize_portfolio(start_date)
            positions = {symbol: {'quantity': 0, 'avg_price': 0, 'entry_date': None} for symbol in symbols}
            trades = []

            # 전체 기간에 대한 날짜 인덱스 생성
            all_dates = pd.date_range(start=start_date, end=end_date, freq='B') # 'B'는 Business day

            # 포트폴리오 가치 기록용 DataFrame
            portfolio_history = pd.DataFrame(index=all_dates, columns=['total_value'])

            # 2. 날짜별 시뮬레이션
            for date in all_dates:
                if date < pd.to_datetime(start_date): continue

                portfolio['cash'] = portfolio.get(date, {}).get('cash', self.initial_capital)

                # 현재 포지션 가치 계산
                current_position_value = 0
                for symbol, pos in positions.items():
                    if pos['quantity'] > 0 and symbol in self.price_data and date in self.price_data[symbol].index:
                        current_price = self.price_data[symbol].loc[date, 'close']
                        current_position_value += pos['quantity'] * current_price

                # 포트폴리오 총 가치 기록
                total_value = portfolio['cash'] + current_position_value
                portfolio_history.loc[date] = total_value

                # 각 종목에 대해 거래 결정
                for symbol in symbols:
                    if symbol not in self.price_data or date not in self.price_data[symbol].index:
                        continue

                    price_df = self.price_data[symbol]
                    pred_df = self.ml_predictions.get(symbol, pd.DataFrame())

                    # 신호 생성
                    signals = self.generate_signals(price_df.loc[:date], pred_df.loc[:date])
                    if signals.empty or date not in signals.index:
                        continue

                    signal = signals.loc[date, 'signal']
                    current_price = price_df.loc[date, 'close']

                    # 포지션 관리 (청산)
                    if positions[symbol]['quantity'] > 0:
                        entry_price = positions[symbol]['avg_price']
                        entry_date = positions[symbol]['entry_date']
                        holding_days = (date - entry_date).days

                        exit_reason = None
                        if current_price <= entry_price * (1 - self.stop_loss_pct):
                            exit_reason = 'STOP_LOSS'
                        elif current_price >= entry_price * (1 + self.take_profit_pct):
                            exit_reason = 'TAKE_PROFIT'
                        elif holding_days > self.max_holding_days:
                            exit_reason = 'TIME_LIMIT'
                        elif signal == -1.0:
                            exit_reason = 'SIGNAL'

                        if exit_reason:
                            # 매도 실행
                            quantity_to_sell = positions[symbol]['quantity']
                            sell_value = quantity_to_sell * current_price * (1 - self.transaction_cost - self.slippage)
                            portfolio['cash'] += sell_value

                            pnl = (current_price - entry_price) * quantity_to_sell
                            pnl_pct = (current_price / entry_price) - 1

                            trades.append(Trade(
                                entry_date=entry_date.strftime('%Y-%m-%d'),
                                exit_date=date.strftime('%Y-%m-%d'),
                                symbol=symbol,
                                side='BUY',
                                entry_price=entry_price,
                                exit_price=current_price,
                                quantity=quantity_to_sell,
                                pnl=pnl,
                                pnl_pct=pnl_pct,
                                duration_days=holding_days,
                                reason=exit_reason
                            ))

                            positions[symbol] = {'quantity': 0, 'avg_price': 0, 'entry_date': None}

                    # 포지션 진입
                    if signal == 1.0 and positions[symbol]['quantity'] == 0:
                        # 매수 실행
                        investment_per_trade = total_value * self.max_position_size
                        quantity_to_buy = int(investment_per_trade / current_price)

                        if quantity_to_buy > 0:
                            buy_cost = quantity_to_buy * current_price * (1 + self.transaction_cost + self.slippage)
                            if portfolio['cash'] >= buy_cost:
                                portfolio['cash'] -= buy_cost
                                positions[symbol] = {
                                    'quantity': quantity_to_buy,
                                    'avg_price': current_price,
                                    'entry_date': date
                                }

            # 3. 결과 분석
            portfolio_history.dropna(inplace=True)
            final_result = self.analyze_performance(portfolio_history, trades, start_date, end_date)

            logger.info(f"백테스트 완료. 최종 수익률: {final_result.total_return:.2%}")

            return final_result

        except Exception as e:
            logger.error(f"백테스트 실행 중 오류 발생: {e}", exc_info=True)
            return None

    def _initialize_portfolio(self, start_date: str) -> Dict:
        """포트폴리오 초기화"""
        return {
            pd.to_datetime(start_date): {
                'cash': self.initial_capital,
                'positions': {},
                'total_value': self.initial_capital
            }
        }

    def analyze_performance(self, portfolio_history: pd.DataFrame, trades: List[Trade], start_date: str, end_date: str) -> BacktestResult:
        """성과 분석"""
        if portfolio_history.empty:
            return BacktestResult(trades, pd.DataFrame(), 0,0,0,0,0,0,0,0)

        # 총 수익률
        total_return = (portfolio_history['total_value'].iloc[-1] / portfolio_history['total_value'].iloc[0]) - 1

        # 연평균 수익률 (CAGR)
        days = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days
        years = days / 365.25
        annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0

        # 샤프 지수
        returns = portfolio_history['total_value'].pct_change().dropna()
        sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() != 0 else 0

        # 최대 낙폭 (MDD)
        peak = portfolio_history['total_value'].expanding(min_periods=1).max()
        drawdown = (portfolio_history['total_value'] - peak) / peak
        max_drawdown = drawdown.min()

        # 승률
        winning_trades = [t for t in trades if t.pnl > 0]
        win_rate = len(winning_trades) / len(trades) if trades else 0

        # 수익 팩터
        total_profit = sum(t.pnl for t in winning_trades)
        losing_trades = [t for t in trades if t.pnl <= 0]
        total_loss = abs(sum(t.pnl for t in losing_trades))
        profit_factor = total_profit / total_loss if total_loss != 0 else float('inf')

        # 평균 거래 기간
        avg_trade_duration = np.mean([t.duration_days for t in trades]) if trades else 0

        return BacktestResult(
            trades=trades,
            portfolio_history=portfolio_history,
            total_return=total_return,
            annual_return=annual_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=len(trades),
            avg_trade_duration=avg_trade_duration
        )

    def plot_results(self, result: BacktestResult):
        """결과 시각화"""
        try:
            # 포트폴리오 가치 추세
            plt.figure(figsize=(10, 6))
            plt.plot(result.portfolio_history.index, result.portfolio_history['total_value'], label='Portfolio Value', color='blue')
            plt.title('포트폴리오 가치 추세')
            plt.xlabel('날짜')
            plt.ylabel('총 가치')
            plt.legend()
            plt.grid()
            plt.show()

            # 거래 내역
            if result.trades:
                trades_df = pd.DataFrame([t.__dict__ for t in result.trades])

                # 거래별 수익률
                trades_df['trade_return'] = trades_df.apply(lambda x: (x['exit_price'] - x['entry_price']) / x['entry_price'], axis=1)

                plt.figure(figsize=(10, 6))
                sns.barplot(x='exit_date', y='trade_return', data=trades_df, palette='coolwarm')
                plt.title('거래별 수익률')
                plt.xlabel('거래 종료 날짜')
                plt.ylabel('수익률')
                plt.xticks(rotation=45)
                plt.grid(axis='y')
                plt.show()

        except Exception as e:
            logger.error(f"결과 시각화 실패: {e}")

def main():
    """메인 실행"""
    print("📊 고급 백테스팅 시스템")
    print("=" * 50)

    # 설정
    symbols = ['005930', '000660', '035420', '035720', '051910']  # 대형주 5개
    start_date = '2023-01-01'
    end_date = '2024-10-31'

    try:
        backtester = AdvancedBacktester()

        # 백테스트 실행
        print(f"백테스트 시작: {start_date} ~ {end_date}")
        print(f"대상 종목: {symbols}")

        results = backtester.run_multi_symbol_backtest(symbols, start_date, end_date)

        if results:
            # 리포트 생성
            report = backtester.create_performance_report(results)

            # 결과 출력
            print("\n" + report)

            # 결과 저장
            backtester.save_results(results, report)

            print(f"\n✅ 백테스트 완료! 결과가 results/advanced_backtest/ 에 저장되었습니다.")
        else:
            print("❌ 백테스트 실행 실패: 데이터 부족")

    except Exception as e:
        print(f"❌ 시스템 오류: {e}")

if __name__ == "__main__":
    main()
