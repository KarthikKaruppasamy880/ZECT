# ZECT Mentrix — stop stale services, then start backend + frontend + Electron.
# Run from repo root:  .\RESTART_MENTRIX.ps1

param(
    [switch]$StopOnly,
    [switch]$NoElectron
)

$ErrorActionPreference = "SilentlyContinue"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

function Stop-PortListener {
    param([int]$Port)
    $conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    foreach ($c in $conns) {
        $pid = $c.OwningProcess
        if ($pid -and $pid -ne 0) {
            Write-Host "  Stopping PID $pid on port $Port" -ForegroundColor DarkYellow
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        }
    }
}

Write-Host ""
Write-Host "ZECT Mentrix — restart" -ForegroundColor Cyan
Write-Host "Repo: $root" -ForegroundColor Gray
Write-Host ""

Write-Host "[stop] Freeing ports 8000 (backend) and 5173 (frontend)..." -ForegroundColor Yellow
Stop-PortListener -Port 8000
Stop-PortListener -Port 5173
Start-Sleep -Seconds 1

# Close Electron windows titled like ZECT (optional — user may want to keep other Electron apps)
Get-Process electron -ErrorAction SilentlyContinue | Where-Object {
    $_.MainWindowTitle -match "ZECT|Mentrix"
} | ForEach-Object {
    Write-Host "  Closing Electron PID $($_.Id)" -ForegroundColor DarkYellow
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}

if ($StopOnly) {
    Write-Host "Stop-only complete." -ForegroundColor Green
    exit 0
}

Write-Host ""
Write-Host "[start] Launching services (3 separate windows)..." -ForegroundColor Green
& "$root\RUN_MENTRIX.ps1"
