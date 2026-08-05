# Pull (optional) + stop + start ZECT local stack
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\scripts\restart-local.ps1
#   powershell -ExecutionPolicy Bypass -File .\scripts\restart-local.ps1 -Pull

param([switch]$Pull)

& (Join-Path $PSScriptRoot "start-local.ps1") -StopFirst -Pull:$Pull
