"""
========================================
モニタリングシステム テストスクリプト
========================================

既存のオープンポジションを監視するテストスクリプト。
3層モニタリングシステムの動作確認用。

【使用方法】
python test_monitoring.py

【確認事項】
- Layer 1: 100ms間隔でログが出力される
- Layer 2: 5分間隔でログが出力される
- Layer 3: 30分間隔でログが出力される
- Ctrl+Cで安全に停止できる

【作成日】2025-10-23
"""

import sys
import logging
from datetime import datetime
import MetaTrader5 as mt5
import os
from dotenv import load_dotenv

from src.monitoring.monitor_orchestrator import MonitorOrchestrator


def setup_logging():
    """ログ設定の初期化"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def initialize_mt5():
    """MT5の初期化とログイン"""
    logger = logging.getLogger(__name__)

    # 環境変数の読み込み
    load_dotenv()

    # MT5の初期化
    if not mt5.initialize():
        logger.error("MT5初期化失敗")
        return False

    # ログイン
    login = int(os.getenv('MT5_LOGIN'))
    password = os.getenv('MT5_PASSWORD')
    server = os.getenv('MT5_SERVER')

    authorized = mt5.login(login=login, password=password, server=server)
    if not authorized:
        logger.error(f"MT5ログイン失敗: {mt5.last_error()}")
        mt5.shutdown()
        return False

    logger.info(f"MT5ログイン成功: {login}@{server}")
    return True


def get_open_positions(symbol='USDJPY'):
    """オープンポジションを取得"""
    positions = mt5.positions_get(symbol=symbol)
    if positions is None:
        return []

    return [
        {
            'ticket': pos.ticket,
            'type': 'BUY' if pos.type == mt5.ORDER_TYPE_BUY else 'SELL',
            'volume': pos.volume,
            'price_open': pos.price_open,
            'price_current': pos.price_current,
            'profit': pos.profit,
            'time': datetime.fromtimestamp(pos.time),
        }
        for pos in positions
    ]


def main():
    """メインテスト処理"""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 80)
    logger.info("モニタリングシステム テスト開始")
    logger.info("=" * 80)
    logger.info("")

    # MT5初期化
    logger.info("MT5を初期化中...")
    if not initialize_mt5():
        logger.error("MT5初期化に失敗しました")
        return
    logger.info("")

    # 既存ポジションを確認
    symbol = 'USDJPY'
    logger.info(f"既存のオープンポジションを確認中 ({symbol})...")
    positions = get_open_positions(symbol)

    if not positions:
        logger.warning(f"{symbol}のオープンポジションが見つかりません")
        logger.info("テストを実行するには、先にポジションをオープンしてください：")
        logger.info("  python main.py  # DEMO口座でトレード実行")
        logger.info("")
        mt5.shutdown()
        return

    logger.info(f"オープンポジション: {len(positions)}件")
    for pos in positions:
        logger.info(
            f"  ticket={pos['ticket']}, "
            f"type={pos['type']}, "
            f"volume={pos['volume']}, "
            f"open={pos['price_open']}, "
            f"current={pos['price_current']}, "
            f"profit={pos['profit']:.2f}"
        )
    logger.info("")

    # モニタリングシステムの初期化
    logger.info("3層モニタリングシステムを初期化中...")
    orchestrator = MonitorOrchestrator(
        symbol=symbol,
        ai_model='flash',
        enable_layer1=True,
        enable_layer2=True,
        enable_layer3=True
    )
    logger.info("")

    # 全モニター起動
    orchestrator.start_all()

    # 既存ポジションを登録（Layer 3用）
    # 注: エントリー時の判断が不明なので、デフォルト値を使用
    logger.info("既存ポジションをモニターに登録中...")
    for pos in positions:
        orchestrator.register_position_entry(
            ticket=pos['ticket'],
            action=pos['type'],
            confidence=70.0,  # デフォルト値
            reasoning='Existing position (test mode)'
        )
    logger.info("")

    # モニタリング継続
    logger.info("=" * 80)
    logger.info("モニタリング開始")
    logger.info("=" * 80)
    logger.info("")
    logger.info("以下を監視中：")
    logger.info("  - Layer 1: 緊急停止（100ms間隔、50pips SL、口座2%損失）")
    logger.info("  - Layer 2: 異常検知（5分間隔、DD10%、逆行8pips、スプレッド5pips）")
    logger.info("  - Layer 3: AI再評価（30分間隔、判断反転、信頼度60%）")
    logger.info("")
    logger.info("1分ごとにステータスを表示します...")
    logger.info("Ctrl+Cで終了します")
    logger.info("")

    try:
        import time
        while True:
            time.sleep(60)  # 1分待機

            # ステータス表示
            orchestrator.print_status()

            # ポジション状態も表示
            current_positions = get_open_positions(symbol)
            logger.info(f"現在のオープンポジション: {len(current_positions)}件")
            for pos in current_positions:
                logger.info(
                    f"  ticket={pos['ticket']}, "
                    f"profit={pos['profit']:.2f}, "
                    f"current={pos['price_current']}"
                )
            logger.info("")

    except KeyboardInterrupt:
        logger.info("")
        logger.info("ユーザーによる中断を検知")
        logger.info("")

    finally:
        # モニタリング停止
        orchestrator.stop_all()

        # MT5シャットダウン
        mt5.shutdown()
        logger.info("MT5をシャットダウンしました")

    logger.info("")
    logger.info("=" * 80)
    logger.info("モニタリングシステム テスト終了")
    logger.info("=" * 80)
    logger.info("")


if __name__ == '__main__':
    main()
