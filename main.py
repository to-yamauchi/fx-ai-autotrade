"""
========================================
FX自動トレードシステム - メインエントリーポイント
========================================

ファイル名: main.py
パス: main.py

【概要】
システムのメインエントリーポイントです。
起動チェックを実行後、トレードモードに応じた処理を実行します。

【実行モード】
- backtest: 過去データでバックテスト実行
- demo: DEMO口座でリアルタイムトレード
- live: 本番口座でリアルタイムトレード

【使用例】
```bash
# .envでTRADE_MODEを設定
TRADE_MODE=backtest python main.py
TRADE_MODE=demo python main.py
TRADE_MODE=live python main.py
```

【作成日】2025-10-23
"""

import sys
import logging
from datetime import datetime

from src.utils.startup_checker import StartupChecker
from src.utils.trade_mode import get_trade_mode_config
from src.ai_analysis.ai_analyzer import AIAnalyzer
from src.trade_execution.position_manager import PositionManager


def setup_logging():
    """ログ設定の初期化"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/fx_autotrade.log'),
            logging.StreamHandler()
        ]
    )


def run_backtest_mode():
    """
    バックテストモードの実行

    過去データを使用してシステムの性能を検証します。
    """
    logger = logging.getLogger(__name__)
    mode_config = get_trade_mode_config()

    logger.info("=" * 80)
    logger.info("バックテストモード開始")
    logger.info("=" * 80)

    # 期間とシンボルを取得
    start_date, end_date = mode_config.get_backtest_period()
    symbol = mode_config.get_backtest_symbol()

    logger.info(f"期間: {start_date.date()} ～ {end_date.date()}")
    logger.info(f"シンボル: {symbol}")
    logger.info("")

    # AI分析の実行
    logger.info("AI分析を実行中...")
    analyzer = AIAnalyzer(symbol=symbol, model='flash')
    ai_result = analyzer.analyze_market()

    logger.info(f"AI判断: {ai_result['action']}")
    logger.info(f"信頼度: {ai_result.get('confidence', 0)}%")
    logger.info(f"理由: {ai_result.get('reasoning', 'N/A')[:100]}...")
    logger.info("")

    # ポジション管理（バックテストモードではMT5使用しない）
    logger.info("トレード判断を処理中...")
    position_manager = PositionManager(symbol=symbol, use_mt5=False)
    result = position_manager.process_ai_judgment(ai_result)

    logger.info(f"結果: {result['message']}")
    logger.info("")

    # サマリー表示
    logger.info("=" * 80)
    logger.info("バックテストモード完了")
    logger.info("=" * 80)
    logger.info("")
    logger.info("結果はbacktest_ai_judgmentsテーブルに保存されました。")
    logger.info("詳細はbacktest_summaryビューで確認できます。")
    logger.info("")


def run_demo_mode():
    """
    DEMOモードの実行

    リアルタイムデータでDEMO口座にトレードを実行します。
    """
    logger = logging.getLogger(__name__)

    logger.info("=" * 80)
    logger.info("DEMOモード開始")
    logger.info("=" * 80)
    logger.info("")

    # シンボル設定
    symbol = 'USDJPY'

    # AI分析の実行
    logger.info("リアルタイムデータでAI分析を実行中...")
    analyzer = AIAnalyzer(symbol=symbol, model='flash')
    ai_result = analyzer.analyze_market()

    logger.info(f"AI判断: {ai_result['action']}")
    logger.info(f"信頼度: {ai_result.get('confidence', 0)}%")
    logger.info(f"理由: {ai_result.get('reasoning', 'N/A')[:100]}...")
    logger.info("")

    # ポジション管理（MT5を使用）
    logger.info("DEMO口座でトレードを実行中...")
    position_manager = PositionManager(symbol=symbol, use_mt5=True)
    result = position_manager.process_ai_judgment(ai_result)

    if result['success']:
        logger.info(f"✓ トレード成功: ticket={result['ticket']}")
    else:
        logger.warning(f"✗ トレード失敗: {result['message']}")
    logger.info("")

    # サマリー表示
    logger.info("=" * 80)
    logger.info("DEMOモード完了")
    logger.info("=" * 80)
    logger.info("")
    logger.info("結果はdemo_ai_judgmentsテーブルに保存されました。")
    logger.info("詳細はdemo_summaryビューで確認できます。")
    logger.info("")


def run_live_mode():
    """
    本番モードの実行

    リアルタイムデータで本番口座にトレードを実行します。
    """
    logger = logging.getLogger(__name__)

    logger.info("=" * 80)
    logger.info("本番モード開始")
    logger.info("=" * 80)
    logger.info("")
    logger.warning("⚠ 本番モードで実行中です！実際の資金が使用されます。")
    logger.info("")

    # シンボル設定
    symbol = 'USDJPY'

    # AI分析の実行
    logger.info("リアルタイムデータでAI分析を実行中...")
    analyzer = AIAnalyzer(symbol=symbol, model='flash')
    ai_result = analyzer.analyze_market()

    logger.info(f"AI判断: {ai_result['action']}")
    logger.info(f"信頼度: {ai_result.get('confidence', 0)}%")
    logger.info(f"理由: {ai_result.get('reasoning', 'N/A')[:100]}...")
    logger.info("")

    # ポジション管理（MT5を使用）
    logger.info("本番口座でトレードを実行中...")
    position_manager = PositionManager(symbol=symbol, use_mt5=True)
    result = position_manager.process_ai_judgment(ai_result)

    if result['success']:
        logger.info(f"✓ トレード成功: ticket={result['ticket']}")
    else:
        logger.warning(f"✗ トレード失敗: {result['message']}")
    logger.info("")

    # サマリー表示
    logger.info("=" * 80)
    logger.info("本番モード完了")
    logger.info("=" * 80)
    logger.info("")
    logger.info("結果はai_judgmentsテーブルに保存されました。")
    logger.info("")


def main():
    """メインエントリーポイント"""
    # ログ設定
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("")
    logger.info("=" * 80)
    logger.info("  FX自動トレードシステム起動")
    logger.info("=" * 80)
    logger.info("")

    # 起動チェック
    checker = StartupChecker()
    is_ok, errors = checker.check_all()

    if not is_ok:
        logger.error("起動チェックに失敗しました。上記のエラーを修正してください。")
        sys.exit(1)

    # モード取得
    mode_config = get_trade_mode_config()
    mode = mode_config.get_mode()

    try:
        # モード別実行
        if mode_config.is_backtest():
            run_backtest_mode()
        elif mode_config.is_demo():
            run_demo_mode()
        elif mode_config.is_live():
            run_live_mode()
        else:
            logger.error(f"不明なモード: {mode.value}")
            sys.exit(1)

        logger.info("システム正常終了")
        sys.exit(0)

    except KeyboardInterrupt:
        logger.info("")
        logger.info("ユーザーによる中断")
        sys.exit(0)

    except Exception as e:
        logger.error(f"実行エラー: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
