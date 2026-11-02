@echo off
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" tools\diagnose_environment.py --save --summary %*
) else (
  py -3.12 tools\diagnose_environment.py --save --summary %*
)
set "BOJART_DIAGNOSTIC_EXIT=%ERRORLEVEL%"
pause
exit /b %BOJART_DIAGNOSTIC_EXIT%
