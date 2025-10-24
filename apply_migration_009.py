#!/usr/bin/env python
"""
マイグレーション009を適用
"""
import sys
import os

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 既存のコードからDB接続を利用
from src.data_processing.tick_loader import TickDataLoader

def apply_migration():
    """マイグレーション009を適用"""
    print("📝 マイグレーション009を実行中...")
    print("   backtest_trades.exit_reason を VARCHAR(100) → VARCHAR(500) に拡張")

    try:
        # TickDataLoaderを使用してDB接続を取得
        loader = TickDataLoader()
        conn = loader._get_db_connection()
        cursor = conn.cursor()

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
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = apply_migration()
    sys.exit(0 if success else 1)
