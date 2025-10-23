# ================================
# Backtest Table Migration Fix Script (PowerShell)
# ================================
#
# File: run_backtest_migration_fix.ps1
# Path: scripts/run_backtest_migration_fix.ps1
#
# Description:
# Drops existing incomplete backtest_results table and recreates it with correct schema.
#
# Usage:
# powershell scripts/run_backtest_migration_fix.ps1
#
# Created: 2025-10-23

Write-Host "================================" -ForegroundColor Cyan
Write-Host "Backtest Table Migration Fix" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[WARNING] This will DROP and RECREATE backtest_results table" -ForegroundColor Yellow
Write-Host ""

# Load configuration from .env file
if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -match '^([^#].+?)=(.+)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            Set-Item -Path "env:$name" -Value $value
        }
    }
}

# Default values
$DB_HOST = if ($env:DB_HOST) { $env:DB_HOST } else { "localhost" }
$DB_PORT = if ($env:DB_PORT) { $env:DB_PORT } else { "5432" }
$DB_NAME = if ($env:DB_NAME) { $env:DB_NAME } else { "fx_autotrade" }
$DB_USER = if ($env:DB_USER) { $env:DB_USER } else { "postgres" }
$DB_PASSWORD = $env:DB_PASSWORD

Write-Host "Connection Info:"
Write-Host "  Host: $DB_HOST"
Write-Host "  Port: $DB_PORT"
Write-Host "  Database: $DB_NAME"
Write-Host "  User: $DB_USER"
Write-Host ""

# Find psql executable
$psqlPaths = @(
    "psql",
    "C:\Program Files\PostgreSQL\18\bin\psql.exe",
    "C:\Program Files\PostgreSQL\17\bin\psql.exe",
    "C:\Program Files\PostgreSQL\16\bin\psql.exe",
    "C:\Program Files\PostgreSQL\15\bin\psql.exe"
)

$psql = $null
foreach ($path in $psqlPaths) {
    if (Get-Command $path -ErrorAction SilentlyContinue) {
        $psql = $path
        break
    }
}

if (-not $psql) {
    Write-Host "ERROR: psql not found" -ForegroundColor Red
    Write-Host "Please install PostgreSQL or add it to PATH" -ForegroundColor Red
    exit 1
}

Write-Host "psql found: $psql" -ForegroundColor Green
Write-Host ""

# Execute migration
Write-Host "Executing migration..." -ForegroundColor Yellow

$env:PGPASSWORD = $DB_PASSWORD
& $psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f config/migrations/002_recreate_backtest_results.sql

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "================================" -ForegroundColor Green
    Write-Host "Migration Successful!" -ForegroundColor Green
    Write-Host "================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "backtest_results table has been recreated." -ForegroundColor Green
    Write-Host ""
    Write-Host "Next step:" -ForegroundColor Cyan
    Write-Host "  python test_backtest.py" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "================================" -ForegroundColor Red
    Write-Host "Migration Failed" -ForegroundColor Red
    Write-Host "================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please check the error messages above." -ForegroundColor Red
    exit 1
}
