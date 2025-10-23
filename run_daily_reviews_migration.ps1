# Daily Reviews Tables Migration Script
# Purpose: Create daily_reviews tables for backtest, demo, and live modes

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Daily Reviews Tables Migration" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Load environment variables from .env file
if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]*)\s*=\s*(.*)\s*$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
    Write-Host "Environment variables loaded from .env" -ForegroundColor Green
} else {
    Write-Host "Warning: .env file not found" -ForegroundColor Yellow
}

# Database connection parameters
$DB_HOST = if ($env:DB_HOST) { $env:DB_HOST } else { "localhost" }
$DB_PORT = if ($env:DB_PORT) { $env:DB_PORT } else { "5432" }
$DB_NAME = if ($env:DB_NAME) { $env:DB_NAME } else { "fx_autotrade" }
$DB_USER = if ($env:DB_USER) { $env:DB_USER } else { "postgres" }
$DB_PASSWORD = $env:DB_PASSWORD

Write-Host "Database: $DB_HOST:$DB_PORT/$DB_NAME" -ForegroundColor Cyan
Write-Host ""

# Check if psql is available
if (-not (Get-Command psql -ErrorAction SilentlyContinue)) {
    Write-Host "Error: psql command not found" -ForegroundColor Red
    Write-Host "Please install PostgreSQL client tools" -ForegroundColor Red
    exit 1
}

# Set PGPASSWORD environment variable
$env:PGPASSWORD = $DB_PASSWORD

# Run migration
Write-Host "Running migration: 003_create_daily_reviews_tables.sql" -ForegroundColor Yellow
Write-Host ""

$migrationFile = "config\migrations\003_create_daily_reviews_tables.sql"

if (-not (Test-Path $migrationFile)) {
    Write-Host "Error: Migration file not found: $migrationFile" -ForegroundColor Red
    exit 1
}

try {
    psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f $migrationFile

    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "Migration completed successfully!" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "Created tables:" -ForegroundColor Cyan
        Write-Host "  - backtest_daily_reviews" -ForegroundColor White
        Write-Host "  - demo_daily_reviews" -ForegroundColor White
        Write-Host "  - daily_reviews" -ForegroundColor White
        Write-Host ""
    } else {
        Write-Host ""
        Write-Host "Migration failed with exit code: $LASTEXITCODE" -ForegroundColor Red
        exit $LASTEXITCODE
    }
} catch {
    Write-Host ""
    Write-Host "Error running migration: $_" -ForegroundColor Red
    exit 1
} finally {
    # Clear password from environment
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
}

Write-Host "You can now run: python test_daily_review.py" -ForegroundColor Cyan
Write-Host ""
