import pandas as pd
from unittest.mock import patch, MagicMock
from data import fetch_prices

@patch('data.fetch_prices.fdr')
def test_fetch_ohlcv_with_mock(mock_fdr):
    # fdr.DataReader가 특정 DataFrame을 반환하도록 설정
    # provide full OHLCV columns so function returns the DataFrame
    mock_df = pd.DataFrame({
        'Open': [100, 110, 115],
        'High': [110, 120, 125],
        'Low': [90, 100, 105],
        'Close': [100, 110, 120],
        'Volume': [1000, 1200, 1100]
    })
    mock_fdr.DataReader.return_value = mock_df

    # 함수 호출
    df = fetch_prices.fetch_ohlcv('005930')

    # 검증
    mock_fdr.DataReader.assert_called_with('005930', None, None)
    pd.testing.assert_frame_equal(df, mock_df)

@patch('data.fetch_prices.fdr', None)
def test_fetch_ohlcv_no_fdr():
    # fdr이 설치되지 않은 상황을 시뮬레이션
    with patch('data.fetch_prices.logger.error') as mock_log:
        result = fetch_prices.fetch_ohlcv('005930')
        assert result is None
        mock_log.assert_called_once()
