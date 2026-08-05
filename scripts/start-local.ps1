# Start ZECT local stack: backend :8020 + Vite :5173 + Electron
# Usage (from repo root):
#   powershell -ExecutionPolicy Bypass -File .\scripts\start-local.ps1
#   powershell -ExecutionPolicy Bypass -File .\scripts\start-local.ps1 -NoElectron
#   powershell -ExecutionPolicy Bypass -File .\scripts\start-local.ps1 -Pull
#   powershell -ExecutionPolicy Bypass -File .\scripts\start-local.ps1 -StopFirst -Pull

param(
  [switch]$NoElectron,
  [switch]$Pull,
  [switch]$StopFirst
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$ElectronDir = Join-Path $Root "electron"
$ApiUrl = "http://127.0.0.1:8020"
$ViteUrl = "http://127.0.0.1:5173"

if ($StopFirst) {
  & (Join-Path $PSScriptRoot "stop-local.ps1")
  Start-Sleep 1
}

if ($Pull) {
  Push-Location $Root
  try {
    Write-Host "Pulling origin/develop..."
    git fetch origin develop
    git pull origin develop
  } finally {
    Pop-Location
  }
}

Set-Content -Path (Join-Path $Frontend ".env.local") -Value ("VITE_API_URL=" + $ApiUrl + "`n") -Encoding utf8

$backendCmd = @(
  "`$env:PYTHONIOENCODING='utf-8'",
  "`$env:PYTHONUTF8='1'",
  "Get-Content '$Backend\.env' -ErrorAction SilentlyContinue | ForEach-Object {",
  "  if (`$_ -match '^([A-Z0-9_]+)=(.*)$') { Set-Item -Path ('env:' + `$matches[1]) -Value `$matches[2] -ErrorAction SilentlyContinue }",
  "}",
  "try { `$env:GITHUB_TOKEN = (gh auth token) } catch {}",
  "Set-Location '$Backend'",
  "py -3.12 -m uvicorn app.main:app --host 127.0.0.1 --port 8020 --reload --reload-dir '$Backend'"
) -join "; "

$frontendCmd = "Set-Location '$Frontend'; npm run dev -- --host 127.0.0.1 --port 5173"

$electronCmd = @(
  "`$env:ZECT_DEV='true'",
  "`$env:NODE_ENV='development'",
  "`$env:ZECT_DEV_URL='$ViteUrl'",
  "Set-Location '$ElectronDir'",
  "npm run start:dev"
) -join "; "

Write-Host "Starting backend on $ApiUrl ..."
Start-Process powershell -ArgumentList @("-NoExit", "-Command", $backendCmd) -WorkingDirectory $Backend

Write-Host "Starting Vite on $ViteUrl ..."
Start-Process powershell -ArgumentList @("-NoExit", "-Command", $frontendCmd) -WorkingDirectory $Frontend

$deadline = (Get-Date).AddSeconds(45)
$ok = $false
do {
  Start-Sleep 1
  try {
    $ok = (Invoke-WebRequest -Uri $ViteUrl -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200
  } catch {
    $ok = $false
  }
} while (-not $ok -and (Get-Date) -lt $deadline)

if (-not $ok) {
  Write-Warning "Vite not ready yet - starting Electron anyway. Refresh if blank."
}

if (-not $NoElectron) {
  Write-Host "Starting Electron..."
  Start-Process powershell -ArgumentList @("-NoExit", "-Command", $electronCmd) -WorkingDirectory $ElectronDir
}

Write-Host ""
Write-Host "ZECT local stack launching:"
Write-Host "  API      $ApiUrl"
Write-Host "  Frontend $ViteUrl  (VITE_API_URL=$ApiUrl)"
Write-Host "  Electron uses $ViteUrl"
Write-Host ""
Write-Host "Stop later with:"
Write-Host "  powershell -ExecutionPolicy Bypass -File .\scripts\stop-local.ps1"
