# ============================================
# Riskora  Clean Startup Script
# Run from project root:  .\start.ps1
# ============================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Riskora  Starting...          " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# --- Step 1: Kill anything on ports 8000 and 5173 ---
Write-Host "[1/4] Clearing ports 8000 and 5173..." -ForegroundColor Yellow

$ports = @(8000, 5173)
foreach ($port in $ports) {
    $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($connections) {
        $procIds = $connections.OwningProcess | Sort-Object -Unique
        foreach ($procId in $procIds) {
            if ($procId -gt 0) {
                Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
                Write-Host "  Killed PID $procId on port $port" -ForegroundColor Gray
            }
        }
    }
}
Start-Sleep -Seconds 2
Write-Host "  Ports cleared." -ForegroundColor Green

# --- Step 2: Start Backend ---
Write-Host ""
Write-Host "[2/4] Starting Backend (port 8000)..." -ForegroundColor Yellow

$backendPath = Join-Path $PSScriptRoot "backend"
$venvPython = Join-Path $backendPath "venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "  ERROR: Virtual environment not found!" -ForegroundColor Red
    Write-Host "  Run: cd backend; python -m venv venv; .\venv\Scripts\activate; pip install -r requirements.txt" -ForegroundColor Red
    exit 1
}

$backendJob = Start-Process -FilePath $venvPython `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000" `
    -WorkingDirectory $backendPath `
    -PassThru -NoNewWindow

Write-Host "  Backend PID: $($backendJob.Id)" -ForegroundColor Green

# --- Step 3: Start Frontend ---
Write-Host ""
Write-Host "[3/4] Starting Frontend (port 5173)..." -ForegroundColor Yellow

$frontendPath = Join-Path $PSScriptRoot "frontend"
$frontendJob = Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/c", "npm run dev" `
    -WorkingDirectory $frontendPath `
    -PassThru -NoNewWindow

Write-Host "  Frontend PID: $($frontendJob.Id)" -ForegroundColor Green

# --- Step 4: Wait for backend to be ready ---
Write-Host ""
Write-Host "[4/4] Waiting for backend to load models..." -ForegroundColor Yellow

$ready = $false
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 3
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            $ready = $true
            break
        }
    }
    catch {
        $elapsed = ($i + 1) * 3
        Write-Host "  Still loading... ($elapsed seconds)" -ForegroundColor Gray
    }
}

Write-Host ""
if ($ready) {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  Riskora is READY!             " -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Backend:  http://localhost:8000" -ForegroundColor White
    Write-Host "  Frontend: http://localhost:5173" -ForegroundColor White
    Write-Host "  API Docs: http://localhost:8000/docs" -ForegroundColor White
    Write-Host ""
    Write-Host "  Press Ctrl+C to stop all services." -ForegroundColor Gray
}
else {
    Write-Host "  WARNING: Backend may still be loading." -ForegroundColor Yellow
    Write-Host "  Check: http://localhost:8000/api/health" -ForegroundColor Yellow
}

# Keep script alive so both processes run
Write-Host ""
Write-Host "Servers running. Press Ctrl+C to stop." -ForegroundColor Gray
try {
    Wait-Process -Id $backendJob.Id
}
catch {
    Write-Host ""
    Write-Host "Shutting down..." -ForegroundColor Yellow
    Stop-Process -Id $backendJob.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $frontendJob.Id -Force -ErrorAction SilentlyContinue
    Write-Host "Done." -ForegroundColor Green
}
