$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

python -m nanocode.cli "Inspect examples/calculator, ensure divide(a, b) and its pytest coverage exist, make the smallest safe edit if needed, then run python -m pytest examples/calculator and summarize the diff." --verbose --max-steps 16
