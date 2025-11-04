import pytest
import pandas as pd
import numpy as np
import os
from src.preprocessing.data_preprocessor import (
    load_all_data,
    handle_missing_values,
    create_features,
    preprocess_data
)

@pytest.fixture
def mock_data_path(tmp_path):
    """Pytest fixture to create a temporary data directory with mock data."""
    prices_dir = tmp_path / "prices"
    prices_dir.mkdir()
    fundamentals_dir = tmp_path / "fundamentals"
    fundamentals_dir.mkdir()
    macro_dir = tmp_path / "macro"
    macro_dir.mkdir()

    # 긴 기간의 데이터 생성
    dates = pd.to_datetime(pd.date_range(start="2022-01-01", end="2023-01-10"))
    
    price_data_001 = pd.DataFrame({
        'Open': np.random.uniform(100, 110, size=len(dates)),
        'High': np.random.uniform(110, 120, size=len(dates)),
        'Low': np.random.uniform(90, 100, size=len(dates)),
        'Close': np.random.uniform(100, 115, size=len(dates)),
        'Volume': np.random.randint(1000, 5000, size=len(dates))
    }, index=dates)
    price_data_001.index.name = 'date'
    price_data_001.to_csv(prices_dir / "001.parquet", index=True)

    price_data_002 = price_data_001.copy() * 1.5
    price_data_002.to_csv(prices_dir / "002.parquet", index=True)

    fundamentals_data = pd.DataFrame({'code': ['001', '002'], 'BPS': [1000, 1500]})
    fundamentals_data.to_csv(fundamentals_dir / "fundamentals_20220601.parquet", index=False)
    
    fundamentals_data_2 = pd.DataFrame({'code': ['001', '002'], 'BPS': [1015, 1520]})
    fundamentals_data_2.to_csv(fundamentals_dir / "fundamentals_20221201.parquet", index=False)

    macro_data = pd.DataFrame({
        'KOSPI': np.linspace(2000, 2500, len(dates)),
    }, index=dates)
    macro_data.index.name = 'date'
    macro_data.to_csv(macro_dir / f"macro_{dates.min().strftime('%Y%m%d')}_{dates.max().strftime('%Y%m%d')}.parquet", index=True)

    return str(tmp_path)

def test_load_all_data(mock_data_path):
    """Test loading and merging of all data sources."""
    target_stocks = ['001', '002']
    start_date = "2022-10-01"
    end_date = "2022-12-31"

    df = load_all_data(mock_data_path, target_stocks, start_date, end_date)

    assert df is not None
    assert not df.empty
    assert len(df) == 92 * 2 # 92 days in period * 2 stocks
    assert 'KOSPI' in df.columns
    assert 'BPS' in df.columns
    
    df_001 = df[df['code'] == '001']
    assert df_001[df_001['date'] < '2022-12-01']['BPS'].iloc[-1] == 1000
    assert df_001[df_001['date'] >= '2022-12-01']['BPS'].iloc[0] == 1015

def test_handle_missing_values():
    """Test the missing value handling logic."""
    data = {'code': ['A', 'A'], 'value': [1, np.nan]}
    df = pd.DataFrame(data)
    cleaned_df = handle_missing_values(df)
    assert cleaned_df.isnull().sum().sum() == 0
    assert cleaned_df['value'].iloc[1] == 1

def test_create_features():
    """Test the feature creation logic."""
    dates = pd.to_datetime(pd.date_range(start="2023-01-01", periods=20))
    data = {
        'code': ['A'] * 20, 
        'date': dates, 
        'Close': np.arange(20),
        'Volume': np.arange(100, 120)
    }
    df = pd.DataFrame(data)
    featured_df = create_features(df)
    assert featured_df['ma5'].isnull().sum() == 4
    assert featured_df['volume_ma5'].isnull().sum() == 4
    assert featured_df['ma20'].isnull().sum() == 19

def test_preprocess_data_pipeline(mock_data_path):
    """Test the entire preprocessing pipeline."""
    target_stocks = ['001']
    start_date = "2022-01-01"
    end_date = "2023-01-10"

    final_df = preprocess_data(mock_data_path, target_stocks, start_date, end_date)

    assert final_df is not None
    assert not final_df.empty
    assert final_df.isnull().sum().sum() == 0
    assert 'ma120' in final_df.columns
    # 120일 이동평균 계산에 필요한 최소 데이터(120) -> 119개 행 NaN 발생
    # dropna()로 인해 119개의 행이 제거됨
    assert len(final_df) == len(pd.date_range(start_date, end_date)) - 119
