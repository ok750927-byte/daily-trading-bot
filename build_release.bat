@echo off
REM Build release exe and place into dist_release
setlocal enabledelayedexpansion
python -m PyInstaller --onefile run_gui.py --name daily_trading_gui --distpath dist_release --noconfirm --console
nif %ERRORLEVEL% neq 0 (
  echo PyInstaller build failed with error %ERRORLEVEL%
  exit /b %ERRORLEVEL%
)
necho Build complete. See dist_release\\daily_trading_gui.exe
endlocal
