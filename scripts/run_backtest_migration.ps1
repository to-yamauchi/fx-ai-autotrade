# ================================
# バックテストテーブルマイグレーション実行スクリプト (PowerShell)
# ================================
#
# ファイル名: run_backtest_migration.ps1
# パス: scripts/run_backtest_migration.ps1
#
# 【概要】
# backtest_resultsテーブルを作成するマイグレーションを実行します。
#
# 【使用方法】
# powershell scripts/run_backtest_migration.ps1
#
# 【作成日】2025-10-23

Write-Host "================================" -ForegroundColor Cyan
Write-Host "バックテストテーブルマイグレーション" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# .envファイルから設定を読み込み
if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -match '^([^#].+?)=(.+)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            Set-Item -Path "env:$name" -Value $value
        }
    }
}

# デフォルト値
$DB_HOST = if ($env:DB_HOST) { $env:DB_HOST } else { "localhost" }
$DB_PORT = if ($env:DB_PORT) { $env:DB_PORT } else { "5432" }
$DB_NAME = if ($env:DB_NAME) { $env:DB_NAME } else { "fx_autotrade" }
$DB_USER = if ($env:DB_USER) { $env:DB_USER } else { "postgres" }
$DB_PASSWORD = $env:DB_PASSWORD

Write-Host "接続情報:"
Write-Host "  Host: $DB_HOST"
Write-Host "  Port: $DB_PORT"
Write-Host "  Database: $DB_NAME"
Write-Host "  User: $DB_USER"
Write-Host ""

# psqlのパスを探す
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
    Write-Host "エラー: psqlが見つかりません" -ForegroundColor Red
    Write-Host "PostgreSQLをインストールするか、PATHに追加してください" -ForegroundColor Red
    exit 1
}

Write-Host "psql found: $psql" -ForegroundColor Green
Write-Host ""

# マイグレーション実行
Write-Host "マイグレーションを実行中..." -ForegroundColor Yellow

$env:PGPASSWORD = $DB_PASSWORD
& $psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f config/migrations/002_create_backtest_results.sql

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "================================" -ForegroundColor Green
    Write-Host "マイグレーション成功！" -ForegroundColor Green
    Write-Host "================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "backtest_resultsテーブルが作成されました。" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "================================" -ForegroundColor Red
    Write-Host "マイグレーション失敗" -ForegroundColor Red
    Write-Host "================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "エラーを確認してください。" -ForegroundColor Red
    exit 1
}
