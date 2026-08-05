# Stop ZECT local stack (backend :8020, Vite :5173, Electron)
$ErrorActionPreference = "SilentlyContinue"

Write-Host "Stopping Electron..."
Get-Process -Name electron -ErrorAction SilentlyContinue | Stop-Process -Force

foreach ($port in 8020, 5173, 8000) {
  $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
  foreach ($c in $conns) {
    Write-Host "Killing PID $($c.OwningProcess) on :$port"
    cmd /c "taskkill /F /PID $($c.OwningProcess) /T" | Out-Null
  }
}

Get-CimInstance Win32_Process | Where-Object {
  $_.CommandLine -and (
    $_.CommandLine -match 'uvicorn app\.main:app' -or
    $_.CommandLine -match 'vite.*--port 5173'
  )
} | ForEach-Object {
  Write-Host "Killing $($_.Name) PID $($_.ProcessId)"
  cmd /c "taskkill /F /PID $($_.ProcessId) /T" | Out-Null
}

Start-Sleep 1
Write-Host "Stopped. Listeners left:"
netstat -ano | findstr "LISTENING" | findstr ":8020 :5173 :8000"
Write-Host "electron=$((Get-Process -Name electron -ErrorAction SilentlyContinue | Measure-Object).Count)"
