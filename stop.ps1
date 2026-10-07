# ============================================
# Riskora — Stop All Services
# ============================================

Write-Host "Stopping Riskora..." -ForegroundColor Yellow

@(8000, 5173) | ForEach-Object {
    $port = $_
    $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($connections) {
        $procIds = $connections.OwningProcess | Sort-Object -Unique
        foreach ($procId in $procIds) {
            if ($procId -gt 0) {
                Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
                Write-Host "  Killed PID $procId (port $port)" -ForegroundColor Gray
            }
        }
    }
}

Write-Host "All services stopped." -ForegroundColor Green
