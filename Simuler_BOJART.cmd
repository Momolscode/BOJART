@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" tools\simulate_jarvis_workflows.py --output "%TEMP%\bojart-workflows-%RANDOM%-%RANDOM%.json"
) else (
  py -3.12 tools\simulate_jarvis_workflows.py --output "%TEMP%\bojart-workflows-%RANDOM%-%RANDOM%.json"
)
set "BOJ_SIM_EXIT=%ERRORLEVEL%"
echo.
echo Simulation uniquement : pas de microphone, rendu navigateur ou imprimante.
pause
exit /b %BOJ_SIM_EXIT%
