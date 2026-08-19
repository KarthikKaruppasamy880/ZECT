#requires -Version 5.1
# ZECT local stack front door. Do not declare param() — --profile must reach Python.
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Script = Join-Path $Root "scripts\zect_stack.py"

if (-not $args -or -not $args[0]) {
  Write-Host "Usage: ./zect.ps1 up|down|restart|status|health|logs|doctor [--profile core|desktop|full] [service]"
  exit 2
}

$pyExe = $null
$pyArgs = @()
foreach ($pair in @(
    @{ Exe = "py"; Args = @("-3.12") },
    @{ Exe = "py"; Args = @("-3") },
    @{ Exe = "python"; Args = @() }
  )) {
  try {
    & $pair.Exe @($pair.Args) -c "import sys" 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
      $pyExe = $pair.Exe
      $pyArgs = @($pair.Args)
      break
    }
  } catch {
    continue
  }
}

if (-not $pyExe) {
  Write-Error "Python 3.12+ is required for zect.ps1"
  exit 2
}

& $pyExe @pyArgs $Script @args
exit $LASTEXITCODE
