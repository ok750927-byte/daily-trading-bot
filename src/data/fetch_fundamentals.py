"""
기업 재무 정보(기본적 분석 지표) 수집 유틸리티
pykrx 라이브러리를 사용하여 특정 날짜의 시장 전체 종목에 대한 재무 정보를 가져옵니다.
"""

import logging
from typing import Optional
import pandas as pd

# 로거 설정
logger = logging.getLogger(__name__)

try:
    from pykrx import stock
except ImportError:
    stock = None

def get_market_fundamentals(date: str) -> Optional[pd.DataFrame]:
    """
    지정된 날짜의 KOSPI 및 KOSDAQ 전체 종목의 기본적 분석 지표를 가져옵니다.

    Args:
        date (str): 조회 기준일 'YYYYMMDD' 형식

    Returns:
        Optional[pd.DataFrame]: 성공 시 재무 정보 데이터프레임, 실패 시 None
    """
    if stock is None:
        logger.error("pykrx가 설치되어 있지 않습니다. `pip install pykrx`로 설치해주세요.")
        return None

    logger.info(f"'{date}' 기준 시장 전체 재무 정보 수집을 시작합니다.")
    try:
        # KOSPI, KOSDAQ 정보 동시 조회는 지원하지 않으므로 각각 조회 후 병합
        df_kospi = stock.get_market_fundamental_by_ticker(date, market='KOSPI')
        df_kosdaq = stock.get_market_fundamental_by_ticker(date, market='KOSDAQ')

        # 인덱스를 컬럼으로 변환 (원본 인덱스 이름이 'ticker'일 수 있음)
        df_kospi.reset_index(inplace=True)
        df_kosdaq.reset_index(inplace=True)

        # 각 데이터프레임에 시장 구분 추가
        df_kospi['시장'] = 'KOSPI'
        df_kosdaq['시장'] = 'KOSDAQ'

        # 두 시장 데이터 병합
        df_market = pd.concat([df_kospi, df_kosdaq], ignore_index=True)

        if df_market.empty:
            logger.warning(f"'{date}'에 대한 재무 데이터를 찾을 수 없습니다. 해당 날짜가 영업일인지 확인해주세요.")
            return None

        # 데이터프레임에 기준 날짜 컬럼 추가
        df_market['Date'] = pd.to_datetime(date, format='%Y%m%d')

        # 일부 환경(테스트 모킹)에서는 인덱스 이름이 'ticker' (영문)으로 나옵니다.
        # 테스트는 '티커' 컬럼을 기대하므로 복원해줍니다.
        if '티커' not in df_market.columns and 'ticker' in df_market.columns:
            df_market['티커'] = df_market['ticker']

        # 호환성 차원에서 'code' 컬럼도 제공
        if 'code' not in df_market.columns:
            if '티커' in df_market.columns:
                df_market['code'] = df_market['티커']
            elif 'ticker' in df_market.columns:
                df_market['code'] = df_market['ticker']

        logger.info(f"'{date}' 기준 재무 정보 수집 완료. (총 {len(df_market)}개 종목)")
        return df_market

    except Exception as e:
        logger.error(f"'{date}' 기준 재무 정보 수집 중 예기치 않은 오류 발생: {e}", exc_info=True)
        return None
