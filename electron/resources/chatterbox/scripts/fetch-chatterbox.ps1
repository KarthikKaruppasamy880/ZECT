# Optional: download a private Chatterbox/Voicebox sidecar zip into bin/.
# Usage:
#   $env:CHATTERBOX_BUNDLE_URL = "https://your-artifacts/chatterbox-win-x64.zip"
#   powershell -File electron/resources/chatterbox/scripts/fetch-chatterbox.ps1
#
# ZECT does not host third-party ML weights. Point CHATTERBOX_BUNDLE_URL at
# your licensed/internal artifact.

$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
# scripts/ -> chatterbox/ -> resources/  => we want chatterbox/
$ChatterboxRoot = Split-Path $PSScriptRoot -Parent
$BinDir = Join-Path $ChatterboxRoot "bin"
$Url = $env:CHATTERBOX_BUNDLE_URL

if (-not $Url) {
  Write-Host "CHATTERBOX_BUNDLE_URL is not set."
  Write-Host "Set it to a zip that contains the engine binary, then re-run."
  Write-Host "Or manually copy chatterbox-server.exe / Voicebox.exe into:`n  $BinDir"
  exit 1
}

New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
$Zip = Join-Path $env:TEMP ("zect-chatterbox-" + [guid]::NewGuid().ToString() + ".zip")
Write-Host "Downloading $Url ..."
Invoke-WebRequest -Uri $Url -OutFile $Zip
Write-Host "Extracting to $BinDir ..."
Expand-Archive -Path $Zip -DestinationPath $BinDir -Force
Remove-Item $Zip -Force
Write-Host "Done. Bin contents:"
Get-ChildItem $BinDir | ForEach-Object { Write-Host ("  " + $_.Name) }
