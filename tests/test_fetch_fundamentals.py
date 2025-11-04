"""
fetch_fundamentals.py 모듈에 대한 테스트
"""
import pandas as pd
from unittest.mock import patch, call
from data import fetch_fundamentals

def test_get_market_fundamentals_success():
    """재무 정보 수집 성공 케이스 테스트"""
    # 모의 데이터프레임 생성
    mock_kospi_df = pd.DataFrame({'BPS': [10000], 'PER': [10], 'PBR': [1], 'DIV': [2], 'DPS': [200]}, index=pd.Index(['005930'], name='ticker'))
    mock_kosdaq_df = pd.DataFrame({'BPS': [5000], 'PER': [20], 'PBR': [2], 'DIV': [1], 'DPS': [50]}, index=pd.Index(['068270'], name='ticker'))

    # pykrx의 stock 모듈 자체를 모의 객체로 패치
    with patch('data.fetch_fundamentals.stock') as mock_stock:
        # get_market_fundamental_by_ticker 함수의 반환 값을 순서대로 지정
        mock_stock.get_market_fundamental_by_ticker.side_effect = [mock_kospi_df, mock_kosdaq_df]

        result_df = fetch_fundamentals.get_market_fundamentals('20231027')

        # 함수가 KOSPI와 KOSDAQ에 대해 각각 호출되었는지 확인
        expected_calls = [
            call('20231027', market='KOSPI'),
            call('20231027', market='KOSDAQ')
        ]
        mock_stock.get_market_fundamental_by_ticker.assert_has_calls(expected_calls)

        # 결과 데이터프레임 검증
        assert not result_df.empty
        assert len(result_df) == 2
        assert '시장' in result_df.columns
        assert 'KOSPI' in result_df['시장'].values
        assert 'KOSDAQ' in result_df['시장'].values
        assert '005930' in result_df['티커'].values

def test_get_market_fundamentals_pykrx_not_installed():
    """pykrx 미설치 시 None을 반환하는지 테스트"""
    with patch('data.fetch_fundamentals.stock', None):
        with patch('data.fetch_fundamentals.logger.error') as mock_log:
            result = fetch_fundamentals.get_market_fundamentals('20231027')
            assert result is None
            mock_log.assert_called_once()
            assert "pykrx가 설치되어 있지 않습니다" in mock_log.call_args[0][0]

def test_get_market_fundamentals_api_exception():
    """API 호출 중 예외 발생 시 None을 반환하는지 테스트"""
    with patch('data.fetch_fundamentals.stock') as mock_stock:
        mock_stock.get_market_fundamental_by_ticker.side_effect = Exception("API Error")
        with patch('data.fetch_fundamentals.logger.error') as mock_log:
            result = fetch_fundamentals.get_market_fundamentals('20231027')
            assert result is None
            mock_log.assert_called_once()
            assert "재무 정보 수집 중 예기치 않은 오류 발생" in mock_log.call_args[0][0]

def test_get_market_fundamentals_empty_data():
    """데이터가 없는 경우 (휴장일 등) None을 반환하는지 테스트"""
    empty_df = pd.DataFrame()
    with patch('data.fetch_fundamentals.stock') as mock_stock:
        mock_stock.get_market_fundamental_by_ticker.return_value = empty_df
        with patch('data.fetch_fundamentals.logger.warning') as mock_log:
            result = fetch_fundamentals.get_market_fundamentals('20231028') # 휴장일 가정
            assert result is None
            mock_log.assert_called_once()
            assert "재무 데이터를 찾을 수 없습니다" in mock_log.call_args[0][0]
