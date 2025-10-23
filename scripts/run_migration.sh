#!/bin/bash
# ========================================
# データベースマイグレーション実行スクリプト
# ========================================
#
# 使用方法:
#   bash scripts/run_migration.sh [migration_file]
#
# 例:
#   bash scripts/run_migration.sh config/migrations/001_add_timeframe_to_ai_judgments.sql
#

set -e  # エラーで停止

# 色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 環境変数読み込み
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo -e "${RED}Error: .env file not found${NC}"
    exit 1
fi

# マイグレーションファイルの確認
MIGRATION_FILE=${1:-"config/migrations/001_add_timeframe_to_ai_judgments.sql"}

if [ ! -f "$MIGRATION_FILE" ]; then
    echo -e "${RED}Error: Migration file not found: $MIGRATION_FILE${NC}"
    exit 1
fi

# データベース接続情報
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}
DB_NAME=${DB_NAME:-fx_autotrade}
DB_USER=${DB_USER:-postgres}

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Running Database Migration${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Migration file: $MIGRATION_FILE"
echo "Database: $DB_NAME@$DB_HOST:$DB_PORT"
echo "User: $DB_USER"
echo ""

# 確認
read -p "Do you want to proceed? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Migration cancelled${NC}"
    exit 0
fi

# マイグレーション実行
echo -e "${YELLOW}Executing migration...${NC}"
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f $MIGRATION_FILE

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Migration completed successfully!${NC}"
else
    echo ""
    echo -e "${RED}✗ Migration failed${NC}"
    exit 1
fi
