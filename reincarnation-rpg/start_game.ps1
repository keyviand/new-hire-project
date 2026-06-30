$ErrorActionPreference = "Stop"
$project = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $project
& .\.venv\Scripts\python.exe game.py

