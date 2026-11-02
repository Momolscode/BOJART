@echo off
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"
set "BOJ_BANC_DIR=%USERPROFILE%\BOJART\banc"
if not exist "%BOJ_BANC_DIR%" mkdir "%BOJ_BANC_DIR%"
set "BOJ_BANC_ID=%RANDOM%%RANDOM%"
echo Banc de simulation BOJ.ART : tests, scenarios HTTP, controles Windows.
echo Aucun micro, moniteur physique ni imprimante n'est utilise.
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" tools\banc_preinstallation.py --output "%BOJ_BANC_DIR%\banc-%BOJ_BANC_ID%.json" --markdown "%BOJ_BANC_DIR%\banc-%BOJ_BANC_ID%.md" %*
) else (
  py -3.12 tools\banc_preinstallation.py --output "%BOJ_BANC_DIR%\banc-%BOJ_BANC_ID%.json" --markdown "%BOJ_BANC_DIR%\banc-%BOJ_BANC_ID%.md" %*
)
set "BOJ_BANC_EXIT=%ERRORLEVEL%"
echo.
echo Rapports dans %BOJ_BANC_DIR%
pause
exit /b %BOJ_BANC_EXIT%
