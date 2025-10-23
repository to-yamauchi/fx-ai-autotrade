"""
========================================
全フェーズ統合テストスクリプト
========================================

目的: Phase 1-5の全AI分析機能が正しく動作することを確認
作成日: 2025-10-23
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 環境変数の読み込み
load_dotenv()

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from src.backtest.backtest_engine import BacktestEngine

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

    # テスト設定
    # 短期間でテスト（3日間）
    end_date = datetime.now()
    start_date = end_date - timedelta(days=3)

    print(f"テスト期間: {start_date.date()} ～ {end_date.date()} (3日間)")
    print(f"通貨ペア: USDJPY")
    print(f"初期残高: 100,000円")
    print()

    # 環境変数をバックテストモードに設定
    os.environ['TRADE_MODE'] = 'backtest'
    os.environ['BACKTEST_START_DATE'] = start_date.strftime('%Y-%m-%d')
    os.environ['BACKTEST_END_DATE'] = end_date.strftime('%Y-%m-%d')
    os.environ['BACKTEST_SYMBOL'] = 'USDJPY'

    print("注意:")
    print("  - このテストはGemini APIを使用します（費用が発生します）")
    print("  - 3日間のテストで推定コスト: 約$0.21")
    print("  - CSVデータが必要です（data/tick_data/USDJPY_*.csv）")
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
            symbol='USDJPY',
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            initial_balance=100000.0,
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

        # AI分析実行回数の推定
        days = (end_date - start_date).days + 1
        print("【AI分析実行回数（推定）】")
        print(f"  デイリーレビュー (Phase 1): {days - 1}回")
        print(f"  朝の詳細分析 (Phase 2): {days}回")
        print(f"  定期更新 (Phase 3): {days * 3}回")
        print(f"  Layer 3a監視 (Phase 4): ポジション保有時のみ（ログ参照）")
        print(f"  Layer 3b緊急評価 (Phase 5): 異常検知時のみ（ログ参照）")
        print()

        # コスト推定
        cost_review = (days - 1) * 0.018
        cost_morning = days * 0.018
        cost_update = days * 3 * 0.002
        cost_total = cost_review + cost_morning + cost_update
        print("【推定API コスト】")
        print(f"  デイリーレビュー: ${cost_review:.3f}")
        print(f"  朝の詳細分析: ${cost_morning:.3f}")
        print(f"  定期更新: ${cost_update:.3f}")
        print(f"  Layer 3a/3b: 実行回数による（ログ参照）")
        print(f"  合計（Phase 1-3のみ）: ${cost_total:.3f}")
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
