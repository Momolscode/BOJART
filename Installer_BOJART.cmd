@echo off
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"
py -3.12 tools\prepare_installation.py %*
if errorlevel 1 (
  echo Installation interrompue. Consulter le message ci-dessus.
) else (
  echo Installation terminee. Ouvrir Lancer_BOJART.cmd.
)
pause
