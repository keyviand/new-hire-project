$ErrorActionPreference = "Stop"
$project = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $project

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python was not found on PATH."
    Write-Host "Install Python 3.11 or 3.12 from https://www.python.org/downloads/"
    exit 1
}

python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe test_game.py

Write-Host ""
Write-Host "Setup complete. Start the game with .\start_game.ps1"

