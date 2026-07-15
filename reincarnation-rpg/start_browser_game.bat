@echo off
cd /d "%~dp0"
echo Starting Everdawn Online browser game...
echo Friends on your network can open http://YOUR_IP:8000
echo WARNING: This opens port 8000 to your local network. Do not port-forward it.
choice /C YN /M "Continue with LAN access"
if errorlevel 2 exit /b 1
echo.
.venv\Scripts\python.exe browser_server.py --host 0.0.0.0 --port 8000
pause
