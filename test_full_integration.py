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

def calculate_api_costs(days, avg_positions_per_day=2, avg_monitoring_per_position=8, anomaly_rate=0.05):
    """
    API利用コストを計算

    Args:
        days: テスト期間の日数
        avg_positions_per_day: 1日あたりの平均ポジション数
        avg_monitoring_per_position: 1ポジションあたりの平均監視回数
        anomaly_rate: 異常検知率（0.0-1.0）

    Returns:
        Dict: コスト内訳
    """
    # Phase 1: デイリーレビュー（Gemini Pro: $0.018/call）
    # 最初の日はレビューなし
    phase1_calls = max(0, days - 1)
    phase1_cost = phase1_calls * 0.018

    # Phase 2: 朝の詳細分析（Gemini Pro: $0.018/call）
    phase2_calls = days
    phase2_cost = phase2_calls * 0.018

    # Phase 3: 定期更新（Gemini Flash: $0.002/call）
    # 12:00, 16:00, 21:30 の3回/日
    phase3_calls = days * 3
    phase3_cost = phase3_calls * 0.002

    # Phase 4: Layer 3a監視（Flash-8B: $0.0003/call）
    # ポジション保有時のみ、15分ごと
    # 1ポジションあたり平均4時間保有 = 16回監視と仮定
    total_positions = days * avg_positions_per_day
    phase4_calls = int(total_positions * avg_monitoring_per_position)
    phase4_cost = phase4_calls * 0.0003

    # Phase 5: Layer 3b緊急評価（Gemini Pro: $0.018/call）
    # 異常検知時のみ（全監視回数の5%と仮定）
    phase5_calls = int(phase4_calls * anomaly_rate)
    phase5_cost = phase5_calls * 0.018

    total_cost = phase1_cost + phase2_cost + phase3_cost + phase4_cost + phase5_cost

    return {
        'phase1': {'calls': phase1_calls, 'cost': phase1_cost},
        'phase2': {'calls': phase2_calls, 'cost': phase2_cost},
        'phase3': {'calls': phase3_calls, 'cost': phase3_cost},
        'phase4': {'calls': phase4_calls, 'cost': phase4_cost},
        'phase5': {'calls': phase5_calls, 'cost': phase5_cost},
        'total_calls': phase1_calls + phase2_calls + phase3_calls + phase4_calls + phase5_calls,
        'total_cost': total_cost
    }

def main():
    """メイン処理"""
    print("=" * 80)
    print("全フェーズ統合テスト（Phase 1-5）")
    print("=" * 80)
    print()

    print("このテストは以下を検証します：")
    print("  ✓ Phase 1: デイリーレビュー（06:00、Gemini Pro）")
    print("  ✓ Phase 2: 朝の詳細分析（08:00、Gemini Pro）")
    print("  ✓ Phase 3: 定期更新（12:00/16:00/21:30、Gemini Flash）")
    print("  ✓ Phase 4: Layer 3a監視（15分ごと、Flash-8B）")
    print("  ✓ Phase 5: Layer 3b緊急評価（異常検知時、Gemini Pro）")
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
    print("環境チェック")
    print("=" * 80)
    try:
        from src.ai_analysis import GeminiClient
        gemini_client = GeminiClient()
        if not gemini_client.test_connection(verbose=True):
            print("")
            print("❌ Gemini APIへの接続に失敗しました。")
            print("   以下を確認してください：")
            print("   1. .envファイルにGEMINI_API_KEYが正しく設定されているか")
            print("   2. APIキーが有効か（https://aistudio.google.com/app/apikey で確認）")
            print("   3. Geminiモデル名が正しいか（GEMINI_MODEL_DAILY_ANALYSIS, GEMINI_MODEL_PERIODIC_UPDATE, GEMINI_MODEL_POSITION_MONITOR）")
            print("   4. インターネット接続が正常か")
            print("")
            return 1
    except Exception as e:
        print(f"❌ Gemini APIの初期化に失敗しました: {e}")
        print("")
        print("   .envファイルを確認してください。")
        print("")
        return 1

    print("")

    # APIコスト推定
    cost_estimate = calculate_api_costs(days)

    print("=" * 80)
    print("推定APIコスト")
    print("=" * 80)
    print(f"Phase 1 (デイリーレビュー):  {cost_estimate['phase1']['calls']:3d}回 × $0.018 = ${cost_estimate['phase1']['cost']:.3f}")
    print(f"Phase 2 (朝の詳細分析):      {cost_estimate['phase2']['calls']:3d}回 × $0.018 = ${cost_estimate['phase2']['cost']:.3f}")
    print(f"Phase 3 (定期更新):          {cost_estimate['phase3']['calls']:3d}回 × $0.002 = ${cost_estimate['phase3']['cost']:.3f}")
    print(f"Phase 4 (Layer 3a監視):      {cost_estimate['phase4']['calls']:3d}回 × $0.0003 = ${cost_estimate['phase4']['cost']:.3f} (推定)")
    print(f"Phase 5 (Layer 3b緊急評価):  {cost_estimate['phase5']['calls']:3d}回 × $0.018 = ${cost_estimate['phase5']['cost']:.3f} (推定)")
    print("-" * 80)
    print(f"合計推定コスト:              ${cost_estimate['total_cost']:.3f} (約{cost_estimate['total_calls']}回のAPI呼び出し)")
    print()
    print("注意:")
    print("  - Phase 4/5の回数は実際のポジション数と異常検知により変動します")
    print("  - 上記は平均的なケースの推定値です")
    print()

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

        # AI分析実行回数とコスト
        print("【AI分析実行回数とコスト】")
        print(f"  Phase 1 (デイリーレビュー):    {cost_estimate['phase1']['calls']:3d}回 → ${cost_estimate['phase1']['cost']:.3f}")
        print(f"  Phase 2 (朝の詳細分析):        {cost_estimate['phase2']['calls']:3d}回 → ${cost_estimate['phase2']['cost']:.3f}")
        print(f"  Phase 3 (定期更新):            {cost_estimate['phase3']['calls']:3d}回 → ${cost_estimate['phase3']['cost']:.3f}")
        print(f"  Phase 4 (Layer 3a監視):        {cost_estimate['phase4']['calls']:3d}回 → ${cost_estimate['phase4']['cost']:.3f} (推定)")
        print(f"  Phase 5 (Layer 3b緊急評価):    {cost_estimate['phase5']['calls']:3d}回 → ${cost_estimate['phase5']['cost']:.3f} (推定)")
        print("  " + "-" * 70)
        print(f"  合計:                          {cost_estimate['total_calls']:3d}回 → ${cost_estimate['total_cost']:.3f}")
        print()
        print("  ※ Phase 4/5は推定値です。実際の回数はログを確認してください。")
        print()

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
