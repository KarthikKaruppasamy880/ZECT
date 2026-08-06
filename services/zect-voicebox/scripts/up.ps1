# Bring up ZECT Voicebox (:17493) + upstream Voicebox (:17494).
# Mentrix: CHATTERBOX_BASE_URL=http://127.0.0.1:17493
param(
  [switch]$SkipUpstreamBuild,
  [switch]$ZectOnly
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
Set-Location $root

function Test-Docker {
  try {
    docker info 1>$null 2>$null
    return ($LASTEXITCODE -eq 0)
  } catch {
    return $false
  }
}

if (-not (Test-Docker)) {
  Write-Host @"
Docker is not running.

Start Docker Desktop or Rancher Desktop (dockerd), then re-run this script.
Meanwhile you can run ZECT Voicebox alone (upstream offline → empty profiles,
Mentrix still sees engine online on :17493):

  cd services\zect-voicebox
  `$env:ZECT_VOICEBOX_UPSTREAM_URL='http://127.0.0.1:17494'
  python -m uvicorn app.main:app --host 127.0.0.1 --port 17493

For real clone TTS you need upstream Voicebox answering on :17494.
"@
  exit 1
}

& (Join-Path $PSScriptRoot "clone-upstream.ps1")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$compose = Join-Path $root "docker-compose.zect-voicebox.yml"
if (-not (Test-Path $compose)) {
  throw "Missing $compose"
}

if ($ZectOnly) {
  Write-Host "Starting zect-voicebox only…"
  docker compose -f $compose up -d --build zect-voicebox
} else {
  Write-Host "Building and starting voicebox-upstream + zect-voicebox…"
  docker compose -f $compose up -d --build
}

$deadline = (Get-Date).AddMinutes(5)
$ok = $false
while ((Get-Date) -lt $deadline) {
  try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:17493/profiles" -UseBasicParsing -TimeoutSec 3
    if ($r.StatusCode -lt 500) {
      $ok = $true
      break
    }
  } catch {
    Start-Sleep -Seconds 3
  }
  Start-Sleep -Seconds 2
}

if (-not $ok) {
  Write-Host "ZECT Voicebox did not answer /profiles in time. Check: docker compose -f docker-compose.zect-voicebox.yml logs"
  exit 2
}

Write-Host @"

ZECT Voicebox is up: http://127.0.0.1:17493/profiles
Health:              http://127.0.0.1:17493/health

Set in backend/.env (do not commit):
  CHATTERBOX_BASE_URL=http://127.0.0.1:17493

Restart the ZECT API, then Companion → Voice → Test speak with your clone.
Upstream Voicebox (models) may still be downloading — first generate can be slow.
"@
