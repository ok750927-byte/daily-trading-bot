@echo off
REM AI Trading Bot - Docker 빌드 및 실행 스크립트 (Windows)

echo 🐳 AI Trading Bot Docker 관리 스크립트
echo.

:menu
echo 1. Docker 이미지 빌드
echo 2. 개발 환경 실행
echo 3. 운영 환경 실행
echo 4. 컨테이너 중지
echo 5. 로그 보기
echo 6. 시스템 정리
echo 7. 종료
echo.
set /p choice=선택하세요 (1-7):

if "%choice%"=="1" goto build
if "%choice%"=="2" goto dev
if "%choice%"=="3" goto prod
if "%choice%"=="4" goto stop
if "%choice%"=="5" goto logs
if "%choice%"=="6" goto cleanup
if "%choice%"=="7" goto exit

echo 잘못된 선택입니다.
goto menu

:build
echo.
echo 📦 Docker 이미지 빌드 중...
docker build -f Dockerfile.production -t ai-trading-bot:latest .
if %errorlevel% neq 0 (
    echo ❌ 빌드 실패
    pause
    goto menu
)
echo ✅ 빌드 완료
pause
goto menu

:dev
echo.
echo 🚀 개발 환경 실행 중...
if not exist .env (
    echo ⚠️ .env 파일이 없습니다. .env.template을 참고하여 생성하세요.
    pause
    goto menu
)
docker-compose -f docker-compose.yml up -d
if %errorlevel% neq 0 (
    echo ❌ 개발 환경 실행 실패
    pause
    goto menu
)
echo ✅ 개발 환경 실행 완료
echo 🌐 대시보드: http://localhost:8501
pause
goto menu

:prod
echo.
echo 🏭 운영 환경 실행 중...
if not exist .env (
    echo ❌ .env 파일이 필요합니다.
    pause
    goto menu
)
docker-compose -f docker-compose.production.yml up -d
if %errorlevel% neq 0 (
    echo ❌ 운영 환경 실행 실패
    pause
    goto menu
)
echo ✅ 운영 환경 실행 완료
echo 🌐 대시보드: http://localhost:8501
echo 📊 Grafana: http://localhost:3000
pause
goto menu

:stop
echo.
echo 🛑 컨테이너 중지 중...
docker-compose -f docker-compose.yml down
docker-compose -f docker-compose.production.yml down
echo ✅ 컨테이너 중지 완료
pause
goto menu

:logs
echo.
echo 📋 로그 선택:
echo 1. 전체 로그
echo 2. 거래 엔진 로그
echo 3. 대시보드 로그
echo 4. 에러 로그만
set /p logchoice=선택하세요 (1-4):

if "%logchoice%"=="1" docker-compose logs -f
if "%logchoice%"=="2" docker-compose logs -f trading-bot
if "%logchoice%"=="3" docker-compose logs -f trading-bot | findstr streamlit
if "%logchoice%"=="4" docker-compose logs -f | findstr -i error
pause
goto menu

:cleanup
echo.
echo 🧹 시스템 정리 중...
echo 중지된 컨테이너 제거...
docker container prune -f
echo 사용하지 않는 이미지 제거...
docker image prune -f
echo 사용하지 않는 볼륨 제거...
docker volume prune -f
echo ✅ 정리 완료
pause
goto menu

:exit
echo.
echo 👋 스크립트를 종료합니다.
exit /b 0
