@echo off
setlocal
set PYTHONUTF8=1
set LANGSMITH_TRACING=false
cd /d "%~dp0"
rem Banc de la chaine vocale : rejoue le corpus de prises sur le vrai serveur et le vrai faster-whisper.
rem Aucun micro, aucune imprimante, aucun service distant. Un rapport neuf a chaque passage.
set "PY=py -3.12"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
set "CORPUS=%USERPROFILE%\BOJART\banc-voix\corpus-2026-11-02"
set "MODELE=%USERPROFILE%\BOJART\modeles\whisper-small"
rem Poids deja installes par Installer_Tout_BOJART.cmd (tools\preparer_voix.py) : les reutiliser, sans second telechargement.
set "INSTALLE=%USERPROFILE%\BOJART\modeles\voix\faster-whisper-small-536b0662"
if exist "%INSTALLE%\model.bin" set "MODELE=%INSTALLE%"
set "RAPPORTS=%USERPROFILE%\BOJART\banc-voix\rapports"
if not exist "%RAPPORTS%" mkdir "%RAPPORTS%"
rem Decodage audio de Jarvis (PyAV) verifie d'abord, sans modele : tools\verifier_voix.py.
%PY% tools\verifier_voix.py >nul 2>nul
if errorlevel 1 (
  echo Moteur vocal absent ou decodage audio casse. Lancer : %PY% tools\verifier_voix.py
  echo puis installer : %PY% -m pip install -r jarvis\requirements-voice.txt
  pause
  exit /b 1
)
if not exist "%CORPUS%\corpus.json" (
  echo Corpus absent : extraire corpus-voix-2026-11-02.zip du projet dans %USERPROFILE%\BOJART\banc-voix
  pause
  exit /b 1
)
if not exist "%MODELE%\model.bin" (
  echo Modele faster-whisper small absent dans %MODELE%.
  choice /M "Telecharger le modele epingle (environ 480 Mo) depuis Hugging Face"
  if errorlevel 2 exit /b 1
  %PY% tools\banc_voix.py modele --nom small --dossier "%MODELE%" --je-confirme-le-telechargement
  if errorlevel 1 (
    pause
    exit /b 1
  )
)
echo Mesure en cours : environ 10 a 20 minutes selon le processeur.
%PY% tools\banc_voix.py mesurer --corpus "%CORPUS%" --modele "%MODELE%" --sortie "%RAPPORTS%" --libelle "tour small"
echo Sonde bruit seul : la reconnaissance ne doit inventer aucune commande (environ 5 minutes).
%PY% tools\banc_voix.py bruit --modele "%MODELE%" --sortie "%RAPPORTS%" --libelle "tour small"
echo Rapports dans %RAPPORTS% (JSON et Markdown).
echo Pour les envoyer sur GitHub et les comparer a la mesure du conteneur : Publier_Debrief_BOJART.cmd
pause
