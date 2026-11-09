@echo off
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"
if exist "..\..\Lancer_Jarvis.cmd" goto parentlauncher
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" app\consolidated_workbench.py %*
  goto end
)
where py >nul 2>nul
if not errorlevel 1 (
  py -3 app\consolidated_workbench.py %*
  goto end
)
where python >nul 2>nul
if not errorlevel 1 (
  python app\consolidated_workbench.py %*
  goto end
)
echo Python absent. Aucun logiciel installe automatiquement.
echo Ouverture de l'apercu hors ligne. Le service reste a installer par l'integrateur.
start "" "APERCU_STUDIO_M03.html"
pause
exit /b 1
:end
set "BOJART_EXIT=%errorlevel%"
if not "%BOJART_EXIT%"=="0" (
  echo Le lancement local n'a pas abouti. Ne pas desactiver de protection Windows.
  echo Consulter README.md avec le responsable de l'integration.
)
pause
exit /b %BOJART_EXIT%
:parentlauncher
call "..\..\Lancer_Jarvis.cmd" %*
exit /b %errorlevel%
