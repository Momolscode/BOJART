@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" apps\jarvis\app\consolidated_workbench.py %*
) else (
  py -3 apps\jarvis\app\consolidated_workbench.py %*
)
if errorlevel 1 pause
