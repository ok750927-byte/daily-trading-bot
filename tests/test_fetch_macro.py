"""
fetch_macro.py 모듈에 대한 테스트
"""
import pandas as pd
from unittest.mock import patch, MagicMock
from data import fetch_macro

def test_get_macro_data_success():
    """거시경제 지표 수집 성공 케이스 테스트"""
    # 모의 데이터프레임 생성
    mock_kospi_df = pd.DataFrame(
        {'Close': [3000, 3010]}, 
        index=pd.DatetimeIndex(['2023-01-02', '2023-01-03'], name='Date')
    )
    mock_usd_df = pd.DataFrame(
        {'Close': [1200, 1210]}, 
        index=pd.DatetimeIndex(['2023-01-02', '2023-01-03'], name='Date')
    )
    
    symbol_map = {'KS11': 'KOSPI', 'USD/KRW': 'USD_KRW'}

    # fdr.DataReader를 모의 객체로 패치
    with patch('data.fetch_macro.fdr.DataReader') as mock_datareader:
        # 호출되는 심볼에 따라 다른 데이터프레임 반환
        mock_datareader.side_effect = lambda symbol, start, end: {
            'KS11': mock_kospi_df,
            'USD/KRW': mock_usd_df
        }[symbol]

        result_df = fetch_macro.get_macro_data(symbol_map, '2023-01-02', '2023-01-03')

        assert not result_df.empty
        assert 'KOSPI' in result_df.columns
        assert 'USD_KRW' in result_df.columns
        assert result_df['KOSPI'].iloc[0] == 3000
        assert result_df['USD_KRW'].iloc[1] == 1210

def test_get_macro_data_partial_failure():
    """일부 지표 수집 실패 시, 성공한 지표만으로 데이터프레임을 생성하는지 테스트"""
    mock_kospi_df = pd.DataFrame(
        {'Close': [3000, 3010]}, 
        index=pd.DatetimeIndex(['2023-01-02', '2023-01-03'], name='Date')
    )
    # 유효하지 않은 심볼에 대해서는 빈 데이터프레임 반환
    mock_empty_df = pd.DataFrame()
    symbol_map = {'KS11': 'KOSPI', 'INVALID': 'INVALID_DATA'}

    with patch('data.fetch_macro.fdr.DataReader') as mock_datareader:
        mock_datareader.side_effect = lambda symbol, start, end: {
            'KS11': mock_kospi_df,
            'INVALID': mock_empty_df
        }[symbol]

        with patch('data.fetch_macro.logger.warning') as mock_log:
            result_df = fetch_macro.get_macro_data(symbol_map, '2023-01-02', '2023-01-03')
            
            # 경고 로그가 한 번 호출되었는지 확인
            mock_log.assert_called_once_with("'INVALID'에 대한 데이터를 찾을 수 없습니다.")
            
            # 결과는 KOSPI 데이터만 포함해야 함
            assert not result_df.empty
            assert 'KOSPI' in result_df.columns
            assert 'INVALID_DATA' not in result_df.columns

def test_get_macro_data_total_failure():
    """모든 지표 수집 실패 시 None을 반환하는지 테스트"""
    symbol_map = {'INVALID1': 'INVALID_DATA1', 'INVALID2': 'INVALID_DATA2'}
    with patch('data.fetch_macro.fdr.DataReader', return_value=pd.DataFrame()):
        with patch('data.fetch_macro.logger.error') as mock_log:
            result = fetch_macro.get_macro_data(symbol_map, '2023-01-02', '2023-01-03')
            assert result is None
            # 최종 에러 로그가 한 번 호출되었는지 확인
            mock_log.assert_called_once_with("수집된 거시경제 지표 데이터가 전혀 없습니다.")

def test_get_macro_data_fdr_not_installed():
    """FinanceDataReader 미설치 시 None을 반환하는지 테스트"""
    symbol_map = {'KS11': 'KOSPI'}
    with patch('data.fetch_macro.fdr', None):
        with patch('data.fetch_macro.logger.error') as mock_log:
            result = fetch_macro.get_macro_data(symbol_map, '2023-01-02', '2023-01-03')
            assert result is None
            mock_log.assert_called_once()
            assert "FinanceDataReader가 설치되어 있지 않습니다" in mock_log.call_args[0][0]

def test_get_macro_data_ffill():
    """데이터 병합 후 ffill이 잘 동작하는지 테스트"""
    # 날짜가 서로 다른 모의 데이터프레임
    mock_df1 = pd.DataFrame({'Close': [100]}, index=pd.DatetimeIndex(['2023-01-02'], name='Date'))
    mock_df2 = pd.DataFrame({'Close': [200]}, index=pd.DatetimeIndex(['2023-01-03'], name='Date'))
    
    symbol_map = {'SYM1': 'A', 'SYM2': 'B'}

    with patch('data.fetch_macro.fdr.DataReader') as mock_datareader:
        mock_datareader.side_effect = [mock_df1, mock_df2]
        
        result_df = fetch_macro.get_macro_data(symbol_map, '2023-01-02', '2023-01-03')
        
        # 2023-01-03의 'A' 컬럼 값이 2023-01-02의 값으로 채워졌는지 확인
        assert result_df.loc[pd.Timestamp('2023-01-03'), 'A'] == 100
