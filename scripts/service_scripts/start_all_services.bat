@echo off
echo ================================
echo Daily Trading Bot 서비스 시작
echo ================================

echo 1. 거래 엔진 시작...
start "Trading Engine" cmd /k "cd /d "d:\codding\daily-trading-bot\daily-trading-bot" && "d:\codding\daily-trading-bot\daily-trading-bot\venv314\Scripts\python.exe" services/trading-engine_service.py"

timeout /t 5

echo 2. 메트릭 서버 시작...
start "Metrics Server" cmd /k "cd /d "d:\codding\daily-trading-bot\daily-trading-bot" && "d:\codding\daily-trading-bot\daily-trading-bot\venv314\Scripts\python.exe" services/metrics-server_service.py"

timeout /t 3

echo 3. 대시보드 시작...
start "Dashboard" cmd /k "cd /d "d:\codding\daily-trading-bot\daily-trading-bot" && "d:\codding\daily-trading-bot\daily-trading-bot\venv314\Scripts\python.exe" services/dashboard_service.py"

echo.
echo 모든 서비스가 시작되었습니다.
echo - 거래 엔진: 백그라운드 실행
echo - 메트릭 서버: http://localhost:8000
echo - 대시보드: http://localhost:8501
echo.
pause
