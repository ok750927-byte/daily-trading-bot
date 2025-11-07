"""
포트폴리오 최적화 시스템
- 현대 포트폴리오 이론 적용
- 리스크 패리티
- 동적 리밸런싱
"""
import os
import sys
import json
import numpy as np
import pandas as pd
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.optimize import minimize
import warnings
from dataclasses import dataclass
warnings.filterwarnings('ignore')

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class OptimizationResult:
    """최적화 결과 데이터"""
    weights: Dict[str, float]
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    method: str
    symbols: List[str]

class PortfolioOptimizer:
    """포트폴리오 최적화"""

    def __init__(self):
        self.project_root = project_root

        # 최적화 설정
        self.risk_free_rate = 0.025  # 무위험 수익률 2.5%
        self.max_weight = 0.3  # 단일 종목 최대 비중 30%
        self.min_weight = 0.05  # 단일 종목 최소 비중 5%

        # 리밸런싱
        self.rebalance_frequency = 30  # 30일마다 리밸런싱
        self.drift_threshold = 0.05  # 5% 이상 벗어나면 리밸런싱

    def load_returns_data(self, symbols: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """수익률 데이터 로드"""
        try:
            returns_data = pd.DataFrame()

            for symbol in symbols:
                # 가격 데이터 로드
                data_file = self.project_root / "data" / "prices" / f"{symbol}.csv"

                if data_file.exists():
                    df = pd.read_csv(data_file)
                    df['date'] = pd.to_datetime(df['date'])

                    # 날짜 범위 필터링
                    mask = (df['date'] >= start_date) & (df['date'] <= end_date)
                    df = df[mask].copy()

                    if len(df) > 1:
                        # 일간 수익률 계산
                        df['return'] = df['close'].pct_change()
                        df.set_index('date', inplace=True)

                        returns_data[symbol] = df['return']

                        logger.info(f"수익률 데이터 로드: {symbol} ({len(df)}일)")
                else:
                    logger.warning(f"가격 데이터 파일 없음: {symbol}")

            # 결측값 제거
            returns_data = returns_data.dropna()

            return returns_data

        except Exception as e:
            logger.error(f"수익률 데이터 로드 실패: {e}")
            return pd.DataFrame()

    def calculate_expected_returns(self, returns_df: pd.DataFrame, method: str = 'historical') -> pd.Series:
        """기대 수익률 계산"""
        try:
            if method == 'historical':
                # 과거 평균 수익률
                expected_returns = returns_df.mean() * 252  # 연율화

            elif method == 'capm':
                # CAPM 모델 (단순화)
                market_return = returns_df.mean(axis=1).mean() * 252  # 시장 수익률

                expected_returns = pd.Series(index=returns_df.columns, dtype=float)

                for symbol in returns_df.columns:
                    # 베타 계산
                    market_returns = returns_df.mean(axis=1)
                    stock_returns = returns_df[symbol]

                    covariance = np.cov(stock_returns.dropna(), market_returns)[0, 1]
                    market_variance = np.var(market_returns)

                    beta = covariance / market_variance if market_variance > 0 else 1.0

                    # CAPM 기대 수익률
                    expected_return = self.risk_free_rate + beta * (market_return - self.risk_free_rate)
                    expected_returns[symbol] = expected_return

            elif method == 'momentum':
                # 모멘텀 기반 (최근 3개월 성과)
                recent_returns = returns_df.tail(63)  # 약 3개월
                expected_returns = recent_returns.mean() * 252

            else:
                expected_returns = returns_df.mean() * 252

            return expected_returns

        except Exception as e:
            logger.error(f"기대 수익률 계산 실패: {e}")
            return pd.Series()

    def calculate_covariance_matrix(self, returns_df: pd.DataFrame, method: str = 'sample') -> pd.DataFrame:
        """공분산 행렬 계산"""
        try:
            if method == 'sample':
                # 표본 공분산
                cov_matrix = returns_df.cov() * 252  # 연율화

            elif method == 'ledoit_wolf':
                # Ledoit-Wolf 수축 추정
                from sklearn.covariance import LedoitWolf

                lw = LedoitWolf()
                lw_cov = lw.fit(returns_df.dropna()).covariance_

                cov_matrix = pd.DataFrame(
                    lw_cov * 252,
                    index=returns_df.columns,
                    columns=returns_df.columns
                )

            elif method == 'exponential':
                # 지수 가중 공분산
                cov_matrix = returns_df.ewm(span=60).cov().iloc[-len(returns_df.columns):] * 252

            else:
                cov_matrix = returns_df.cov() * 252

            return cov_matrix

        except Exception as e:
            logger.error(f"공분산 행렬 계산 실패: {e}")
            return pd.DataFrame()

    def optimize_portfolio(self, expected_returns: pd.Series, cov_matrix: pd.DataFrame,
                          method: str = 'max_sharpe') -> Dict:
        """포트폴리오 최적화"""
        try:
            n_assets = len(expected_returns)

            # 제약 조건
            constraints = [
                {'type': 'eq', 'fun': lambda x: np.sum(x) - 1.0}  # 가중치 합 = 1
            ]

            # 경계 조건 (최소/최대 비중)
            bounds = [(self.min_weight, self.max_weight) for _ in range(n_assets)]

            # 초기 가중치 (균등 배분)
            x0 = np.array([1.0 / n_assets] * n_assets)

            if method == 'max_sharpe':
                # 샤프 비율 최대화
                def objective(weights):
                    portfolio_return = np.sum(weights * expected_returns)
                    portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
                    sharpe_ratio = (portfolio_return - self.risk_free_rate) / portfolio_vol
                    return -sharpe_ratio  # 최대화를 위해 음수

            elif method == 'min_vol':
                # 최소 분산
                def objective(weights):
                    return np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))

            elif method == 'risk_parity':
                # 리스크 패리티
                def objective(weights):
                    portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
                    marginal_contribs = np.dot(cov_matrix, weights) / portfolio_vol
                    risk_contribs = weights * marginal_contribs / portfolio_vol

                    # 리스크 기여도의 분산 최소화
                    target_risk = 1.0 / n_assets
                    return np.sum((risk_contribs - target_risk) ** 2)

            elif method == 'max_return':
                # 수익률 최대화
                def objective(weights):
                    return -np.sum(weights * expected_returns)

            else:
                logger.error(f"알 수 없는 최적화 방법: {method}")
                return None

            # 최적화 실행
            result = minimize(objective, x0, method='SLSQP', bounds=bounds, constraints=constraints)

            if result.success:
                optimal_weights = dict(zip(expected_returns.index, result.x))
                return optimal_weights
            else:
                logger.warning(f"최적화 실패: {result.message}")
                # 실패 시 균등 가중치 반환
                return dict(zip(expected_returns.index, x0))

        except Exception as e:
            logger.error(f"포트폴리오 최적화 실패: {e}", exc_info=True)
            return None

    def run_optimization(self, symbols: List[str], start_date: str, end_date: str,
                         opt_method: str = 'max_sharpe',
                         returns_method: str = 'historical',
                         cov_method: str = 'sample') -> Optional[OptimizationResult]:
        """전체 최적화 프로세스 실행"""
        try:
            logger.info(f"포트폴리오 최적화 시작: {symbols}, 기간: {start_date}~{end_date}, 방법: {opt_method}")

            # 1. 데이터 로드
            returns_df = self.load_returns_data(symbols, start_date, end_date)
            if returns_df.empty or len(returns_df.columns) < 2:
                logger.error("최적화를 위한 데이터가 부족합니다.")
                return None

            # 유효한 심볼 목록 업데이트
            valid_symbols = returns_df.columns.tolist()

            # 2. 기대 수익률 및 공분산 계산
            expected_returns = self.calculate_expected_returns(returns_df, method=returns_method)
            cov_matrix = self.calculate_covariance_matrix(returns_df, method=cov_method)

            if expected_returns.empty or cov_matrix.empty:
                logger.error("기대 수익률 또는 공분산 계산에 실패했습니다.")
                return None

            # 3. 포트폴리오 최적화
            optimal_weights = self.optimize_portfolio(expected_returns, cov_matrix, method=opt_method)

            if not optimal_weights:
                logger.error("최적 가중치를 계산하지 못했습니다.")
                return None

            # 4. 결과 계산
            weights_array = np.array([optimal_weights.get(s, 0) for s in valid_symbols])

            exp_return = np.sum(weights_array * expected_returns)
            exp_vol = np.sqrt(np.dot(weights_array.T, np.dot(cov_matrix, weights_array)))
            sharpe = (exp_return - self.risk_free_rate) / exp_vol if exp_vol > 0 else 0

            logger.info(f"최적화 완료. 기대 수익률: {exp_return:.2%}, 기대 변동성: {exp_vol:.2%}, 샤프 지수: {sharpe:.2f}")

            return OptimizationResult(
                weights=optimal_weights,
                expected_return=exp_return,
                expected_volatility=exp_vol,
                sharpe_ratio=sharpe,
                method=opt_method,
                symbols=valid_symbols
            )

        except Exception as e:
            logger.error(f"최적화 프로세스 실행 중 오류: {e}", exc_info=True)
            return None

# 예제 실행
if __name__ == '__main__':
    def example_run():
        optimizer = PortfolioOptimizer()

        # 설정
        symbols = ['005930', '000660', '035420', '035720', '051910', '066570', '068270']  # 대형주 7개
        start_date = '2023-01-01'
        end_date = '2024-10-31'

        optimization_methods = ['max_sharpe', 'min_vol', 'risk_parity']

        try:
            # 전체 최적화 프로세스 실행 (예시)
            result = optimizer.run_optimization(symbols, start_date, end_date,
                                               opt_method='max_sharpe',
                                               returns_method='historical',
                                               cov_method='sample')

            if result:
                print("최적화 결과:")
                print(f"  방법: {result.method}")
                print(f"  기대 수익률: {result.expected_return:.2%}")
                print(f"  기대 변동성: {result.expected_volatility:.2%}")
                print(f"  샤프 비율: {result.sharpe_ratio:.2f}")
                print("  가중치:")

                for symbol, weight in result.weights.items():
                    print(f"    {symbol}: {weight:.2%}")
            else:
                print("최적화 실패")

        except Exception as e:
            print(f"오류 발생: {e}")

    example_run()
