"""
========================================
バックテストエンジン テストスクリプト
========================================

バックテストエンジンの動作確認用スクリプト。
短期間（1週間）のバックテストを実行して結果を表示します。

【使用方法】
python test_backtest.py

【確認事項】
- バックテストエンジンが正常に動作する
- トレードシミュレーターが正常に動作する
- 統計が正しく計算される
- データベースに保存される

【作成日】2025-10-23
"""

import sys
import logging
from datetime import datetime

from src.backtest.backtest_engine import BacktestEngine


def setup_logging():
    """ログ設定の初期化"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def main():
    """メインテスト処理"""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 80)
    logger.info("バックテストエンジン テスト開始")
    logger.info("=" * 80)
    logger.info("")

    # テスト設定（短期間）
    symbol = 'USDJPY'
    start_date = '2024-01-01'  # 1ヶ月のテスト
    end_date = '2024-01-31'
    initial_balance = 100000.0
    ai_model = 'flash'
    sampling_interval_hours = 24  # 1日1回

    # CSV/ZIPファイルパス（存在する場合）
    # Option 1: 単一ZIPファイル
    csv_path = 'data/tick_data/USDJPY/ticks_USDJPY-oj5k_2024-01.zip'

    # Option 2: ディレクトリ（複数ファイル）
    # csv_path = 'data/tick_data/USDJPY/'

    # Option 3: MT5データ使用（csv_path=Noneにする）
    # csv_path = None

    logger.info("テスト設定:")
    logger.info(f"  Symbol: {symbol}")
    logger.info(f"  Period: {start_date} to {end_date}")
    logger.info(f"  Initial Balance: {initial_balance:,.0f} JPY")
    logger.info(f"  AI Model: {ai_model}")
    logger.info(f"  Sampling: {sampling_interval_hours} hours")
    logger.info(f"  Data Source: {csv_path if csv_path else 'MT5'}")
    logger.info("")

    # バックテストエンジン初期化
    logger.info("バックテストエンジンを初期化中...")
    engine = BacktestEngine(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        initial_balance=initial_balance,
        ai_model=ai_model,
        sampling_interval_hours=sampling_interval_hours,
        risk_percent=1.0,
        csv_path=csv_path  # CSVパス指定（Noneの場合はMT5使用）
    )
    logger.info("")

    # バックテスト実行
    logger.info("バックテストを実行中...")
    logger.info("（注: AI分析を実行するため、数分かかる場合があります）")
    logger.info("")

    results = engine.run()

    # 結果の詳細表示
    if results:
        logger.info("")
        logger.info("=" * 80)
        logger.info("テスト結果")
        logger.info("=" * 80)
        logger.info("")

        # 基本情報
        logger.info("[基本情報]")
        logger.info(f"  初期残高: {results['initial_balance']:,.0f} JPY")
        logger.info(f"  最終残高: {results['final_balance']:,.0f} JPY")
        logger.info(f"  純利益: {results['net_profit']:+,.0f} JPY")
        logger.info(f"  リターン: {results['return_pct']:+.2f}%")
        logger.info("")

        # トレード統計
        logger.info("[トレード統計]")
        logger.info(f"  総トレード数: {results['total_trades']}")
        logger.info(f"  勝ちトレード: {results['winning_trades']}")
        logger.info(f"  負けトレード: {results['losing_trades']}")
        logger.info(f"  勝率: {results['win_rate']:.2f}%")
        logger.info("")

        # 損益詳細
        logger.info("[損益詳細]")
        logger.info(f"  総利益: {results['total_profit']:,.0f} JPY")
        logger.info(f"  総損失: {results['total_loss']:,.0f} JPY")
        logger.info(f"  平均利益: {results['avg_profit']:,.0f} JPY")
        logger.info(f"  平均損失: {results['avg_loss']:,.0f} JPY")
        logger.info(f"  プロフィットファクター: {results['profit_factor']:.2f}")
        logger.info("")

        # リスク指標
        logger.info("[リスク指標]")
        logger.info(f"  最大ドローダウン: {results['max_drawdown']:,.0f} JPY")
        logger.info(f"  最大DD率: {results['max_drawdown_pct']:.2f}%")
        logger.info("")

        # パフォーマンス評価
        logger.info("[パフォーマンス評価]")

        rating = "要改善"
        if (results['return_pct'] >= 10 and
            results['win_rate'] >= 60 and
            results['profit_factor'] >= 2.0):
            rating = "優秀"
        elif (results['return_pct'] >= 5 and
              results['win_rate'] >= 50 and
              results['profit_factor'] >= 1.5):
            rating = "良好"
        elif (results['return_pct'] >= 0 and
              results['win_rate'] >= 40 and
              results['profit_factor'] >= 1.0):
            rating = "普通"

        logger.info(f"  総合評価: {rating}")
        logger.info("")

        # 成功判定
        logger.info("=" * 80)
        if results['total_trades'] > 0:
            logger.info("[成功] バックテストが正常に完了しました ✅")
        else:
            logger.warning("[警告] トレードが実行されませんでした")
            logger.warning("  期間が短すぎるか、AI判断がHOLDのみだった可能性があります")
        logger.info("=" * 80)
        logger.info("")

        logger.info("結果はbacktest_resultsテーブルに保存されました。")
        logger.info("詳細はbacktest_summaryビューで確認できます：")
        logger.info("  SELECT * FROM backtest_summary ORDER BY created_at DESC LIMIT 1;")
        logger.info("")

    else:
        logger.error("")
        logger.error("=" * 80)
        logger.error("[失敗] バックテストが失敗しました ❌")
        logger.error("=" * 80)
        logger.error("")
        logger.error("エラーログを確認してください。")
        logger.error("")

    logger.info("=" * 80)
    logger.info("テスト終了")
    logger.info("=" * 80)
    logger.info("")


if __name__ == '__main__':
    main()
