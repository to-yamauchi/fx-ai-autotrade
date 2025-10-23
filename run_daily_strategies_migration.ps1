# ========================================
# デイリー戦略テーブル作成マイグレーション実行スクリプト
# ========================================
# 作成日: 2025-10-23
# 目的: 004_create_daily_strategies_tables.sqlを実行してテーブルを作成
#

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Daily Strategies Tables Migration" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# .envファイルから設定を読み込む
$envFile = ".env"
if (Test-Path $envFile) {
    Write-Host "Loading database credentials from .env..." -ForegroundColor Yellow
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^([^#][^=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            Set-Item -Path "env:$name" -Value $value
        }
    }
} else {
    Write-Host "ERROR: .env file not found!" -ForegroundColor Red
    Write-Host "Please create .env file from .env.template" -ForegroundColor Red
    exit 1
}

# データベース接続情報
$DB_HOST = $env:DB_HOST
$DB_PORT = $env:DB_PORT
$DB_NAME = $env:DB_NAME
$DB_USER = $env:DB_USER
$DB_PASSWORD = $env:DB_PASSWORD

Write-Host "Database: ${DB_NAME}@${DB_HOST}:${DB_PORT}" -ForegroundColor Yellow
Write-Host "User: $DB_USER" -ForegroundColor Yellow
Write-Host ""

# Find psql executable
$psqlPath = $null

# Check if psql is in PATH
if (Get-Command psql -ErrorAction SilentlyContinue) {
    $psqlPath = "psql"
    Write-Host "Found psql in PATH" -ForegroundColor Green
} else {
    # Search common PostgreSQL installation directories
    $commonPaths = @(
        "C:\Program Files\PostgreSQL\*\bin\psql.exe",
        "C:\Program Files (x86)\PostgreSQL\*\bin\psql.exe",
        "C:\PostgreSQL\*\bin\psql.exe"
    )

    foreach ($pathPattern in $commonPaths) {
        $found = Get-ChildItem -Path $pathPattern -ErrorAction SilentlyContinue |
                 Sort-Object FullName -Descending |
                 Select-Object -First 1

        if ($found) {
            $psqlPath = $found.FullName
            Write-Host "Found psql at: $psqlPath" -ForegroundColor Green
            break
        }
    }
}

if (-not $psqlPath) {
    Write-Host "Error: psql command not found" -ForegroundColor Red
    Write-Host "Please ensure PostgreSQL is installed and try one of:" -ForegroundColor Yellow
    Write-Host "  1. Add PostgreSQL bin directory to your PATH" -ForegroundColor Yellow
    Write-Host "  2. Set `$env:PSQL_PATH to your psql.exe location" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Or run migration manually with:" -ForegroundColor Cyan
    Write-Host "  psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f config/migrations/004_create_daily_strategies_tables.sql" -ForegroundColor White
    exit 1
}

# マイグレーションファイルパス
$migrationFile = "config/migrations/004_create_daily_strategies_tables.sql"

if (-not (Test-Path $migrationFile)) {
    Write-Host "ERROR: Migration file not found: $migrationFile" -ForegroundColor Red
    exit 1
}

Write-Host "Executing migration: $migrationFile" -ForegroundColor Yellow
Write-Host ""

# 環境変数でパスワードを設定（psqlはPGPASSWORD環境変数を使用）
$env:PGPASSWORD = $DB_PASSWORD

# psqlコマンド実行
try {
    # psqlコマンドを実行
    $output = & $psqlPath -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f $migrationFile 2>&1

    if ($LASTEXITCODE -eq 0) {
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "Migration completed successfully!" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "Created tables:" -ForegroundColor Cyan
        Write-Host "  - backtest_daily_strategies" -ForegroundColor White
        Write-Host "  - demo_daily_strategies" -ForegroundColor White
        Write-Host "  - daily_strategies" -ForegroundColor White
        Write-Host ""
        Write-Host "Output:" -ForegroundColor Cyan
        Write-Host $output -ForegroundColor Gray
    } else {
        Write-Host "========================================" -ForegroundColor Red
        Write-Host "Migration failed!" -ForegroundColor Red
        Write-Host "========================================" -ForegroundColor Red
        Write-Host ""
        Write-Host "Error output:" -ForegroundColor Red
        Write-Host $output -ForegroundColor Gray
        exit 1
    }
} catch {
    Write-Host "ERROR: Failed to execute psql command" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "Make sure PostgreSQL client tools (psql) are installed and in PATH" -ForegroundColor Yellow
    exit 1
} finally {
    # パスワード環境変数をクリア
    Remove-Item env:PGPASSWORD -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Verify tables with: psql -U $DB_USER -d $DB_NAME -c '\dt *daily_strategies'" -ForegroundColor White
Write-Host "  2. Test morning_analysis() method" -ForegroundColor White
Write-Host "  3. Run backtest with Phase 2 integration" -ForegroundColor White
Write-Host ""
