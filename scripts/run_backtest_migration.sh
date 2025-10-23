#!/bin/bash
# ================================
# バックテストテーブルマイグレーション実行スクリプト
# ================================
#
# ファイル名: run_backtest_migration.sh
# パス: scripts/run_backtest_migration.sh
#
# 【概要】
# backtest_resultsテーブルを作成するマイグレーションを実行します。
#
# 【使用方法】
# bash scripts/run_backtest_migration.sh
#
# 【作成日】2025-10-23

echo "================================"
echo "バックテストテーブルマイグレーション"
echo "================================"
echo ""

# .envファイルから設定を読み込み
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# デフォルト値
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}
DB_NAME=${DB_NAME:-fx_autotrade}
DB_USER=${DB_USER:-postgres}

echo "接続情報:"
echo "  Host: $DB_HOST"
echo "  Port: $DB_PORT"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo ""

# マイグレーション実行
echo "マイグレーションを実行中..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f config/migrations/002_create_backtest_results.sql

if [ $? -eq 0 ]; then
    echo ""
    echo "================================"
    echo "マイグレーション成功！"
    echo "================================"
    echo ""
    echo "backtest_resultsテーブルが作成されました。"
else
    echo ""
    echo "================================"
    echo "マイグレーション失敗"
    echo "================================"
    echo ""
    echo "エラーを確認してください。"
    exit 1
fi
