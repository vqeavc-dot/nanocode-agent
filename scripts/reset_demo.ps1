$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

git checkout -- examples/calculator/calculator.py examples/calculator/test_calculator.py 2>$null
Write-Host "Demo files reset. Current calculator files are ready for a fresh run."
