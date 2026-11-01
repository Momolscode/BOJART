@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -File "%~dp0Audit_Windows.ps1"
if errorlevel 1 echo Audit non termine. Ne pas desactiver la securite Windows ; faire verifier l'autorisation par le technicien.
pause
