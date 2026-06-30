$ErrorActionPreference = "Stop"
$project = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $project

Write-Host "Starting Nova..."
Write-Host "Open http://127.0.0.1:8000 in your browser."
Write-Host "Keep this PowerShell window open while chatting."
Write-Host ""

& .\.venv\Scripts\python.exe web_app.py

