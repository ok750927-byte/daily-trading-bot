"""
시세 데이터 수집 유틸리티
FinanceDataReader를 사용하여 OHLCV 데이터를 가져옵니다.
- 로깅, 예외 처리, 데이터 검증 기능 포함
"""

import logging
from typing import Optional
import pandas as pd

# 로거 설정
logger = logging.getLogger(__name__)

try:
    import FinanceDataReader as fdr
except ImportError:
    fdr = None


def fetch_ohlcv(ticker: str, start: Optional[str] = None, end: Optional[str] = None) -> Optional[pd.DataFrame]:
    """
    지정된 티커의 OHLCV 데이터를 가져옵니다.

    Args:
        ticker: '005930' 또는 'AAPL' 등 FinanceDataReader에서 지원하는 형식
        start (Optional[str]): 조회 시작일 'YYYY-MM-DD'
        end (Optional[str]): 조회 종료일 'YYYY-MM-DD'

    Returns:
        Optional[pd.DataFrame]: 성공 시 OHLCV 데이터프레임, 실패 시 None
    """
    if fdr is None:
        # Tests expect logger.error + None when FinanceDataReader is not installed
        logger.error("FinanceDataReader가 설치되어 있지 않습니다. `pip install finance-datareader`로 설치해주세요.")
        return None

    logger.info(f"'{ticker}'의 시세 데이터 수집을 시작합니다 (기간: {start}~{end}).")
    try:
        df = fdr.DataReader(ticker, start, end)

        # treat both None and empty DataFrame as no-data
        if df is None or (hasattr(df, 'empty') and df.empty):
            logger.warning(f"'{ticker}'에 대한 데이터를 찾을 수 없습니다. 티커가 유효한지 확인해주세요.")
            return None

        # 간단한 데이터 검증: 필수 컬럼이 없으면 None 반환 (테스트 기대)
        required_columns = {'Open', 'High', 'Low', 'Close', 'Volume'}
        if not required_columns.issubset(df.columns):
            logger.error(f"수집된 데이터에 필수 컬럼({required_columns})이 부족합니다.")
            return None

        logger.info(f"'{ticker}' 데이터 수집 완료. (총 {len(df)}일치)")
        return df

    except Exception as e:
        logger.error(f"'{ticker}' 데이터 수집 중 예기치 않은 오류 발생: {e}", exc_info=True)
        return None
