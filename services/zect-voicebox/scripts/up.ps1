# Bring up ZECT Voicebox (:17493) + upstream Voicebox (:17494).
# Mentrix: CHATTERBOX_BASE_URL=http://127.0.0.1:17493
# Requires Rancher Desktop (dockerd/moby) or Docker Desktop.
param(
  [switch]$SkipUpstreamBuild,
  [switch]$ZectOnly
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
Set-Location $root

function Test-Docker {
  $prev = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    $null = docker info 2>&1
    return ($LASTEXITCODE -eq 0)
  } catch {
    return $false
  } finally {
    $ErrorActionPreference = $prev
  }
}

if (-not (Test-Docker)) {
  Write-Host @"
Docker daemon is not reachable (docker info failed).

Rancher Desktop:
  1. Open Rancher Desktop and wait until the VM is Running
  2. Preferences -> Container Engine -> use dockerd (moby), not containerd-only
  3. If docker still points at Docker Desktop, run:  docker context use default
  4. Re-run this script

Docker Desktop: start the app and wait until the whale icon is idle.

Meanwhile you can run ZECT Voicebox alone (upstream offline = empty profiles,
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

# Prefer ZectOnly / SkipUpstreamBuild when full upstream image build is too heavy.
$useZectOnly = $ZectOnly -or $SkipUpstreamBuild
if ($useZectOnly) {
  Write-Host "Starting zect-voicebox only (no upstream ML build; Mentrix can go online on :17493)..."
  $env:ZECT_VOICEBOX_UPSTREAM_URL = "http://host.docker.internal:17494"
  docker compose -f $compose up -d --build --no-deps zect-voicebox
} else {
  Write-Host "Building and starting voicebox-upstream + zect-voicebox (Rancher/Docker, profile full)..."
  $env:ZECT_VOICEBOX_UPSTREAM_URL = "http://voicebox-upstream:17493"
  docker compose -f $compose --profile full up -d --build
  if ($LASTEXITCODE -ne 0) {
    Write-Host "Full compose failed - falling back to zect-voicebox only..."
    $env:ZECT_VOICEBOX_UPSTREAM_URL = "http://host.docker.internal:17494"
    docker compose -f $compose up -d --build --no-deps zect-voicebox
  }
}

$deadline = (Get-Date).AddMinutes(5)
$ok = $false
$healthJson = $null
while ((Get-Date) -lt $deadline) {
  try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:17493/profiles" -UseBasicParsing -TimeoutSec 3
    if ($r.StatusCode -lt 500) {
      $ok = $true
      try {
        $h = Invoke-WebRequest -Uri "http://127.0.0.1:17493/health" -UseBasicParsing -TimeoutSec 3
        $healthJson = $h.Content
      } catch {
        # ignore health probe failure
      }
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

$upstreamNote = "upstream_online unknown - open /health"
if ($healthJson) {
  $upstreamNote = $healthJson
}

Write-Host @"

ZECT Voicebox is up: http://127.0.0.1:17493/profiles
Root:                http://127.0.0.1:17493/
Health:              http://127.0.0.1:17493/health
$upstreamNote

Set in backend/.env (do not commit):
  CHATTERBOX_BASE_URL=http://127.0.0.1:17493

Restart the ZECT API, then Companion -> Voice -> Test speak with your clone.
Upstream Voicebox (models) may still be downloading - first generate can be slow.
Use -ZectOnly if upstream build is too heavy; Mentrix can still go online.
"@
