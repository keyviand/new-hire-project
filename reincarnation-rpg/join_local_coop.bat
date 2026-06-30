@echo off
cd /d "%~dp0"
set /p PLAYER_NAME=Character name: 
.venv\Scripts\python.exe game.py --online --host 127.0.0.1 --port 7777 --name "%PLAYER_NAME%"
pause

