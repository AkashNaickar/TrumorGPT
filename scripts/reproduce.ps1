# Reproduce the TrumorGPT reproduction end-to-end.
# Usage:  pwsh -File scripts/reproduce.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "== 1. Create venv (Python 3.12) =="
if (-not (Test-Path ".venv")) {
    uv venv --python 3.12 .venv
}
$py = ".venv\Scripts\python.exe"

Write-Host "== 2. Install dependencies =="
uv pip install --python $py -r requirements.txt
uv pip install --python $py -r requirements-dev.txt

Write-Host "== 3. Fetch LIAR (PolitiFact-derived) data =="
if (-not (Test-Path "data\liar\train.tsv")) {
    New-Item -ItemType Directory -Force -Path "data\liar" | Out-Null
    $base = "https://raw.githubusercontent.com/thiagorainmaker77/liar_dataset/master"
    foreach ($s in @("train", "valid", "test")) {
        Invoke-WebRequest -Uri "$base/$s.tsv" -OutFile "data\liar\$s.tsv"
    }
}

Write-Host "== 4. Build evaluation sets =="
& $py scripts\build_eval_sets.py

Write-Host "== 5. Run tests =="
& $py scripts\run_tests.py

Write-Host "== 6. Run full evaluation (writes results/) =="
$env:TRUMORGPT_OFFLINE = "1"
& $py scripts\evaluate.py all

Write-Host "== 7. Error analysis =="
& $py scripts\error_analysis.py

Write-Host "Done. See results\metrics.json and results\figures\."
