@echo off
echo ================================
echo Daily Trading Bot 서비스 상태
echo ================================

echo 거래 엔진 로그 (최근 10줄):
type "d:\codding\daily-trading-bot\daily-trading-bot\logs\trading-engine.log" | find /v "" | more +0 2>nul
if errorlevel 1 echo [로그 파일 없음]

echo.
echo 메트릭 서버 상태 확인:
curl -s http://localhost:8000/health 2>nul
if errorlevel 1 echo [메트릭 서버 연결 실패]

echo.
echo 대시보드 상태 확인:
curl -s http://localhost:8501 2>nul | find "Streamlit" >nul
if errorlevel 1 (
    echo [대시보드 연결 실패]
) else (
    echo [대시보드 정상 실행 중]
)

echo.
pause
