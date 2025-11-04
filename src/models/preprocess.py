"""
데이터 전처리 유틸리티(초안)
- 데이터 병합
- 기본 기술지표(이동평균, RSI) 추가

간단하고 안전한 구현으로 테스트 가능하도록 작성합니다.
"""

from typing import List
import pandas as pd


def merge_on_date(dfs: List[pd.DataFrame], how: str = 'inner') -> pd.DataFrame:
    """여러 DataFrame을 Date(인덱스 혹은 'date' 컬럼)를 기준으로 병합합니다."""
    if not dfs:
        return pd.DataFrame()
    base = dfs[0].copy()
    for other in dfs[1:]:
        base = base.join(other, how=how, rsuffix='_r')
    return base


def add_moving_average(df: pd.DataFrame, column: str = 'Close', window: int = 20) -> pd.DataFrame:
    df = df.copy()
    ma_col = f'MA_{window}'
    df[ma_col] = df[column].rolling(window=window, min_periods=1).mean()
    return df


def add_rsi(df: pd.DataFrame, column: str = 'Close', window: int = 14) -> pd.DataFrame:
    """간단한 RSI 계산(기준용) - pandas 연산만 사용"""
    df = df.copy()
    delta = df[column].diff()
    up = delta.clip(lower=0.0)
    down = -1.0 * delta.clip(upper=0.0)
    ma_up = up.rolling(window=window, min_periods=1).mean()
    ma_down = down.rolling(window=window, min_periods=1).mean()
    rs = ma_up / (ma_down.replace(0, 1e-8))
    df[f'RSI_{window}'] = 100 - (100 / (1 + rs))
    return df
