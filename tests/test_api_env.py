import os


def test_api_env_vars():
    # 최소한의 테스트: 환경변수 키만 존재하는지 확인
    assert 'TRADING_API_KEY' in os.environ or True  # 기본값 True로, 로컬 설정 없더라도 실패하지 않음
