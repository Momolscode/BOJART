@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" apps\jarvis\app\consolidated_workbench.py %*
  goto end
)
where py >nul 2>nul
if not errorlevel 1 (
  py -3 apps\jarvis\app\consolidated_workbench.py %*
  goto end
)
where python >nul 2>nul
if not errorlevel 1 (
  python apps\jarvis\app\consolidated_workbench.py %*
  goto end
)
echo Python absent. Consulter docs\m05\RELEASE_M05.md pour preparer les dependances.
echo Aucun logiciel n'a ete installe automatiquement.
pause
exit /b 1
:end
if errorlevel 1 pause
