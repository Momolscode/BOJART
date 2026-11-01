@echo off
setlocal
cd /d "%~dp0"
echo BOJ.ART - Publication privee vers Momolscode/bojart-jarvis
echo Prerequis : Python 3, Git et GitHub CLI connecte a Momolscode.
where py >nul 2>nul
if not errorlevel 1 (
  py -3 PUBLIER_GITHUB.py --delivery "%~dp0." --execute --create-private
) else (
  python PUBLIER_GITHUB.py --delivery "%~dp0." --execute --create-private
)
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" echo Publication non confirmee. Lire le message ci-dessus.
if "%RESULT%"=="0" echo Publication et verification terminees. Voir delivery_result.json.
pause
exit /b %RESULT%
