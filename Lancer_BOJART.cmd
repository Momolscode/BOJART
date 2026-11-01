@echo off
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" tools\start_jarvis.py %*
) else (
  py -3.12 tools\start_jarvis.py %*
)
if errorlevel 1 pause
