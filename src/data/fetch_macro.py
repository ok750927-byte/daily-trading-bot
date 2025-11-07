"""
거시경제 지표 데이터 수집 유틸리티
FinanceDataReader를 사용하여 주요 지수, 환율, 금리 등의 데이터를 가져옵니다.
"""

import logging
from typing import Optional, Dict
import pandas as pd
from functools import reduce

# 로거 설정
logger = logging.getLogger(__name__)

try:
    import FinanceDataReader as fdr
except ImportError:
    fdr = None

def get_macro_data(symbol_map: Dict[str, str], start: str, end: str) -> Optional[pd.DataFrame]:
    """
    지정된 여러 거시경제 지표 데이터를 가져와 하나의 데이터프레임으로 병합합니다.

    Args:
        symbol_map (Dict[str, str]): {'심볼': '컬럼명'} 형식의 딕셔너리
                                     예: {'KS11': 'KOSPI', 'USD/KRW': 'USD_KRW'}
        start (str): 조회 시작일 'YYYY-MM-DD'
        end (str): 조회 종료일 'YYYY-MM-DD'

    Returns:
        Optional[pd.DataFrame]: 성공 시 병합된 데이터프레임, 실패 시 None
    """
    if fdr is None:
        logger.error("FinanceDataReader가 설치되어 있지 않습니다. `pip install finance-datareader`로 설치해주세요.")
        return None

    logger.info(f"거시경제 지표 수집을 시작합니다 (기간: {start}~{end}).")

    all_dfs = []
    for symbol, col_name in symbol_map.items():
        try:
            logger.debug(f"'{symbol}' 데이터 수집 중...")
            df = fdr.DataReader(symbol, start, end)

            if df.empty:
                logger.warning(f"'{symbol}'에 대한 데이터를 찾을 수 없습니다.")
                continue

            # 'Close' 컬럼만 사용하고 컬럼명 변경
            df_renamed = df[['Close']].rename(columns={'Close': col_name})
            all_dfs.append(df_renamed)

        except Exception as e:
            logger.error(f"'{symbol}' 데이터 수집 중 오류 발생: {e}", exc_info=True)
            # 하나의 지표 실패가 전체를 중단시키지 않도록 계속 진행
            continue

    if not all_dfs:
        logger.error("수집된 거시경제 지표 데이터가 전혀 없습니다.")
        return None

    # 모든 데이터프레임을 'Date' 인덱스 기준으로 병합
    try:
        # reduce를 사용하여 리스트의 모든 데이터프레임을 순차적으로 병합
        final_df = reduce(lambda left, right: pd.merge(left, right, left_index=True, right_index=True, how='outer'), all_dfs)

        # 데이터가 없는 날짜(주말 등)의 NaN 값을 이전 값으로 채우기 (Forward Fill)
        final_df.ffill(inplace=True)

        logger.info(f"거시경제 지표 수집 및 병합 완료. (총 {len(final_df)}일치)")
        return final_df

    except Exception as e:
        logger.error(f"거시경제 지표 데이터 병합 중 오류 발생: {e}", exc_info=True)
        return None
