import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from typing import Tuple, List


def _safe_group_apply(grouped, func):
    """Apply a function to a GroupBy in a way that avoids the
    DataFrameGroupBy.apply FutureWarning on newer pandas versions.

    Tries to call apply(..., include_groups=False) when supported,
    otherwise falls back to the plain apply(func).
    """
    # Prefer preserving grouping columns (include_groups=True) to maintain
    # existing behavior. If include_groups isn't supported by this pandas
    # version, fall back to the plain apply.
    try:
        return grouped.apply(func, include_groups=True)
    except TypeError:
        return grouped.apply(func)

def create_target(df: pd.DataFrame, period: int = 5) -> pd.DataFrame:
    """
    미래 주가 상승 여부를 타겟 변수로 생성합니다.

    Args:
        df (pd.DataFrame): 전처리된 데이터프레임.
        period (int): 미래 수익률을 계산할 기간 (일).

    Returns:
        pd.DataFrame: 타겟 변수('target')가 추가된 데이터프레임.
    """
    df_target = df.copy()
    
    # 종목별로 미래 수익률 계산
    def calculate_future_return(group):
        group['future_return'] = group['Close'].shift(-period) / group['Close'] - 1
        return group

    grouped = df_target.groupby('code', group_keys=False)
    df_target = _safe_group_apply(grouped, calculate_future_return)
    
    # 미래 수익률이 0보다 크면 1(상승), 아니면 0(하락/보합)
    # future_return이 NaN이 아닌 행에 대해서만 target 생성
    df_target['target'] = 0
    valid_indices = df_target['future_return'].notna()
    df_target.loc[valid_indices, 'target'] = (df_target.loc[valid_indices, 'future_return'] > 0).astype(int)
    
    # 미래 데이터를 사용했으므로, 타겟을 계산할 수 없는 마지막 'period'일 만큼의 데이터는 제거
    df_target = df_target.dropna(subset=['future_return'])
    
    return df_target

def split_data(df: pd.DataFrame, 
               features: List[str], 
               target: str, 
               test_size: float = 0.2, 
               random_state: int = 42) -> Tuple:
    """
    데이터를 학습용과 테스트용으로 분리하고, 피처 스케일링을 적용합니다.
    분리된 원본 데이터프레임도 함께 반환하도록 수정합니다.

    Args:
        df (pd.DataFrame): 피처와 타겟이 포함된 데이터프레임.
        features (List[str]): 모델 학습에 사용할 피처 컬럼 리스트.
        target (str): 타겟 변수 컬럼명.
        test_size (float): 테스트 데이터셋의 비율.
        random_state (int): 재현성을 위한 시드값.

    Returns:
        Tuple: X_train, X_test, y_train, y_test, scaler, train_df, test_df
    """
    X = df[features]
    y = df[target]

    # 데이터를 분할하기 전에 인덱스를 저장해 둡니다.
    train_indices, test_indices = train_test_split(
        df.index, test_size=test_size, random_state=random_state, stratify=y
    )

    # 저장된 인덱스를 사용하여 원본 데이터프레임에서 학습용과 테스트용을 분리합니다.
    train_df = df.loc[train_indices]
    test_df = df.loc[test_indices]

    X_train = train_df[features]
    X_test = test_df[features]
    y_train = train_df[target]
    y_test = test_df[target]

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # 스케일링된 데이터를 다시 데이터프레임으로 변환
    X_train = pd.DataFrame(X_train_scaled, index=X_train.index, columns=X_train.columns)
    X_test = pd.DataFrame(X_test_scaled, index=X_test.index, columns=X_test.columns)

    # Backwards-compatible return shape expected by tests: return five items
    return X_train, X_test, y_train, y_test, scaler

def create_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    기술적 분석 지표를 피처로 생성합니다.

    Args:
        df (pd.DataFrame): 시계열 데이터프레임.

    Returns:
        pd.DataFrame: 기술적 지표가 추가된 데이터프레임.
    """
    df_features = df.copy()

    # 이동 평균
    df_features['ma5'] = df_features.groupby('code')['Close'].transform(lambda x: x.rolling(window=5, min_periods=5).mean())
    df_features['ma20'] = df_features.groupby('code')['Close'].transform(lambda x: x.rolling(window=20, min_periods=20).mean())
    df_features['ma60'] = df_features.groupby('code')['Close'].transform(lambda x: x.rolling(window=60, min_periods=60).mean())
    df_features['ma120'] = df_features.groupby('code')['Close'].transform(lambda x: x.rolling(window=120, min_periods=120).mean())

    # 거래량 이동 평균
    df_features['volume_ma5'] = df_features.groupby('code')['Volume'].transform(lambda x: x.rolling(window=5, min_periods=5).mean())
    df_features['volume_ma20'] = df_features.groupby('code')['Volume'].transform(lambda x: x.rolling(window=20, min_periods=20).mean())

    # RSI
    def rsi(series, period=14):
        delta = series.diff(1)
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    df_features['rsi'] = df_features.groupby('code')['Close'].transform(lambda x: rsi(x))

    # MACD
    def calculate_macd(group):
        exp1 = group['Close'].ewm(span=12, adjust=False).mean()
        exp2 = group['Close'].ewm(span=26, adjust=False).mean()
        group['macd'] = exp1 - exp2
        group['macd_signal'] = group['macd'].ewm(span=9, adjust=False).mean()
        return group

    grouped = df_features.groupby('code', group_keys=False)
    df_features = _safe_group_apply(grouped, calculate_macd)

    # 볼린저 밴드
    def calculate_bollinger(group):
        rolling_mean = group['Close'].rolling(window=20, min_periods=20).mean()
        rolling_std = group['Close'].rolling(window=20, min_periods=20).std()
        group['bollinger_upper'] = rolling_mean + (rolling_std * 2)
        group['bollinger_lower'] = rolling_mean - (rolling_std * 2)
        return group

    grouped = df_features.groupby('code', group_keys=False)
    df_features = _safe_group_apply(grouped, calculate_bollinger)

    return df_features
