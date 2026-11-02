@echo off
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"
echo Mesures dans des memoires temporaires, puis essai du modele local speed.
echo Les rapports restent dans le dossier BOJART\benchmarks de votre profil.
call :python --mode memory
if errorlevel 1 goto failed
call :python --mode models --profile speed
if errorlevel 1 goto failed
echo Mesures terminees. Lire les rapports JSON et leurs limites.
pause
exit /b 0
:failed
echo Un controle a echoue. Consulter le rapport ou le message ci-dessus.
pause
exit /b 1
:python
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" tools\benchmark_jarvis.py %*
) else (
  py -3.12 tools\benchmark_jarvis.py %*
)
exit /b %errorlevel%
