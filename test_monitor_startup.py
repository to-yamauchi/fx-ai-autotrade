"""
========================================
モニター起動テスト
========================================

ポジションの有無に関わらず、モニターの起動・停止をテストします。
MT5接続が必要です。

【使用方法】
python test_monitor_startup.py

【確認事項】
- 各Layerが正常に起動する
- スレッドが正常に動作する
- ステータスが正常に取得できる
- 正常に停止できる

【作成日】2025-10-23
"""

import sys
import logging
from datetime import datetime
import MetaTrader5 as mt5
import os
from dotenv import load_dotenv
import time

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


def test_orchestrator_startup():
    """オーケストレーターの起動テスト"""
    logger = logging.getLogger(__name__)

    logger.info("=" * 80)
    logger.info("TEST 1: オーケストレーター起動テスト")
    logger.info("=" * 80)
    logger.info("")

    # オーケストレーター作成
    orchestrator = MonitorOrchestrator(
        symbol='USDJPY',
        ai_model='flash',
        enable_layer1=True,
        enable_layer2=True,
        enable_layer3=True
    )

    # 起動
    logger.info("モニター起動中...")
    orchestrator.start_all()
    logger.info("[成功] モニター起動完了")
    logger.info("")

    # 10秒待機
    logger.info("10秒間動作を確認...")
    time.sleep(10)

    # ステータス確認
    logger.info("ステータス取得中...")
    status = orchestrator.get_status()

    logger.info(f"Layer 1 Running: {status['layer1']['is_running']}")
    logger.info(f"Layer 1 Thread: {status['layer1']['thread_alive']}")
    logger.info(f"Layer 2 Running: {status['layer2']['is_running']}")
    logger.info(f"Layer 2 Thread: {status['layer2']['thread_alive']}")
    logger.info(f"Layer 3 Running: {status['layer3']['is_running']}")
    logger.info(f"Layer 3 Thread: {status['layer3']['thread_alive']}")
    logger.info("")

    # 停止
    logger.info("モニター停止中...")
    orchestrator.stop_all()
    logger.info("[成功] モニター停止完了")
    logger.info("")

    # 結果
    all_started = (
        status['layer1']['is_running'] and
        status['layer2']['is_running'] and
        status['layer3']['is_running']
    )
    all_threads_alive = (
        status['layer1']['thread_alive'] and
        status['layer2']['thread_alive'] and
        status['layer3']['thread_alive']
    )

    if all_started and all_threads_alive:
        logger.info("[合格] 全モニターが正常に起動・動作しました")
    else:
        logger.error("[不合格] 一部のモニターが正常に動作していません")

    logger.info("")
    return all_started and all_threads_alive


def test_individual_layers():
    """個別Layer起動テスト"""
    logger = logging.getLogger(__name__)

    logger.info("=" * 80)
    logger.info("TEST 2: 個別Layer起動テスト")
    logger.info("=" * 80)
    logger.info("")

    results = {}

    # Layer 1のみ
    logger.info("Layer 1のみ起動...")
    orch1 = MonitorOrchestrator(
        symbol='USDJPY',
        enable_layer1=True,
        enable_layer2=False,
        enable_layer3=False
    )
    orch1.start_all()
    time.sleep(3)
    status1 = orch1.get_status()
    results['layer1'] = status1['layer1']['is_running']
    logger.info(f"Layer 1: {'[成功]' if results['layer1'] else '[失敗]'}")
    orch1.stop_all()
    logger.info("")

    # Layer 2のみ
    logger.info("Layer 2のみ起動...")
    orch2 = MonitorOrchestrator(
        symbol='USDJPY',
        enable_layer1=False,
        enable_layer2=True,
        enable_layer3=False
    )
    orch2.start_all()
    time.sleep(3)
    status2 = orch2.get_status()
    results['layer2'] = status2['layer2']['is_running']
    logger.info(f"Layer 2: {'[成功]' if results['layer2'] else '[失敗]'}")
    orch2.stop_all()
    logger.info("")

    # Layer 3のみ
    logger.info("Layer 3のみ起動...")
    orch3 = MonitorOrchestrator(
        symbol='USDJPY',
        enable_layer1=False,
        enable_layer2=False,
        enable_layer3=True
    )
    orch3.start_all()
    time.sleep(3)
    status3 = orch3.get_status()
    results['layer3'] = status3['layer3']['is_running']
    logger.info(f"Layer 3: {'[成功]' if results['layer3'] else '[失敗]'}")
    orch3.stop_all()
    logger.info("")

    # 結果
    all_passed = all(results.values())
    if all_passed:
        logger.info("[合格] 全Layerが個別に正常動作しました")
    else:
        logger.error("[不合格] 一部のLayerが動作していません")

    logger.info("")
    return all_passed


def test_position_registration():
    """ポジション登録テスト"""
    logger = logging.getLogger(__name__)

    logger.info("=" * 80)
    logger.info("TEST 3: ポジション登録テスト")
    logger.info("=" * 80)
    logger.info("")

    orchestrator = MonitorOrchestrator(symbol='USDJPY')
    orchestrator.start_all()
    time.sleep(2)

    # ダミーポジションを登録
    logger.info("ダミーポジションを登録...")
    orchestrator.register_position_entry(
        ticket=999999,
        action='BUY',
        confidence=85.0,
        reasoning='Test position'
    )
    logger.info("[成功] ポジション登録完了")
    logger.info("")

    # ステータス確認
    time.sleep(2)
    status = orchestrator.get_status()
    logger.info(f"Layer 3 Tracked Positions: {status['layer3']['tracked_positions']}")

    # クリア
    logger.info("ポジション追跡をクリア...")
    orchestrator.clear_position_tracking(999999)
    logger.info("[成功] クリア完了")
    logger.info("")

    # 停止
    orchestrator.stop_all()

    # 結果
    if status['layer3']['tracked_positions'] >= 1:
        logger.info("[合格] ポジション登録が正常に動作しました")
        return True
    else:
        logger.error("[不合格] ポジション登録が失敗しました")
        return False


def main():
    """メインテスト処理"""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 80)
    logger.info("モニター起動テスト 開始")
    logger.info("=" * 80)
    logger.info("")

    # MT5初期化
    logger.info("MT5を初期化中...")
    if not initialize_mt5():
        logger.error("MT5初期化に失敗しました")
        return
    logger.info("")

    try:
        # テスト実行
        results = {}

        results['test1'] = test_orchestrator_startup()
        time.sleep(2)

        results['test2'] = test_individual_layers()
        time.sleep(2)

        results['test3'] = test_position_registration()

        # 総合結果
        logger.info("=" * 80)
        logger.info("テスト結果サマリー")
        logger.info("=" * 80)
        logger.info(f"TEST 1 (オーケストレーター起動): {'[合格]' if results['test1'] else '[不合格]'}")
        logger.info(f"TEST 2 (個別Layer起動): {'[合格]' if results['test2'] else '[不合格]'}")
        logger.info(f"TEST 3 (ポジション登録): {'[合格]' if results['test3'] else '[不合格]'}")
        logger.info("")

        if all(results.values()):
            logger.info("[総合結果] 全テスト合格 ✅")
        else:
            logger.error("[総合結果] 一部テスト不合格 ❌")

        logger.info("")

    finally:
        # MT5シャットダウン
        mt5.shutdown()
        logger.info("MT5をシャットダウンしました")
        logger.info("")


if __name__ == '__main__':
    main()
