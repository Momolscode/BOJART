@echo off
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto nopy
py -3 -c "import cadquery,trimesh" >nul 2>nul
if errorlevel 1 goto deps
py -3 app\server.py
pause
exit /b
:nopy
echo Python 3 manque. Ouvrez APERCU_MISSION_01.html pour la visite sans installation.
echo Le responsable de l'integration doit installer les dependances dans un environnement isole.
pause
exit /b 1
:deps
echo CadQuery ou trimesh manque. Aucun logiciel n'a ete installe automatiquement.
echo Ouvrez APERCU_MISSION_01.html ; le guide de reprise est dans README.md.
pause
exit /b 1
