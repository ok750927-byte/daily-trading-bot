import pandas as pd
from unittest.mock import patch
import logging

from data import fetch_prices

def test_fetch_ohlcv_success():
    """데이터 수집 성공 케이스 테스트"""
    mock_df = pd.DataFrame({
        'Open': [100], 'High': [120], 'Low': [90], 'Close': [110], 'Volume': [1000]
    })
    with patch('data.fetch_prices.fdr.DataReader', return_value=mock_df) as mock_datareader:
        df = fetch_prices.fetch_ohlcv('005930', '2023-01-01', '2023-01-02')
        mock_datareader.assert_called_once_with('005930', '2023-01-01', '2023-01-02')
        pd.testing.assert_frame_equal(df, mock_df)

def test_fetch_ohlcv_fdr_not_installed():
    """FinanceDataReader 미설치 시 None을 반환하는지 테스트"""
    with patch('data.fetch_prices.fdr', None):
        with patch('data.fetch_prices.logger.error') as mock_log:
            result = fetch_prices.fetch_ohlcv('005930')
            assert result is None
            mock_log.assert_called_once()
            assert "FinanceDataReader가 설치되어 있지 않습니다" in mock_log.call_args[0][0]

def test_fetch_ohlcv_api_exception():
    """API 호출 중 예외 발생 시 None을 반환하는지 테스트"""
    with patch('data.fetch_prices.fdr.DataReader', side_effect=Exception("API Error")):
        with patch('data.fetch_prices.logger.error') as mock_log:
            result = fetch_prices.fetch_ohlcv('005930')
            assert result is None
            mock_log.assert_called_once()
            assert "데이터 수집 중 예기치 않은 오류 발생" in mock_log.call_args[0][0]

def test_fetch_ohlcv_empty_dataframe():
    """API가 비어있는 데이터프레임 반환 시 None을 반환하는지 테스트"""
    mock_df = pd.DataFrame()
    with patch('data.fetch_prices.fdr.DataReader', return_value=mock_df):
        with patch('data.fetch_prices.logger.warning') as mock_log:
            result = fetch_prices.fetch_ohlcv('INVALID_TICKER')
            assert result is None
            mock_log.assert_called_once()
            assert "데이터를 찾을 수 없습니다" in mock_log.call_args[0][0]

def test_fetch_ohlcv_missing_columns():
    """필수 컬럼이 누락된 데이터프레임 반환 시 None을 반환하는지 테스트"""
    mock_df = pd.DataFrame({'Open': [100], 'Volume': [1000]}) # 'Close' 등 누락
    with patch('data.fetch_prices.fdr.DataReader', return_value=mock_df):
        with patch('data.fetch_prices.logger.error') as mock_log:
            result = fetch_prices.fetch_ohlcv('005930')
            assert result is None
            mock_log.assert_called_once()
            assert "수집된 데이터에 필수 컬럼" in mock_log.call_args[0][0]
