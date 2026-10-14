# start_backend.ps1 - Start the DeepGuard FastAPI backend
#
# Usage: .\start_backend.ps1

$ErrorActionPreference = "Stop"
$BackendDir = Join-Path $PSScriptRoot "backend"

Write-Host ""
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "  DeepGuard Backend Startup" -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host ""

# Check MySQL
Write-Host "Checking MySQL..." -ForegroundColor Yellow
try {
    $mysqlRunning = $false
    $tcpClient = New-Object System.Net.Sockets.TcpClient
    try {
        $tcpClient.Connect("localhost", 3306)
        $mysqlRunning = $true
    } catch { }
    finally {
        $tcpClient.Close()
    }

    if (-not $mysqlRunning) {
        Write-Host "  [!] MySQL does not appear to be running on port 3306." -ForegroundColor Yellow
        Write-Host "      Start it from MySQL Workbench or run: net start MySQL80" -ForegroundColor Yellow
    } else {
        Write-Host "  [OK] MySQL is reachable on port 3306." -ForegroundColor Green
    }
} catch { }

# Virtual environment
$VenvPath = Join-Path $BackendDir ".venv"
$PythonPath = Join-Path $VenvPath "Scripts\python.exe"

if (-not (Test-Path $PythonPath)) {
    Write-Host ""
    Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv "$VenvPath"
    Write-Host "  [OK] Virtual environment created." -ForegroundColor Green
}

Write-Host ""
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& "$VenvPath\Scripts\Activate.ps1"

# Install dependencies
Write-Host ""
Write-Host "Installing/verifying Python dependencies..." -ForegroundColor Yellow
pip install -r "$BackendDir\requirements.txt" -q
Write-Host "  [OK] Dependencies ready." -ForegroundColor Green

# Start Uvicorn
Write-Host ""
Write-Host "Starting FastAPI server on http://localhost:8000" -ForegroundColor Cyan
Write-Host "Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""

Set-Location $BackendDir
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
