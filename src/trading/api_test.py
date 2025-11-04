"""
간단한 API 테스트 예제
환경변수에서 API 키를 읽어 간단히 출력(실사용시 키는 로그에 남기지 마세요).
"""
import os

def get_api_credentials():
    api_key = os.environ.get('TRADING_API_KEY')
    api_secret = os.environ.get('TRADING_API_SECRET')
    return api_key, api_secret


def main():
    api_key, api_secret = get_api_credentials()
    if not api_key or not api_secret:
        print('경고: API 키/시크릿이 설정되지 않았습니다. 환경변수를 확인하세요.')
    else:
        print('API 키와 시크릿이 환경변수에 설정되어 있습니다. (보안을 위해 출력 생략)')


if __name__ == '__main__':
    main()
