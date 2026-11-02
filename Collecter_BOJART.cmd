@echo off
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"
echo Collecte guidee BOJ.ART : videos, photos, documents et exports.
echo Tes dossiers sont copies et verifies, jamais modifies, deplaces ni publies.
echo.
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" tools\collecte_guidee.py %*
) else (
  py -3.12 tools\collecte_guidee.py %*
)
set "BOJ_EXIT=%ERRORLEVEL%"
echo.
pause
exit /b %BOJ_EXIT%
