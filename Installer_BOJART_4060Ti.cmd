@echo off
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"
echo Profil BOJ.ART : RTX 4060 Ti 8 Go, Qwen3.5 4B et memoire locale.
echo Prerequis : Python 3.12 et Ollama installe et demarre.
echo Cette installation telecharge les deux modeles manquants et les teste.
py -3.12 tools\prepare_installation.py --model-profile speed --download-models
if errorlevel 1 (
  echo Installation interrompue. Consulter le message ci-dessus.
  pause
  exit /b 1
)
echo Installation terminee. Ouvrir Lancer_BOJART.cmd.
pause
exit /b 0
