# Bring up ZECT Voicebox on :17493 (native Mentrix Chatterbox engine).
# Requires Rancher Desktop (dockerd/moby) or Docker Desktop.
param()

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

Meanwhile you can run ZECT Voicebox without Docker:

  cd services\zect-voicebox
  pip install -r requirements.txt
  # Optional real clone ML: pip install -r requirements-ml.txt
  `$env:ZECT_VOICEBOX_ALLOW_STUB='1'
  python -m uvicorn app.main:app --host 127.0.0.1 --port 17493
"@
  exit 1
}

$compose = Join-Path $root "docker-compose.zect-voicebox.yml"
if (-not (Test-Path $compose)) {
  throw "Missing $compose"
}

Write-Host "Building and starting zect-voicebox on 127.0.0.1:17493..."
$env:ZECT_VOICEBOX_SYNTH = if ($env:ZECT_VOICEBOX_SYNTH) { $env:ZECT_VOICEBOX_SYNTH } else { "auto" }
$env:ZECT_VOICEBOX_ALLOW_STUB = if ($env:ZECT_VOICEBOX_ALLOW_STUB) { $env:ZECT_VOICEBOX_ALLOW_STUB } else { "1" }
docker compose -f $compose up -d --build
if ($LASTEXITCODE -ne 0) {
  Write-Host "Compose failed."
  exit $LASTEXITCODE
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
        # ignore
      }
      break
    }
  } catch {
    Start-Sleep -Seconds 2
  }
  Start-Sleep -Seconds 2
}

if (-not $ok) {
  Write-Host "ZECT Voicebox did not answer /profiles in time. Check: docker compose -f docker-compose.zect-voicebox.yml logs"
  exit 2
}

Write-Host @"

ZECT Voicebox is up: http://127.0.0.1:17493/profiles
Root:                http://127.0.0.1:17493/
Health:              http://127.0.0.1:17493/health
$healthJson

Set in backend/.env (do not commit):
  CHATTERBOX_BASE_URL=http://127.0.0.1:17493
  CHATTERBOX_SPEAK_TIMEOUT=120

Restart the ZECT API, then Companion -> Voice -> Test speak.
Stub synth works without ML; for real clone quality install requirements-ml.txt / set ZECT_VOICEBOX_SYNTH=chatterbox.
"@
