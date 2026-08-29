# ZECT packaged API sidecar. No installer secrets. No credential printing.
# Prefer bundled python-runtime or zect-api.exe. System Python only if ZECT_ALLOW_SYSTEM_PYTHON=1 (dev).
param(
  [string]$UserData = $env:ZECT_USER_DATA,
  [string]$Port = $(if ($env:ZECT_API_PORT) { $env:ZECT_API_PORT } else { "8000" }),
  [string]$ResourcesDir = $PSScriptRoot
)

$ErrorActionPreference = "Stop"
$env:ZECT_PACKAGED = "1"
if (-not $UserData) {
  throw "ZECT_USER_DATA / -UserData is required (upgrade-safe per-user data dir)"
}

$dataDir = Join-Path $UserData "data"
$logDir = Join-Path $UserData "logs"
$configDir = Join-Path $UserData "config"
foreach ($d in @($dataDir, $logDir, $configDir)) {
  if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d | Out-Null }
}

$env:ZECT_USER_DATA = $UserData
$dbPath = (Join-Path $dataDir "zect.db") -replace "\\", "/"
if (-not $env:DATABASE_URL) {
  # Supported packaged mode is desktop_sqlite under userData. Not a Postgres defect.
  $env:DATABASE_URL = "sqlite:///$dbPath"
}

# Do not inherit installer/dev secrets. Per-user config may restore them.
foreach ($secret in @("ENCRYPTION_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GITHUB_TOKEN")) {
  Remove-Item "env:$secret" -ErrorAction SilentlyContinue
}

# Load per-user config only (never installer .env).
$userEnv = Join-Path $configDir ".env"
if (Test-Path $userEnv) {
  Get-Content $userEnv | ForEach-Object {
    if ($_ -match "^\s*#" -or $_ -notmatch "=") { return }
    $k, $v = $_.Split("=", 2)
    $name = $k.Trim()
    if (-not $name) { return }
    if ($name -in @("ZECT_PASSWORD", "ENCRYPTION_KEY", "OPENAI_API_KEY", "GITHUB_TOKEN")) {
      if (-not [string]::IsNullOrWhiteSpace($v)) {
        Set-Item -Path "env:$name" -Value $v.Trim().Trim('"').Trim("'")
      }
      return
    }
    if (-not (Get-Item -Path "env:$name" -ErrorAction SilentlyContinue)) {
      Set-Item -Path "env:$name" -Value $v.Trim().Trim('"').Trim("'")
    }
  }
}

$logFile = Join-Path $logDir "api.log"
function Write-ApiLog([string]$msg) {
  $line = "{0:o} {1}" -f (Get-Date).ToUniversalTime(), $msg
  Add-Content -Path $logFile -Value $line -Encoding utf8
}

$exe = Join-Path $ResourcesDir "zect-api.exe"
$py = Join-Path $ResourcesDir "python-runtime\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = Join-Path $ResourcesDir "python-runtime\python.exe" }
$src = Join-Path $ResourcesDir "src"
$entry = Join-Path $ResourcesDir "zect_api_entry.py"

Write-ApiLog "sidecar starting port=$Port"
try {
  if (Test-Path $exe) {
    Write-ApiLog "using zect-api.exe"
    & $exe --host 127.0.0.1 --port $Port
    exit $LASTEXITCODE
  }
  if (Test-Path $py) {
    if (Test-Path $src) { $env:PYTHONPATH = $src }
    Write-ApiLog "using bundled python-runtime"
    & $py $entry --host 127.0.0.1 --port $Port
    exit $LASTEXITCODE
  }
  if ($env:ZECT_ALLOW_SYSTEM_PYTHON -eq "1") {
    Write-ApiLog "WARNING using system Python (dev only)"
    if (Test-Path $src) { $env:PYTHONPATH = $src }
    py -3.12 $entry --host 127.0.0.1 --port $Port
    exit $LASTEXITCODE
  }
  Write-ApiLog "ERROR backend runtime missing (no zect-api.exe / python-runtime)"
  exit 2
} catch {
  Write-ApiLog ("ERROR " + $_.Exception.Message)
  exit 1
}
