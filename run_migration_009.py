"""
マイグレーション009を実行するスクリプト
backtest_tradesテーブルのexit_reasonカラムを拡張
"""
import os
import psycopg2
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()

def run_migration():
    """マイグレーション009を実行"""
    try:
        # データベース接続
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 5432)),
            database=os.getenv('DB_NAME', 'fx_autotrade'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', ''),
        )
        cursor = conn.cursor()

        print("📝 マイグレーション009を実行中...")

        # exit_reasonカラムの型を変更
        cursor.execute("""
            ALTER TABLE backtest_trades
            ALTER COLUMN exit_reason TYPE VARCHAR(500)
        """)

        # コメントを更新
        cursor.execute("""
            COMMENT ON COLUMN backtest_trades.exit_reason IS '決済理由（最大500文字）'
        """)

        conn.commit()

        # 変更を確認
        cursor.execute("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'backtest_trades' AND column_name = 'exit_reason'
        """)
        result = cursor.fetchone()

        print("✓ マイグレーション009完了")
        print(f"  exit_reasonカラム: {result[1]}({result[2]})")

        cursor.close()
        conn.close()

        return True

    except Exception as e:
        print(f"❌ マイグレーション失敗: {e}")
        return False

if __name__ == '__main__':
    success = run_migration()
    exit(0 if success else 1)
