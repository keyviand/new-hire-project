@echo off
cd /d "%~dp0"
echo Starting Everdawn Online co-op server on port 7777...
.venv\Scripts\python.exe coop_server.py --host 0.0.0.0 --port 7777
pause

