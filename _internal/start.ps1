$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (!(Test-Path $Python)) {
    python -m venv .venv
}

& $Python -c "import flask, soundcard, openai, dotenv, numpy" 2>$null
if ($LASTEXITCODE -ne 0) {
    & $Python -m pip install --upgrade pip
    & $Python -m pip install -r requirements.txt
}

& $Python -m realtime_translator run
