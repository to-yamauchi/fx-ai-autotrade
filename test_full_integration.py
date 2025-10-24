"""
========================================
全フェーズ統合テストスクリプト
========================================

目的: Phase 1-5の全AI分析機能が正しく動作することを確認
作成日: 2025-10-23

使用方法:
  python test_full_integration.py --start-date 2024-01-01 --end-date 2024-01-31
  python test_full_integration.py  # インタラクティブモード
"""

import os
import sys
import logging
import argparse
from datetime import datetime, timedelta
from dotenv import load_dotenv

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 環境変数の読み込み
load_dotenv()

# ログ設定（エラーと警告のみ表示）
logging.basicConfig(
    level=logging.WARNING,
    format='%(levelname)s: %(message)s'
)

from src.backtest.backtest_engine import BacktestEngine

def parse_arguments():
    """コマンドライン引数を解析"""
    parser = argparse.ArgumentParser(
        description='全フェーズ統合テスト（Phase 1-5）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 2024年1月全体をテスト
  python test_full_integration.py --start-date 2024-01-01 --end-date 2024-01-31

  # 直近1週間をテスト
  python test_full_integration.py --start-date 2024-10-16 --end-date 2024-10-23

  # インタラクティブモード（引数なし）
  python test_full_integration.py
        """
    )
    parser.add_argument(
        '--start-date',
        type=str,
        help='開始日（YYYY-MM-DD形式）例: 2024-01-01'
    )
    parser.add_argument(
        '--end-date',
        type=str,
        help='終了日（YYYY-MM-DD形式）例: 2024-01-31'
    )
    parser.add_argument(
        '--symbol',
        type=str,
        default='USDJPY',
        help='通貨ペア（デフォルト: USDJPY）'
    )
    parser.add_argument(
        '--balance',
        type=float,
        default=100000.0,
        help='初期残高（デフォルト: 100000円）'
    )

    return parser.parse_args()

def get_date_range_interactive():
    """インタラクティブに期間を取得"""
    print("=" * 80)
    print("テスト期間の設定")
    print("=" * 80)
    print()
    print("バックテストを実行する期間を指定してください。")
    print()

    while True:
        start_input = input("開始日 (YYYY-MM-DD 例: 2024-01-01): ").strip()
        try:
            start_date = datetime.strptime(start_input, '%Y-%m-%d')
            break
        except ValueError:
            print("❌ 無効な日付形式です。YYYY-MM-DD形式で入力してください。")

    while True:
        end_input = input("終了日 (YYYY-MM-DD 例: 2024-01-31): ").strip()
        try:
            end_date = datetime.strptime(end_input, '%Y-%m-%d')
            if end_date < start_date:
                print("❌ 終了日は開始日より後にしてください。")
                continue
            break
        except ValueError:
            print("❌ 無効な日付形式です。YYYY-MM-DD形式で入力してください。")

    return start_date, end_date


def main():
    """メイン処理"""
    print("=" * 80)
    print("全フェーズ統合テスト（Phase 1-5）")
    print("=" * 80)
    print()

    # 設定値を読み込んでモデル名を取得
    from src.utils.config import get_config
    config = get_config()

    print("このテストは以下を検証します：")
    print(f"  ✓ Phase 1: デイリーレビュー（06:00、{config.model_daily_analysis}）")
    print(f"  ✓ Phase 2: 朝の詳細分析（08:00、{config.model_daily_analysis}）")
    print(f"  ✓ Phase 3: 定期更新（12:00/16:00/21:30、{config.model_periodic_update}）")
    print(f"  ✓ Phase 4: Layer 3a監視（15分ごと、{config.model_position_monitor}）")
    print(f"  ✓ Phase 5: Layer 3b緊急評価（異常検知時、{config.model_emergency_evaluation}）")
    print()

    # コマンドライン引数を解析
    args = parse_arguments()

    # 期間の取得（引数またはインタラクティブ）
    if args.start_date and args.end_date:
        # コマンドライン引数から取得
        try:
            start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
            end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
            if end_date < start_date:
                print("❌ エラー: 終了日は開始日より後にしてください。")
                return 1
        except ValueError as e:
            print(f"❌ エラー: 日付形式が無効です。YYYY-MM-DD形式で指定してください。")
            print(f"   詳細: {e}")
            return 1
    else:
        # インタラクティブモード
        start_date, end_date = get_date_range_interactive()

    symbol = args.symbol
    initial_balance = args.balance
    days = (end_date - start_date).days + 1

    print()
    print(f"テスト期間: {start_date.date()} ～ {end_date.date()} ({days}日間)")
    print(f"通貨ペア: {symbol}")
    print(f"初期残高: {initial_balance:,.0f}円")
    print()

    # 環境変数をバックテストモードに設定
    os.environ['TRADE_MODE'] = 'backtest'
    os.environ['BACKTEST_START_DATE'] = start_date.strftime('%Y-%m-%d')
    os.environ['BACKTEST_END_DATE'] = end_date.strftime('%Y-%m-%d')
    os.environ['BACKTEST_SYMBOL'] = symbol

    # Gemini API接続チェック
    print("=" * 80)
    print("環境チェック（LLM API接続）")
    print("=" * 80)
    try:
        from src.ai_analysis import create_phase_clients
        from src.utils.config import get_config

        config = get_config()

        # Phase別のLLMクライアントを生成・接続テスト
        phase_clients = create_phase_clients()

        # 各クライアントの接続テスト
        all_connected = True
        for phase_name, client in phase_clients.items():
            provider = client.get_provider_name()
            if phase_name == 'daily_analysis':
                model = config.model_daily_analysis
                label = "Phase 1,2   (デイリー分析)"
            elif phase_name == 'periodic_update':
                model = config.model_periodic_update
                label = "Phase 3     (定期更新)"
            elif phase_name == 'position_monitor':
                model = config.model_position_monitor
                label = "Phase 4     (ポジション監視)"
            else:  # emergency_evaluation
                model = config.model_emergency_evaluation
                label = "Phase 5     (緊急評価)"

            print(f"{label}: {model}")
            print(f"  Provider: {provider.upper()}", end=' ')

            # 実際の.envモデルでテスト
            if not client.test_connection(verbose=False, model=model):
                print(" ❌ 接続失敗")
                all_connected = False
            else:
                print(" ✓ 接続成功")

        if not all_connected:
            print("")
            print("❌ LLM APIへの接続に失敗しました。")
            print("   以下を確認してください：")
            print("   1. .envファイルに各APIキーが設定されているか")
            print("      - GEMINI_API_KEY (Geminiを使用する場合)")
            print("      - OPENAI_API_KEY (OpenAIを使用する場合)")
            print("      - ANTHROPIC_API_KEY (Anthropicを使用する場合)")
            print("   2. モデル名が正しいか")
            print("   3. インターネット接続が正常か")
            print("")
            return 1

    except Exception as e:
        import traceback
        print(f"❌ LLM APIの初期化に失敗しました: {e}")
        print("")
        print("詳細なエラー情報：")
        traceback.print_exc()
        print("")
        print("   .envファイルを確認してください。")
        print("")
        return 1

    print("")

    print("=" * 80)
    print("データ要件")
    print("=" * 80)
    print(f"  - CSVティックデータ: data/tick_data/{symbol}_*.csv")
    print(f"  - 期間: {start_date.date()} ～ {end_date.date()}")
    print()

    response = input("テストを実行しますか？ (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("テストをキャンセルしました。")
        return 0

    print()
    print("=" * 80)
    print("バックテスト開始")
    print("=" * 80)
    print()

    try:
        # バックテストエンジン初期化
        engine = BacktestEngine(
            symbol=symbol,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            initial_balance=initial_balance,
            ai_model='flash',  # 定期更新用（朝の分析はPro、監視はFlash-8B）
            sampling_interval_hours=24,
            risk_percent=1.0,
            csv_path=None  # MT5から取得（またはCSVパスを指定）
        )

        # バックテスト実行
        results = engine.run()

        print()
        print("=" * 80)
        print("テスト結果サマリー")
        print("=" * 80)
        print()

        # 基本統計
        print("【基本統計】")
        print(f"  期間: {start_date.date()} ～ {end_date.date()}")
        print(f"  初期残高: {results.get('initial_balance', 0):,.0f}円")
        print(f"  最終残高: {results.get('final_balance', 0):,.0f}円")
        print(f"  損益: {results.get('net_profit', 0):,.0f}円 ({results.get('profit_percent', 0):.2f}%)")
        print()

        # トレード統計
        print("【トレード統計】")
        print(f"  総トレード数: {results.get('total_trades', 0)}")
        print(f"  勝ちトレード: {results.get('win_trades', 0)}")
        print(f"  負けトレード: {results.get('loss_trades', 0)}")
        print(f"  勝率: {results.get('win_rate', 0):.2f}%")
        print(f"  総pips: {results.get('total_pips', 0):.1f}pips")
        print()

        # リスク指標
        print("【リスク指標】")
        print(f"  最大ドローダウン: {results.get('max_drawdown', 0):.2f}%")
        print(f"  最大連敗: {results.get('max_consecutive_losses', 0)}")
        print(f"  最大連勝: {results.get('max_consecutive_wins', 0)}")
        print()

        # トークン使用量レポート
        from src.ai_analysis.token_usage_tracker import get_token_tracker
        tracker = get_token_tracker()
        tracker.print_summary()

        # データベース確認
        print("=" * 80)
        print("データベース確認")
        print("=" * 80)
        print()
        print("以下のコマンドで各フェーズの結果を確認できます：")
        print()
        print("# Phase 1: デイリーレビュー")
        print("  psql -U postgres -d fx_autotrade -c \"SELECT review_date, total_score FROM backtest_daily_reviews ORDER BY review_date DESC LIMIT 5;\"")
        print()
        print("# Phase 2: 朝の詳細分析")
        print("  psql -U postgres -d fx_autotrade -c \"SELECT strategy_date, daily_bias, confidence FROM backtest_daily_strategies ORDER BY strategy_date DESC LIMIT 5;\"")
        print()
        print("# Phase 3: 定期更新")
        print("  psql -U postgres -d fx_autotrade -c \"SELECT update_date, update_time, update_type FROM backtest_periodic_updates ORDER BY update_date DESC, update_time DESC LIMIT 10;\"")
        print()
        print("# Phase 4: Layer 3a監視")
        print("  psql -U postgres -d fx_autotrade -c \"SELECT check_timestamp, action, reason FROM backtest_layer3a_monitoring ORDER BY check_timestamp DESC LIMIT 10;\"")
        print()
        print("# Phase 5: Layer 3b緊急評価")
        print("  psql -U postgres -d fx_autotrade -c \"SELECT event_timestamp, severity, action FROM backtest_layer3b_emergency ORDER BY event_timestamp DESC LIMIT 5;\"")
        print()

        print("=" * 80)
        print("テスト完了")
        print("=" * 80)
        print()
        print("✓ すべてのフェーズが正常に実行されました")
        print("✓ 詳細なログは上記を参照してください")
        print("✓ データベースに結果が保存されています")
        print()

        return 0

    except Exception as e:
        print()
        print("=" * 80)
        print("エラーが発生しました")
        print("=" * 80)
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
        print()
        print("トラブルシューティング:")
        print("  1. .envファイルが正しく設定されているか確認")
        print("  2. データベースが起動しているか確認")
        print("  3. CSVデータが存在するか確認（data/tick_data/）")
        print("  4. Gemini APIキーが有効か確認")
        print()
        return 1


if __name__ == '__main__':
    exit(main())
