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
from src.monitoring.monitor_orchestrator import MonitorOrchestrator
from src.backtest.backtest_engine import BacktestEngine


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

    logger.info("=" * 80)
    logger.info("バックテストモード開始")
    logger.info("=" * 80)
    logger.info("")

    # シンボルと期間設定
    symbol = 'USDJPY'
    start_date = '2024-09-01'  # 1ヶ月のバックテスト
    end_date = '2024-09-30'
    initial_balance = 100000.0
    ai_model = 'flash'
    sampling_interval_hours = 24  # 1日1回AI分析

    logger.info(f"Symbol: {symbol}")
    logger.info(f"Period: {start_date} to {end_date}")
    logger.info(f"Initial Balance: {initial_balance:,.0f} JPY")
    logger.info(f"AI Model: {ai_model}")
    logger.info(f"Sampling Interval: {sampling_interval_hours} hours")
    logger.info("")

    # バックテストエンジン初期化
    engine = BacktestEngine(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        initial_balance=initial_balance,
        ai_model=ai_model,
        sampling_interval_hours=sampling_interval_hours,
        risk_percent=1.0
    )

    # バックテスト実行
    results = engine.run()

    # サマリー表示
    logger.info("=" * 80)
    logger.info("バックテストモード完了")
    logger.info("=" * 80)
    logger.info("")

    if results:
        logger.info("結果サマリー:")
        logger.info(f"  最終残高: {results['final_balance']:,.0f} JPY")
        logger.info(f"  純利益: {results['net_profit']:,.0f} JPY")
        logger.info(f"  リターン: {results['return_pct']:.2f}%")
        logger.info(f"  勝率: {results['win_rate']:.2f}%")
        logger.info(f"  プロフィットファクター: {results['profit_factor']:.2f}")
        logger.info(f"  最大ドローダウン: {results['max_drawdown']:,.0f} JPY ({results['max_drawdown_pct']:.2f}%)")
        logger.info("")
        logger.info("詳細結果はbacktest_resultsテーブルに保存されました。")
    else:
        logger.error("バックテストが失敗しました。")

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

    # モニタリングシステムの初期化
    logger.info("3層モニタリングシステムを初期化中...")
    orchestrator = MonitorOrchestrator(symbol=symbol, ai_model='flash')
    logger.info("")

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
        logger.info(f"[成功] トレード成功: ticket={result['ticket']}")
        logger.info("")

        # トレード成功時はモニタリングを開始
        logger.info("トレード成功！モニタリングシステムを起動します...")
        logger.info("")

        orchestrator.start_all()

        # ポジションを登録
        orchestrator.register_position_entry(
            ticket=result['ticket'],
            action=ai_result['action'],
            confidence=ai_result.get('confidence', 0),
            reasoning=ai_result.get('reasoning', '')
        )
        logger.info("")

        # モニタリングステータス表示
        logger.info("モニタリングシステムが起動しました。")
        logger.info("以下の3層でポジションを監視します：")
        logger.info("  - Layer 1: 緊急停止（100ms間隔、50pips SL、口座2%損失）")
        logger.info("  - Layer 2: 異常検知（5分間隔、DD10%、逆行8pips、スプレッド5pips）")
        logger.info("  - Layer 3: AI再評価（30分間隔、判断反転、信頼度60%）")
        logger.info("")
        logger.info("Ctrl+Cで終了します...")
        logger.info("")

        try:
            # モニタリングを継続（ユーザーが中断するまで）
            import time
            while True:
                time.sleep(60)  # 1分ごとにステータス表示
                orchestrator.print_status()
        except KeyboardInterrupt:
            logger.info("")
            logger.info("ユーザーによる中断を検知")
            logger.info("")
        finally:
            # モニタリング停止
            orchestrator.stop_all()
    else:
        logger.warning(f"[失敗] トレード失敗: {result['message']}")
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

    # モニタリングシステムの初期化
    logger.info("3層モニタリングシステムを初期化中...")
    orchestrator = MonitorOrchestrator(symbol=symbol, ai_model='flash')
    logger.info("")

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
        logger.info(f"[成功] トレード成功: ticket={result['ticket']}")
        logger.info("")

        # トレード成功時はモニタリングを開始
        logger.info("トレード成功！モニタリングシステムを起動します...")
        logger.info("")

        orchestrator.start_all()

        # ポジションを登録
        orchestrator.register_position_entry(
            ticket=result['ticket'],
            action=ai_result['action'],
            confidence=ai_result.get('confidence', 0),
            reasoning=ai_result.get('reasoning', '')
        )
        logger.info("")

        # モニタリングステータス表示
        logger.info("モニタリングシステムが起動しました。")
        logger.info("以下の3層でポジションを監視します：")
        logger.info("  - Layer 1: 緊急停止（100ms間隔、50pips SL、口座2%損失）")
        logger.info("  - Layer 2: 異常検知（5分間隔、DD10%、逆行8pips、スプレッド5pips）")
        logger.info("  - Layer 3: AI再評価（30分間隔、判断反転、信頼度60%）")
        logger.info("")
        logger.warning("⚠ 本番モードで監視中！Ctrl+Cで終了します...")
        logger.info("")

        try:
            # モニタリングを継続（ユーザーが中断するまで）
            import time
            while True:
                time.sleep(60)  # 1分ごとにステータス表示
                orchestrator.print_status()
        except KeyboardInterrupt:
            logger.info("")
            logger.info("ユーザーによる中断を検知")
            logger.info("")
        finally:
            # モニタリング停止
            orchestrator.stop_all()
    else:
        logger.warning(f"[失敗] トレード失敗: {result['message']}")
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
