@echo off
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"
echo ============================================================
echo  BOJ.ART Jarvis : installation complete de la tour
echo ============================================================
echo Verifie puis installe, si besoin : Python 3.12, Ollama, FFmpeg, Git,
echo Jarvis complet (memoire, CAO, LangGraph, voix, figurine) depuis le
echo verrou Windows, la voix prete a l'emploi (poids small ~470 Mo),
echo les modeles locaux du profil speed, puis lance le banc.
echo Aucune imprimante pilotee, rien de publie, rien d'achete.
echo.
set "BOJ_PY="
call :trouver_python
if defined BOJ_PY goto :installer
where winget >nul 2>&1
if errorlevel 1 goto :sans_winget
choice /c ON /m "Python 3.12 est absent. L'installer maintenant avec winget"
if errorlevel 2 goto :refus
winget install --id Python.Python.3.12 --exact --source winget --accept-package-agreements --accept-source-agreements
call :trouver_python
if not defined BOJ_PY goto :relancer

:installer
"%BOJ_PY%" tools\installer_tout.py %*
set "BOJ_EXIT=%ERRORLEVEL%"
echo.
pause
exit /b %BOJ_EXIT%

:trouver_python
for /f "delims=" %%P in ('py -3.12 -c "import sys; print(sys.executable)" 2^>nul') do set "BOJ_PY=%%P"
if defined BOJ_PY exit /b 0
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "BOJ_PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if defined BOJ_PY exit /b 0
if exist "%ProgramFiles%\Python312\python.exe" set "BOJ_PY=%ProgramFiles%\Python312\python.exe"
exit /b 0

:sans_winget
echo Python 3.12 est absent et winget n'est pas disponible.
echo Installer Python 3.12 depuis https://www.python.org/downloads/ puis relancer ce fichier.
pause
exit /b 2

:refus
echo Rien n'a ete installe.
pause
exit /b 3

:relancer
echo Python 3.12 vient d'etre installe mais cette fenetre ne le voit pas encore.
echo Fermer cette fenetre puis relancer Installer_Tout_BOJART.cmd.
pause
exit /b 2
