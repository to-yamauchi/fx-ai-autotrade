# ========================================
# 全マイグレーション一括実行スクリプト (PowerShell)
# ========================================
# 作成日: 2025-10-23
# 目的: AI分析機能の全マイグレーションを順番に実行
#

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "FX AI Auto-Trade - All Migrations" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This script will execute all database migrations in order:" -ForegroundColor Yellow
Write-Host "  1. Daily Reviews Tables (003)" -ForegroundColor White
Write-Host "  2. Daily Strategies Tables (004)" -ForegroundColor White
Write-Host "  3. Periodic Updates Tables (005)" -ForegroundColor White
Write-Host "  4. Layer 3 Monitoring Tables (006)" -ForegroundColor White
Write-Host ""

# 確認を求める
$confirmation = Read-Host "Do you want to continue? (yes/no)"
if ($confirmation -ne "yes") {
    Write-Host "Migration cancelled." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting migrations..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# マイグレーションスクリプトのリスト
$migrations = @(
    "run_daily_reviews_migration.ps1",
    "run_daily_strategies_migration.ps1",
    "run_periodic_updates_migration.ps1",
    "run_layer3_monitoring_migration.ps1"
)

$successCount = 0
$failCount = 0

# 各マイグレーションを実行
foreach ($migration in $migrations) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Magenta
    Write-Host "Executing: $migration" -ForegroundColor Magenta
    Write-Host "========================================" -ForegroundColor Magenta
    Write-Host ""

    if (-not (Test-Path $migration)) {
        Write-Host "ERROR: Migration script not found: $migration" -ForegroundColor Red
        $failCount++
        continue
    }

    try {
        # スクリプトを実行
        & ".\$migration"

        if ($LASTEXITCODE -eq 0 -or $null -eq $LASTEXITCODE) {
            Write-Host "✓ $migration completed successfully" -ForegroundColor Green
            $successCount++
        } else {
            Write-Host "✗ $migration failed with exit code: $LASTEXITCODE" -ForegroundColor Red
            $failCount++

            # 失敗時に続行するか確認
            $continueOnError = Read-Host "Do you want to continue with remaining migrations? (yes/no)"
            if ($continueOnError -ne "yes") {
                Write-Host "Migration process stopped." -ForegroundColor Yellow
                break
            }
        }
    } catch {
        Write-Host "✗ Error executing $migration" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        $failCount++

        # 失敗時に続行するか確認
        $continueOnError = Read-Host "Do you want to continue with remaining migrations? (yes/no)"
        if ($continueOnError -ne "yes") {
            Write-Host "Migration process stopped." -ForegroundColor Yellow
            break
        }
    }

    Write-Host ""
}

# 最終結果
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Migration Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Successful: $successCount" -ForegroundColor Green
Write-Host "Failed: $failCount" -ForegroundColor $(if ($failCount -gt 0) { "Red" } else { "White" })
Write-Host ""

if ($failCount -eq 0) {
    Write-Host "All migrations completed successfully! 🎉" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Run integration test: python test_full_integration.py" -ForegroundColor White
    Write-Host "  2. Check database tables with:" -ForegroundColor White
    Write-Host "     psql -U postgres -d fx_autotrade -c '\dt backtest_*'" -ForegroundColor Gray
    Write-Host ""
    Write-Host "You're ready to test the AI analysis features!" -ForegroundColor Green
} else {
    Write-Host "Some migrations failed. Please review the errors above." -ForegroundColor Yellow
    Write-Host "You can re-run individual migration scripts to fix issues." -ForegroundColor Yellow
    exit 1
}
