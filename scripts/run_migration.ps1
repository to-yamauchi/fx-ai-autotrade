# ========================================
# データベースマイグレーション実行スクリプト (PowerShell)
# ========================================
#
# 使用方法:
#   .\scripts\run_migration.ps1 [migration_file]
#
# 例:
#   .\scripts\run_migration.ps1 config\migrations\001_add_timeframe_to_ai_judgments.sql
#

param(
    [string]$MigrationFile = "config\migrations\001_add_timeframe_to_ai_judgments.sql"
)

# エラーで停止
$ErrorActionPreference = "Stop"

# .envファイルから環境変数を読み込み
if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -match '^([^#][^=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [System.Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
} else {
    Write-Host "Error: .env file not found" -ForegroundColor Red
    exit 1
}

# マイグレーションファイルの確認
if (-not (Test-Path $MigrationFile)) {
    Write-Host "Error: Migration file not found: $MigrationFile" -ForegroundColor Red
    exit 1
}

# データベース接続情報
$DB_HOST = if ($env:DB_HOST) { $env:DB_HOST } else { "localhost" }
$DB_PORT = if ($env:DB_PORT) { $env:DB_PORT } else { "5432" }
$DB_NAME = if ($env:DB_NAME) { $env:DB_NAME } else { "fx_autotrade" }
$DB_USER = if ($env:DB_USER) { $env:DB_USER } else { "postgres" }
$DB_PASSWORD = $env:DB_PASSWORD

Write-Host "========================================" -ForegroundColor Green
Write-Host "Running Database Migration" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Migration file: $MigrationFile"
Write-Host "Database: $DB_NAME@${DB_HOST}:${DB_PORT}"
Write-Host "User: $DB_USER"
Write-Host ""

# 確認
$response = Read-Host "Do you want to proceed? (y/n)"
if ($response -ne 'y' -and $response -ne 'Y') {
    Write-Host "Migration cancelled" -ForegroundColor Yellow
    exit 0
}

# マイグレーション実行
Write-Host "Executing migration..." -ForegroundColor Yellow

# PostgreSQLのパスを確認
$psqlPath = Get-Command psql -ErrorAction SilentlyContinue
if (-not $psqlPath) {
    Write-Host "Error: psql command not found. Please install PostgreSQL client tools." -ForegroundColor Red
    exit 1
}

# PGPASSWORD環境変数を設定してpsqlを実行
$env:PGPASSWORD = $DB_PASSWORD
& psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f $MigrationFile

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "[成功] Migration completed successfully!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "[失敗] Migration failed" -ForegroundColor Red
    exit 1
}
