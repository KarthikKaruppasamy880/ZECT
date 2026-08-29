# Bring up Mentrix Local LLM on 127.0.0.1:11434 (OpenAI-compatible /v1).
# Requires Rancher Desktop (dockerd/moby) or Docker Desktop.
param(
  [string]$SeedModel = "qwen2.5:7b"
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

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
  2. Preferences -> Container Engine -> use dockerd (moby)
  3. Re-run this script

See docs/guides/MENTRIX_LLM_GATEWAY.md
"@
  exit 1
}

Write-Host "Starting Mentrix Local LLM (compose)…"
docker compose -f docker-compose.yml up -d

Write-Host "Waiting for Mentrix Local LLM…"
$ready = $false
for ($i = 0; $i -lt 40; $i++) {
  try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -UseBasicParsing -TimeoutSec 2
    if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 300) {
      $ready = $true
      break
    }
  } catch {
    Start-Sleep -Seconds 2
  }
}

if (-not $ready) {
  Write-Host "Mentrix Local LLM did not become ready in time. Check: docker logs mentrix-llm"
  exit 1
}

Write-Host "Seeding Mentrix Local model: $SeedModel"
docker exec mentrix-llm ollama pull $SeedModel

Write-Host @"

Mentrix Local LLM is up.

Point ZECT backend/.env at the gateway:

  ZECT_LLM_BASE_URL=http://127.0.0.1:11434/v1
  ZECT_LLM_API_KEY=local
  ZECT_LLM_CHAT_MODEL=$SeedModel
  MENTRIX_COMPANION_MODEL=$SeedModel

OpenAI-compatible probe: GET http://127.0.0.1:11434/v1/models
ZECT status: GET /api/models/gateway
"@
