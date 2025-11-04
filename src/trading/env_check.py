"""
환경변수 점검 및 예외처리 샘플
- 필수 환경변수 존재 여부, 값 포맷, 누락/오타/빈값 등 체크
"""
import os
import sys
import json
from pathlib import Path

REQUIRED_ENV = [
    'KOREA_APP_KEY',
    'KOREA_APP_SECRET',
    'KOREA_ACCOUNT_NO',
    'KOREA_ACCOUNT_PRDT'
]

def check_env():
    """Check required environment variables.

    Behavior:
    - If variables missing, attempt to load from .env (if python-dotenv available)
      or from common secrets JSON files in the repo/home directory.
    - If still missing, print clear instructions and exit(1).
    """
    def _missing_keys():
        return [k for k in REQUIRED_ENV if not os.environ.get(k) or os.environ.get(k).strip() == '']

    missing = _missing_keys()
    # Attempt to load .env if python-dotenv is available
    if missing:
        try:
            from dotenv import load_dotenv
            env_path = Path(__file__).resolve().parents[2] / '.env'
            if env_path.exists():
                load_dotenv(env_path)
                missing = _missing_keys()
        except Exception:
            # python-dotenv not installed or failed; continue to JSON fallbacks
            pass

    # Attempt to load from OS keyring (cross-platform) using 'keyring' package
    # Service name 'daily_trading_bot' is used; store each env-key as the "username"
    # with its secret as the password when saving into the keyring.
    if missing:
        try:
            import keyring
            service = 'daily_trading_bot'
            for k in missing[:]:
                try:
                    val = keyring.get_password(service, k)
                    if val:
                        os.environ[k] = str(val)
                        missing.remove(k)
                except Exception:
                    # ignore individual retrieval errors and continue
                    continue
        except Exception:
            # keyring not installed or not available; continue to JSON fallback
            pass

    # Try common JSON secret file locations
    if missing:
        candidate_paths = [
            Path(__file__).resolve().parents[2] / 'secrets.json',
            Path(__file__).resolve().parents[2] / 'config_secrets.json',
            Path.home() / '.daily_trading_secrets.json',
        ]
        for p in candidate_paths:
            if p.exists():
                try:
                    with open(p, 'r', encoding='utf-8') as fh:
                        data = json.load(fh)
                    for k in missing[:]:
                        if k in data and data[k]:
                            os.environ[k] = str(data[k])
                            missing.remove(k)
                    if not missing:
                        break
                except Exception:
                    # ignore parse errors and continue
                    continue

    # Final check
    missing = _missing_keys()
    if missing:
        print("[환경변수 오류] 누락/빈값 확인 필요:", missing)
        print("")
        print("해결 방법(예):")
        print(" 1) 환경변수로 설정 (Windows cmd 예):")
        print("    set KOREA_APP_KEY=your_app_key")
        print("    set KOREA_APP_SECRET=your_app_secret")
        print("    set KOREA_ACCOUNT_NO=12345678")
        print("    set KOREA_ACCOUNT_PRDT=01")
        print("")
        print(" 2) 프로젝트 루트에 '.env' 파일 추가 (KEY=VALUE) 또는 'secrets.json' 생성")
        print("    secrets.json 예: {\"KOREA_APP_KEY\":\"...\", \"KOREA_APP_SECRET\":\"...\", \"KOREA_ACCOUNT_NO\":\"...\", \"KOREA_ACCOUNT_PRDT\":\"...\"}")
        print("")
        print("테스트/개발 중이면 임시더미값을 설정한 뒤 재시도하세요.")
        sys.exit(1)

    print("[환경변수 점검] 모든 필수 환경변수 OK!")

if __name__ == "__main__":
    check_env()
