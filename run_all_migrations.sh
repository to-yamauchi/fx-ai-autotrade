#!/bin/bash

# ========================================
# 全マイグレーション実行スクリプト
# ========================================
# 作成日: 2025-10-23
# 目的: すべてのマイグレーションを順次実行
#

echo "========================================"
echo "All Migrations Execution"
echo "========================================"
echo ""

# .envファイルから環境変数を読み込む
if [ -f .env ]; then
    echo "Loading database credentials from .env..."
    export $(grep -v '^#' .env | xargs)
else
    echo "ERROR: .env file not found!"
    echo "Please create .env file from .env.template"
    exit 1
fi

echo "Database: ${DB_NAME}@${DB_HOST}:${DB_PORT}"
echo "User: ${DB_USER}"
echo ""

# マイグレーションファイルのリスト
migrations=(
    "config/migrations/003_create_daily_reviews_tables.sql"
    "config/migrations/004_create_daily_strategies_tables.sql"
    "config/migrations/005_create_periodic_updates_tables.sql"
    "config/migrations/006_create_layer3_monitoring_tables.sql"
)

# 各マイグレーションを実行
for migration in "${migrations[@]}"; do
    if [ ! -f "$migration" ]; then
        echo "ERROR: Migration file not found: $migration"
        exit 1
    fi

    echo "----------------------------------------"
    echo "Executing: $migration"
    echo "----------------------------------------"

    # パスワードを環境変数で設定してpsql実行
    PGPASSWORD=${DB_PASSWORD} psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} -f "$migration"

    if [ $? -eq 0 ]; then
        echo "✓ Migration completed successfully"
        echo ""
    else
        echo "✗ Migration failed!"
        exit 1
    fi
done

echo "========================================"
echo "All Migrations Completed Successfully!"
echo "========================================"
echo ""
echo "Created tables:"
echo "  - backtest_daily_reviews, demo_daily_reviews, daily_reviews"
echo "  - backtest_daily_strategies, demo_daily_strategies, daily_strategies"
echo "  - backtest_periodic_updates, demo_periodic_updates, periodic_updates"
echo "  - backtest_layer3a_monitoring, demo_layer3a_monitoring, layer3a_monitoring"
echo "  - backtest_layer3b_emergency, demo_layer3b_emergency, layer3b_emergency"
echo ""
echo "Verify with:"
echo "  psql -U ${DB_USER} -d ${DB_NAME} -c \"\\dt *daily* *periodic* *layer*\""
echo ""
