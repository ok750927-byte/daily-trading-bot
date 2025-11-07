@echo off
chcp 65001 > nul

REM =============================================
REM 일일 트레이딩 봇 대시보드를 실행합니다 (개선된 안전성)
REM - venv가 있으면 venv의 python을 사용합니다.
REM - venv가 없으면 시스템 python을 찾아 사용합니다.
REM - 기존 로그를 백업하고 새 로그에 실행 결과를 기록합니다.
REM =============================================

REM 이 배치 파일이 있는 디렉토리를 가져옵니다. (끝에 \ 포함)
set "CURRENT_DIR=%~dp0"

REM 프로젝트 루트 디렉토리
set "PROJECT_ROOT=%CURRENT_DIR%"

REM 로그 파일 경로
set "LOG_FILE=%PROJECT_ROOT%dashboard_run.log"

REM 기본 가상환경 Python 경로(가정)
set "VENV_PY=%PROJECT_ROOT%venv\Scripts\python.exe"

echo ==================================================
echo  일일 트레이딩 봇 대시보드를 시작합니다...
echo ==================================================
echo.
echo  프로젝트 경로: %PROJECT_ROOT%
echo  예상 venv 파이썬: %VENV_PY%
echo.

REM 현재 디렉토리를 프로젝트 루트로 변경합니다.
cd /d "%PROJECT_ROOT%"

REM 이전 로그 파일이 있으면 백업
if exist "%LOG_FILE%" (
	move /Y "%LOG_FILE%" "%LOG_FILE%.bak" >nul 2>&1
)

echo [%date% %time%] 대시보드 실행 시작... > "%LOG_FILE%"

REM 가상환경 Python 사용 우선
if exist "%VENV_PY%" (
	set "PYTHON_EXE=%VENV_PY%"
) else (
	REM venv가 없으면 시스템 python을 찾음
	for /f "usebackq tokens=*" %%i in (`where python 2^>nul`) do (
		set "PYTHON_EXE=%%i"
		goto :found_python
	)
	echo Python 실행파일을 찾을 수 없습니다. 가상환경을 만들거나 Python을 설치하세요. >> "%LOG_FILE%"
	echo Python 실행파일을 찾을 수 없습니다. 가상환경을 만들거나 Python을 설치하세요.
	pause
	exit /b 1
)

:found_python
echo 사용 중인 Python: %PYTHON_EXE% >> "%LOG_FILE%"

REM 실행할 모듈 또는 파일 확인
if exist "%PROJECT_ROOT%src\gui\trading_dashboard.py" (
	REM 패키지 구조가 불확실할 때는 직접 파일 실행 시도
	echo 실행 명령: "%PYTHON_EXE%" -m src.gui.trading_dashboard (우선) >> "%LOG_FILE%"
	"%PYTHON_EXE%" -m src.gui.trading_dashboard >> "%LOG_FILE%" 2>&1 || (
		echo - 모듈 실행 실패, 파일 직접 실행 시도 >> "%LOG_FILE%"
		"%PYTHON_EXE%" "%PROJECT_ROOT%src\gui\trading_dashboard.py" >> "%LOG_FILE%" 2>&1
	)
) else (
	echo 대시보드 모듈/파일을 찾을 수 없습니다: %PROJECT_ROOT%src\gui\trading_dashboard.py >> "%LOG_FILE%"
	echo 대시보드 모듈/파일을 찾을 수 없습니다: %PROJECT_ROOT%src\gui\trading_dashboard.py
	pause
	exit /b 2
)

REM 실행 결과 확인
set "EXIT_CODE=%ERRORLEVEL%"
echo [%date% %time%] 대시보드 프로세스 종료 코드: %EXIT_CODE% >> "%LOG_FILE%"

if not "%EXIT_CODE%"=="0" (
	echo ================================================== >> "%LOG_FILE%"
	echo  대시보드 실행 중 오류 발생(코드 %EXIT_CODE%). 로그를 확인하세요: %LOG_FILE% >> "%LOG_FILE%"
	echo ==================================================
	echo  대시보드 실행 중 오류가 발생했습니다. 로그 파일을 확인하세요: %LOG_FILE%
) else (
	echo ================================================== >> "%LOG_FILE%"
	echo  대시보드가 정상적으로 종료되었습니다. >> "%LOG_FILE%"
	echo ==================================================
	echo  대시보드가 정상적으로 종료되었습니다.
)

pause
