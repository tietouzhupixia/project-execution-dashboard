$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Streamlit = Join-Path $ProjectRoot ".venv\Scripts\streamlit.exe"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Missing local Python environment: $Python. Recreate it with: python -m venv .venv"
}

if (-not (Test-Path -LiteralPath $Streamlit)) {
    throw "Streamlit is not installed in .venv. Run: .\.venv\Scripts\python.exe -m pip install -r requirements.txt"
}

Set-Location -LiteralPath $ProjectRoot
& $Streamlit run app.py

