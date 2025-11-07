@echo off
echo ================================
echo Daily Trading Bot 서비스 중지
echo ================================

echo Python 프로세스 확인 및 종료...
taskkill /f /im python.exe 2>nul
taskkill /f /im streamlit.exe 2>nul

echo 포트 사용 프로세스 확인...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8000" ^| find "LISTENING"') do (
    echo 포트 8000 프로세스 (PID: %%a) 종료 중...
    taskkill /f /pid %%a 2>nul
)

for /f "tokens=5" %%a in ('netstat -aon ^| find ":8501" ^| find "LISTENING"') do (
    echo 포트 8501 프로세스 (PID: %%a) 종료 중...
    taskkill /f /pid %%a 2>nul
)

echo.
echo 모든 서비스가 중지되었습니다.
pause
