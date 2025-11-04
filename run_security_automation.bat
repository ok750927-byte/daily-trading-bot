@echo off
REM 운영 자동화/보안 점검 스크립트 예시
REM 1. pip-audit로 의존성 취약점 점검
REM 2. 주요 민감정보 환경변수/권한 점검
REM 3. 자동화 파이프라인 실행

REM 1. pip-audit 설치 및 실행
call D:/codding/daily-trading-bot/daily-trading-bot/venv/Scripts/pip.exe install pip-audit
call D:/codding/daily-trading-bot/daily-trading-bot/venv/Scripts/pip-audit.exe > results/pip_audit_report.txt

REM 2. 환경변수/권한 점검 (예시)
echo [환경변수 점검] > results/env_check_report.txt
set KOREA_APP_KEY > results/env_check_report.txt
set KOREA_APP_SECRET >> results/env_check_report.txt
set KOREA_ACCOUNT_NO >> results/env_check_report.txt
set KOREA_ACCOUNT_PRDT >> results/env_check_report.txt

REM 3. 자동화 파이프라인 실행
call D:/codding/daily-trading-bot/daily-trading-bot/venv/Scripts/python.exe run_auto_pipeline.py
