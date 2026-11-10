@echo off
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"
echo ============================================================
echo  BOJ.ART Jarvis : debrief de la tour vers GitHub
echo ============================================================
echo Envoie les rapports ecrits par Jarvis : installation, banc, voix, mesures.
echo Rien d'autre ne part : ni media, ni base, ni donnee client.
echo Le dossier personnel, le nom de session et le nom du poste sont retires.
echo La liste exacte est montree avant l'envoi, puis un accord est demande.
echo Branche neuve tour/debrief-... du depot Momolscode/BOJART, jamais main.
echo.
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" tools\publier_debrief.py %*
) else (
  py -3.12 tools\publier_debrief.py %*
)
set "BOJ_DEBRIEF_EXIT=%ERRORLEVEL%"
echo.
pause
exit /b %BOJ_DEBRIEF_EXIT%
