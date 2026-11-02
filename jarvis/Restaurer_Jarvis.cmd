@echo off
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"
if exist "..\tools\start_jarvis.py" if exist "..\.venv\Scripts\python.exe" goto rootvenv
if exist ".venv\Scripts\python.exe" goto venv
where py >nul 2>nul
if not errorlevel 1 goto pylauncher
where python >nul 2>nul
if not errorlevel 1 goto pythonexe
echo Python absent. Aucune restauration effectuee.
pause
exit /b 1
:rootvenv
if "%~1"=="" (
  "..\.venv\Scripts\python.exe" tools\restore_workspace.py --choose
) else (
  "..\.venv\Scripts\python.exe" tools\restore_workspace.py %*
)
goto end
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
set "BOJART_EXIT=%errorlevel%"
if not "%BOJART_EXIT%"=="0" pause
exit /b %BOJART_EXIT%
