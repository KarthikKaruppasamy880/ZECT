# Create or update the ZECT Mentrix desktop shortcut (Windows)
# Run from the ZECT repo root: .\CREATE_DESKTOP_SHORTCUT.ps1

$ErrorActionPreference = "Stop"

if (-not (Test-Path "backend")) {
    Write-Host "ERROR: Run this script from the ZECT root directory." -ForegroundColor Red
    exit 1
}

$repoRoot = (Get-Location).Path
$launcher = Join-Path $repoRoot "RUN_MENTRIX.ps1"
if (-not (Test-Path $launcher)) {
    Write-Host "ERROR: RUN_MENTRIX.ps1 not found at $launcher" -ForegroundColor Red
    exit 1
}

$icon = Join-Path $repoRoot "electron\icons\icon.ico"
if (-not (Test-Path $icon)) {
    $icon = Join-Path $repoRoot "electron\icons\icon.png"
}

$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "ZECT Mentrix.lnk"
$shell = New-Object -ComObject WScript.Shell
$link = $shell.CreateShortcut($shortcutPath)
$link.TargetPath = (Get-Command powershell.exe).Source
$link.Arguments = "-ExecutionPolicy Bypass -NoProfile -File `"$launcher`""
$link.WorkingDirectory = $repoRoot
$link.Description = "ZECT Mentrix Control Tower - launch backend, frontend, and desktop"
if (Test-Path $icon) {
    $link.IconLocation = "$icon,0"
}
$link.Save()

Write-Host ""
Write-Host "Desktop shortcut created:" -ForegroundColor Green
Write-Host "  $shortcutPath"
Write-Host ""
Write-Host "Double-click 'ZECT Mentrix' on your desktop to start ZECT after code updates." -ForegroundColor Cyan
