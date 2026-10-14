#!/usr/bin/env pwsh
# start_frontend.ps1 — Start the DeepGuard React frontend
#
# Usage: .\start_frontend.ps1

$ErrorActionPreference = "Stop"
$FrontendDir = Join-Path $PSScriptRoot "frontend"

Write-Host ""
Write-Host "======================================================" -ForegroundColor Magenta
Write-Host "  DeepGuard Frontend Startup" -ForegroundColor Magenta
Write-Host "======================================================" -ForegroundColor Magenta
Write-Host ""

Set-Location $FrontendDir

if (-not (Test-Path "node_modules")) {
    Write-Host "Installing npm packages…" -ForegroundColor Yellow
    npm install --legacy-peer-deps
}

Write-Host ""
Write-Host "Starting Vite dev server on http://localhost:5173" -ForegroundColor Magenta
Write-Host ""
npm run dev
