# EduMate One-Click PowerShell Launcher
Set-Location $PSScriptRoot

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "     Starting EduMate AI Study Tutor (React UI)" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""

# Automatically free ports 8000, 3000, 8501 if older processes are still holding them
$oldConnections = Get-NetTCPConnection -LocalPort 8000, 3000, 8501, 8502 -ErrorAction SilentlyContinue
if ($oldConnections) {
    Write-Host "Freeing occupied ports..." -ForegroundColor Yellow
    foreach ($conn in $oldConnections) {
        Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 1
}

Write-Host "1. Starting Backend Server on http://127.0.0.1:8000 ..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$PSScriptRoot'; .\venv\Scripts\python.exe run_server.py"

Write-Host "2. Waiting 5 seconds for backend to initialize..." -ForegroundColor Gray
Start-Sleep -Seconds 5

Write-Host "3. Starting React Frontend UI on http://localhost:3000 ..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$PSScriptRoot\frontend'; npm run dev"

Write-Host ""
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "EduMate services started in separate windows!" -ForegroundColor Cyan
Write-Host "- React UI: http://localhost:3000" -ForegroundColor Green
Write-Host "- Backend API: http://127.0.0.1:8000" -ForegroundColor Yellow
Write-Host "- API Docs: http://127.0.0.1:8000/docs" -ForegroundColor Gray
Write-Host "=======================================================" -ForegroundColor Cyan

Start-Sleep -Seconds 3
Start-Process "http://localhost:3000"
