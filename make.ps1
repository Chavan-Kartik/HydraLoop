# Windows task runner. Mirrors the Makefile targets by delegating to the CLI.
# Usage: .\make.ps1 <target>   e.g.  .\make.ps1 demo
param(
    [Parameter(Position = 0)]
    [string]$Target = "help"
)

$ErrorActionPreference = "Stop"
$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

switch ($Target) {
    "setup" {
        & $py -m pip install --upgrade pip
        & $py -m pip install -r requirements-dev.txt
        & $py -m pip install -e .
    }
    "test" { & $py -m pytest tests -v }
    "lint" {
        & $py -m ruff check src tests scripts
        & $py scripts\check_authenticity.py
    }
    "authenticity" { & $py scripts\check_authenticity.py }
    "demo" { & $py -m hydraloop demo }
    "twin" { & $py -m hydraloop twin }
    "attack" { & $py -m hydraloop attack }
    "train" { & $py -m hydraloop train }
    "stack" { & $py -m hydraloop stack }
    "loop" { & $py -m hydraloop loop }
    "report" { & $py scripts\build_reports.py }
    "api" { & $py -m hydraloop api }
    "ui" { Push-Location ui; npm install; npm run dev; Pop-Location }
    default {
        Write-Host "Targets: setup test lint demo twin attack train stack loop report api ui"
    }
}
