@echo off
cd /d "%~dp0"
echo Starting Everdawn Online co-op server on port 7777...
echo WARNING: This opens port 7777 to your local network. Do not port-forward it.
choice /C YN /M "Continue with LAN access"
if errorlevel 2 exit /b 1
.venv\Scripts\python.exe coop_server.py --host 0.0.0.0 --port 7777
pause

