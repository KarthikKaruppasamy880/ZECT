# ZECT Mentrix Desktop Launcher (PowerShell)
# Start all three services for Mentrix voice assistant

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   ZECT Mentrix Control Tower — Desktop Application         ║" -ForegroundColor Cyan
Write-Host "║   Status: Ready for Launch                                 ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Check if we're in the right directory
if (-not (Test-Path "backend")) {
    Write-Host "ERROR: Run this script from the ZECT root directory" -ForegroundColor Red
    Write-Host "Current directory: $(Get-Location)"
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[1/3] Starting Backend (Python FastAPI)..." -ForegroundColor Yellow
Write-Host "   Command: python -m uvicorn app.main:app --reload" -ForegroundColor Gray
Write-Host "   URL: http://localhost:8000" -ForegroundColor Gray
Write-Host ""

# Start backend in new window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$(Get-Location)\backend'; py -3.12 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000" -WindowStyle Normal
Start-Sleep -Seconds 3

Write-Host "[2/3] Starting Frontend (React Dev Server)..." -ForegroundColor Yellow
Write-Host "   Command: npm run dev" -ForegroundColor Gray
Write-Host "   URL: http://127.0.0.1:5173" -ForegroundColor Gray
Write-Host ""

# Start frontend in new window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$(Get-Location)\frontend'; npm run dev -- --host 127.0.0.1 --port 5173" -WindowStyle Normal
Start-Sleep -Seconds 3

Write-Host "[3/3] Starting Electron App..." -ForegroundColor Yellow
Write-Host "   Command: npm start" -ForegroundColor Gray
Write-Host ""

# Start electron in new window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$(Get-Location)\electron'; `$env:ZECT_DEV='true'; `$env:ZECT_DEV_URL='http://127.0.0.1:5173'; npm run start:dev" -WindowStyle Normal

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║   All services starting...                                  ║" -ForegroundColor Green
Write-Host "║   - Backend:  http://localhost:8000                         ║" -ForegroundColor Cyan
Write-Host "║   - Frontend: http://127.0.0.1:5173                         ║" -ForegroundColor Cyan
Write-Host "║   - Desktop:  Opening in new window                         ║" -ForegroundColor Cyan
Write-Host "║                                                             ║" -ForegroundColor Gray
Write-Host "║   Test voice: Say 'Hey Mentrix, what's in this repo?'      ║" -ForegroundColor White
Write-Host "║   Hotkey: Ctrl+Shift+Space to wake Mentrix                 ║" -ForegroundColor White
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "Services are running in separate windows. Close windows to stop services." -ForegroundColor Yellow
Read-Host "Press Enter to close this launcher"
