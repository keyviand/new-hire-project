@echo off
cd /d "%~dp0"
echo Starting Everdawn Online browser game...
echo Friends on your network can open http://YOUR_IP:8000
echo.
.venv\Scripts\python.exe browser_server.py --host 0.0.0.0 --port 8000
pause
