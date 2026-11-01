@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto venv
where py >nul 2>nul
if not errorlevel 1 goto pylauncher
where python >nul 2>nul
if not errorlevel 1 goto pythonexe
echo Python absent. Aucune restauration effectuee.
pause
exit /b 1
:venv
if "%~1"=="" (
  ".venv\Scripts\python.exe" tools\restore_workspace.py --choose
) else (
  ".venv\Scripts\python.exe" tools\restore_workspace.py %*
)
goto end
:pylauncher
if "%~1"=="" (
  py -3 tools\restore_workspace.py --choose
) else (
  py -3 tools\restore_workspace.py %*
)
goto end
:pythonexe
if "%~1"=="" (
  python tools\restore_workspace.py --choose
) else (
  python tools\restore_workspace.py %*
)
:end
if errorlevel 1 pause
