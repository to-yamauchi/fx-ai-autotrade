#!/usr/bin/env python3
"""
========================================
バックテストデータリセットツール
========================================

バックテスト用テーブルのデータを削除するユーティリティスクリプト

使用方法:
  python reset_backtest_data.py                    # .envの設定を使用
  python reset_backtest_data.py --yes              # 確認なしで削除
  python reset_backtest_data.py --symbol USDJPY --start 2024-01-01 --end 2024-12-31

オプション:
  --symbol SYMBOL    通貨ペア（デフォルト: .envのBACKTEST_SYMBOL）
  --start YYYY-MM-DD 開始日（デフォルト: .envのBACKTEST_START_DATE）
  --end YYYY-MM-DD   終了日（デフォルト: .envのBACKTEST_END_DATE）
  --yes              確認プロンプトをスキップ

作成日: 2025-10-23
"""

import sys
import argparse
import logging
from datetime import datetime

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(
        description='バックテストデータをリセット（削除）します',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # .envの設定でリセット（確認あり）
  python reset_backtest_data.py

  # 確認なしで削除
  python reset_backtest_data.py --yes

  # 特定の期間を指定
  python reset_backtest_data.py --symbol USDJPY --start 2024-01-01 --end 2024-12-31
        """
    )

    parser.add_argument(
        '--symbol',
        type=str,
        help='通貨ペア（デフォルト: .envのBACKTEST_SYMBOL）'
    )
    parser.add_argument(
        '--start',
        type=str,
        help='開始日（YYYY-MM-DD形式、デフォルト: .envのBACKTEST_START_DATE）'
    )
    parser.add_argument(
        '--end',
        type=str,
        help='終了日（YYYY-MM-DD形式、デフォルト: .envのBACKTEST_END_DATE）'
    )
    parser.add_argument(
        '--yes', '-y',
        action='store_true',
        help='確認プロンプトをスキップして削除を実行'
    )

    args = parser.parse_args()

    try:
        # BacktestEngineをインポート（環境変数の読み込みも実行される）
        from src.backtest.backtest_engine import BacktestEngine

        # BacktestEngineを初期化（引数があれば使用、なければ.envのデフォルト）
        print("")
        print("=" * 80)
        print("バックテストデータリセットツール")
        print("=" * 80)

        # 引数の日付形式をチェック
        if args.start:
            try:
                datetime.strptime(args.start, '%Y-%m-%d')
            except ValueError:
                print(f"❌ エラー: 開始日の形式が不正です: {args.start}")
                print("正しい形式: YYYY-MM-DD (例: 2024-01-01)")
                sys.exit(1)

        if args.end:
            try:
                datetime.strptime(args.end, '%Y-%m-%d')
            except ValueError:
                print(f"❌ エラー: 終了日の形式が不正です: {args.end}")
                print("正しい形式: YYYY-MM-DD (例: 2024-12-31)")
                sys.exit(1)

        # BacktestEngineを初期化（Gemini API接続はスキップ）
        engine = BacktestEngine(
            symbol=args.symbol,
            start_date=args.start,
            end_date=args.end,
            skip_api_check=True  # リセット処理にはAPI接続不要
        )

        # リセット実行
        confirm = not args.yes
        success = engine.reset_backtest_tables(confirm=confirm)

        if success:
            print("✓ リセットが完了しました。")
            sys.exit(0)
        else:
            print("リセットがキャンセルまたは失敗しました。")
            sys.exit(1)

    except KeyboardInterrupt:
        print("")
        print("キャンセルされました。")
        sys.exit(1)
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
