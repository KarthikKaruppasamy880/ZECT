# Clone jamiepine/voicebox into third_party/voicebox (gitignored).
param(
  [string]$RepoUrl = "https://github.com/jamiepine/voicebox.git",
  [string]$Dest = ""
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
if (-not $Dest) {
  $Dest = Join-Path $root "third_party\voicebox"
}

if (Test-Path (Join-Path $Dest ".git")) {
  Write-Host "Upstream already present: $Dest"
  exit 0
}

New-Item -ItemType Directory -Force -Path (Split-Path $Dest) | Out-Null
Write-Host "Cloning $RepoUrl -> $Dest (shallow)…"
git clone --depth 1 $RepoUrl $Dest
if ($LASTEXITCODE -ne 0) {
  throw "git clone failed — check network / git install"
}
Write-Host "Done. Next: docker compose -f docker-compose.zect-voicebox.yml up -d --build"
