@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" app\workbench.py
  goto end
)
where py >nul 2>nul
if not errorlevel 1 (
  py -3 app\workbench.py
  goto end
)
where python >nul 2>nul
if not errorlevel 1 (
  python app\workbench.py
  goto end
)
echo Python absent. Aucun logiciel installe automatiquement.
echo Ouverture de l'apercu hors ligne. Le service reste a installer par l'integrateur.
start "" "APERCU_MISSION_02.html"
:end
if errorlevel 1 (
  echo Le lancement local n'a pas abouti. Ne pas desactiver de protection Windows.
  echo Consulter README.md avec le responsable de l'integration.
)
pause
