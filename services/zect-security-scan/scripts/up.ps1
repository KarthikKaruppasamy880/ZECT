# Bring up ZECT Security Scan daemon on :3310 for ZECT Security Agent.
param()

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
Docker daemon is not reachable.

Start Rancher Desktop / Docker Desktop, then re-run:
  services\zect-security-scan\scripts\up.ps1

Backend will report ZECT Security Agent status as degraded until the daemon is up.
Set ZECT_MALWARE_SCAN_HOST=127.0.0.1 and ZECT_MALWARE_SCAN_PORT=3310 in backend/.env
"@
  exit 1
}

docker compose -f docker-compose.yml up -d
Write-Host "ZECT Security Scan starting on 127.0.0.1:3310 (first boot may take several minutes for signatures)."
Write-Host "Check: GET /api/security/malware/status"
