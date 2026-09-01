param(
    [Parameter(Mandatory=$true)]
    [string]$Name,
    [Parameter(Mandatory=$true)]
    [string]$VideoPath
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path $VideoPath)) {
    throw "Video file not found: $VideoPath"
}

$staging = Join-Path $root "submission"
$zipPath = Join-Path $root "$Name.zip"
New-Item -ItemType Directory -Force -Path $staging | Out-Null
Copy-Item README.txt (Join-Path $staging "README.txt") -Force
Copy-Item $VideoPath (Join-Path $staging "demo.mp4") -Force
if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}
Compress-Archive -Path (Join-Path $staging "*") -DestinationPath $zipPath
Write-Host "Created $zipPath"
