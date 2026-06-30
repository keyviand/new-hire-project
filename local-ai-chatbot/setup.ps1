$ErrorActionPreference = "Stop"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python was not found."
    Write-Host "Install Python 3.11 or 3.12 from https://www.python.org/downloads/"
    Write-Host "During installation, select: Add python.exe to PATH"
    exit 1
}

python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cu128
& .\.venv\Scripts\python.exe test_model.py

Write-Host ""
Write-Host "Setup complete. Start a small training run with:"
Write-Host '.\.venv\Scripts\python.exe train.py --steps 500'
