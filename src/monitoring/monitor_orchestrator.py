"""
========================================
モニターオーケストレーター
========================================

ファイル名: monitor_orchestrator.py
パス: src/monitoring/monitor_orchestrator.py

【概要】
3層モニタリングシステムを統合管理するオーケストレーター。
Layer 1/2/3を協調動作させ、ポジションの安全性を多層的に監視します。

【管理対象】
- Layer 1: 緊急停止モニター（100ms、50pips、口座2%損失）
- Layer 2: 異常検知モニター（5分、DD10%、逆行8pips、スプレッド5pips）
- Layer 3: AI再評価モニター（30分、判断反転、信頼度60%）

【主な機能】
1. 全モニターの一括起動・停止
2. ポジションエントリー時の登録
3. ポジション決済時のクリーンアップ
4. 統合ステータス報告
5. 緊急停止時の連携処理

【使用例】
```python
from src.monitoring.monitor_orchestrator import MonitorOrchestrator

# 初期化
orchestrator = MonitorOrchestrator(symbol='USDJPY')

# 全モニター起動
orchestrator.start_all()

# ポジションエントリー時
orchestrator.register_position_entry(
    ticket=12345,
    action='BUY',
    confidence=85.0,
    reasoning='Strong uptrend detected'
)

# 全モニター停止
orchestrator.stop_all()
```

【作成日】2025-10-23
"""

import logging
from typing import Dict, Optional
from datetime import datetime

from src.monitoring.layer1_emergency import Layer1EmergencyMonitor
from src.monitoring.layer2_anomaly import Layer2AnomalyMonitor
from src.monitoring.layer3_ai_review import Layer3AIReviewMonitor


class MonitorOrchestrator:
    """
    モニターオーケストレータークラス

    3層モニタリングシステムを統合管理し、協調動作を実現します。
    """

    def __init__(
        self,
        symbol: str = 'USDJPY',
        ai_model: str = 'flash',
        enable_layer1: bool = True,
        enable_layer2: bool = True,
        enable_layer3: bool = True
    ):
        """
        オーケストレーターの初期化

        Args:
            symbol: 監視対象の通貨ペア
            ai_model: Layer 3で使用するAIモデル
            enable_layer1: Layer 1を有効化
            enable_layer2: Layer 2を有効化
            enable_layer3: Layer 3を有効化
        """
        self.symbol = symbol
        self.ai_model = ai_model
        self.logger = logging.getLogger(__name__)

        # 各層の有効化フラグ
        self.enable_layer1 = enable_layer1
        self.enable_layer2 = enable_layer2
        self.enable_layer3 = enable_layer3

        # 各層のモニター初期化
        self.layer1: Optional[Layer1EmergencyMonitor] = None
        self.layer2: Optional[Layer2AnomalyMonitor] = None
        self.layer3: Optional[Layer3AIReviewMonitor] = None

        if self.enable_layer1:
            self.layer1 = Layer1EmergencyMonitor(symbol=symbol)

        if self.enable_layer2:
            self.layer2 = Layer2AnomalyMonitor(symbol=symbol)

        if self.enable_layer3:
            self.layer3 = Layer3AIReviewMonitor(
                symbol=symbol,
                ai_model=ai_model
            )

        # 起動時刻
        self.start_time: Optional[datetime] = None

        self.logger.info(
            f"MonitorOrchestrator initialized: "
            f"symbol={symbol}, "
            f"L1={enable_layer1}, L2={enable_layer2}, L3={enable_layer3}"
        )

    def start_all(self):
        """
        全モニターを起動

        Layer 1 → Layer 2 → Layer 3 の順に起動します。
        """
        self.logger.info("=" * 80)
        self.logger.info("Starting 3-Layer Monitoring System")
        self.logger.info("=" * 80)
        self.logger.info("")

        self.start_time = datetime.now()

        # Layer 1: 緊急停止モニター
        if self.enable_layer1 and self.layer1:
            self.logger.info("[Layer 1] Starting Emergency Monitor...")
            self.layer1.start()
            self.logger.info(
                f"  - Interval: {self.layer1.MONITOR_INTERVAL * 1000:.0f}ms"
            )
            self.logger.info(
                f"  - Hard SL: {self.layer1.HARD_STOP_LOSS_PIPS} pips"
            )
            self.logger.info(
                f"  - Max Loss: {self.layer1.MAX_ACCOUNT_LOSS_PCT}%"
            )
            self.logger.info("")

        # Layer 2: 異常検知モニター
        if self.enable_layer2 and self.layer2:
            self.logger.info("[Layer 2] Starting Anomaly Monitor...")
            self.layer2.start()
            self.logger.info(
                f"  - Interval: {self.layer2.MONITOR_INTERVAL // 60:.0f} min"
            )
            self.logger.info(
                f"  - Drawdown: {self.layer2.MAX_DRAWDOWN_PCT}%"
            )
            self.logger.info(
                f"  - Reversal: {self.layer2.REVERSAL_THRESHOLD_PIPS} pips"
            )
            self.logger.info(
                f"  - Spread: {self.layer2.MAX_SPREAD_PIPS} pips"
            )
            self.logger.info("")

        # Layer 3: AI再評価モニター
        if self.enable_layer3 and self.layer3:
            self.logger.info("[Layer 3] Starting AI Review Monitor...")
            self.layer3.start()
            self.logger.info(
                f"  - Interval: {self.layer3.MONITOR_INTERVAL // 60:.0f} min"
            )
            self.logger.info(
                f"  - Min Confidence: {self.layer3.MIN_CONFIDENCE_PCT}%"
            )
            self.logger.info(
                f"  - AI Model: {self.ai_model}"
            )
            self.logger.info("")

        self.logger.info("=" * 80)
        self.logger.info("All monitoring layers started successfully")
        self.logger.info("=" * 80)
        self.logger.info("")

    def stop_all(self):
        """
        全モニターを停止

        Layer 3 → Layer 2 → Layer 1 の順（逆順）に停止します。
        """
        self.logger.info("=" * 80)
        self.logger.info("Stopping 3-Layer Monitoring System")
        self.logger.info("=" * 80)
        self.logger.info("")

        # Layer 3から順に停止（逆順）
        if self.enable_layer3 and self.layer3:
            self.logger.info("[Layer 3] Stopping AI Review Monitor...")
            self.layer3.stop()
            self.logger.info("")

        if self.enable_layer2 and self.layer2:
            self.logger.info("[Layer 2] Stopping Anomaly Monitor...")
            self.layer2.stop()
            self.logger.info("")

        if self.enable_layer1 and self.layer1:
            self.logger.info("[Layer 1] Stopping Emergency Monitor...")
            self.layer1.stop()
            self.logger.info("")

        # 稼働時間を計算
        if self.start_time:
            uptime = datetime.now() - self.start_time
            hours, remainder = divmod(uptime.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            self.logger.info(f"Total uptime: {hours}h {minutes}m {seconds}s")
            self.logger.info("")

        self.logger.info("=" * 80)
        self.logger.info("All monitoring layers stopped successfully")
        self.logger.info("=" * 80)
        self.logger.info("")

    def register_position_entry(
        self,
        ticket: int,
        action: str,
        confidence: float,
        reasoning: str
    ):
        """
        ポジションエントリー時の登録

        全モニターにポジション情報を登録します。

        Args:
            ticket: チケット番号
            action: アクション（BUY/SELL）
            confidence: 信頼度
            reasoning: 判断理由
        """
        self.logger.info(
            f"Registering position {ticket} to all monitors: "
            f"{action} (confidence: {confidence}%)"
        )

        # Layer 1は登録不要（全ポジションを自動監視）

        # Layer 2は登録不要（全ポジションを自動監視）

        # Layer 3: エントリー判断を登録
        if self.enable_layer3 and self.layer3:
            self.layer3.register_position_entry(
                ticket=ticket,
                action=action,
                confidence=confidence,
                reasoning=reasoning
            )

        self.logger.info(f"Position {ticket} registered successfully")

    def clear_position_tracking(self, ticket: int):
        """
        ポジション決済時のクリーンアップ

        全モニターからポジション追跡情報を削除します。

        Args:
            ticket: チケット番号
        """
        self.logger.info(f"Clearing position {ticket} from all monitors")

        # Layer 1
        if self.enable_layer1 and self.layer1:
            self.layer1.clear_position_tracking(ticket)

        # Layer 2
        if self.enable_layer2 and self.layer2:
            self.layer2.clear_position_tracking(ticket)

        # Layer 3
        if self.enable_layer3 and self.layer3:
            self.layer3.clear_position_tracking(ticket)

        self.logger.info(f"Position {ticket} cleared successfully")

    def get_status(self) -> Dict:
        """
        全モニターの統合ステータスを取得

        Returns:
            Dict: 統合ステータス情報
        """
        status = {
            'orchestrator': {
                'symbol': self.symbol,
                'ai_model': self.ai_model,
                'start_time': self.start_time.isoformat() if self.start_time else None,
                'uptime_seconds': (
                    (datetime.now() - self.start_time).total_seconds()
                    if self.start_time else 0
                )
            },
            'layer1': None,
            'layer2': None,
            'layer3': None
        }

        # Layer 1ステータス
        if self.enable_layer1 and self.layer1:
            status['layer1'] = self.layer1.get_status()

        # Layer 2ステータス
        if self.enable_layer2 and self.layer2:
            status['layer2'] = self.layer2.get_status()

        # Layer 3ステータス
        if self.enable_layer3 and self.layer3:
            status['layer3'] = self.layer3.get_status()

        return status

    def print_status(self):
        """
        統合ステータスをログに出力
        """
        status = self.get_status()

        self.logger.info("=" * 80)
        self.logger.info("Monitoring System Status")
        self.logger.info("=" * 80)

        # オーケストレーター情報
        orch = status['orchestrator']
        if orch['start_time']:
            uptime_sec = orch['uptime_seconds']
            hours, remainder = divmod(int(uptime_sec), 3600)
            minutes, seconds = divmod(remainder, 60)

            self.logger.info(f"Symbol: {orch['symbol']}")
            self.logger.info(f"AI Model: {orch['ai_model']}")
            self.logger.info(f"Uptime: {hours}h {minutes}m {seconds}s")
            self.logger.info("")

        # Layer 1ステータス
        if status['layer1']:
            l1 = status['layer1']
            self.logger.info("[Layer 1] Emergency Monitor")
            self.logger.info(f"  Running: {l1['is_running']}")
            self.logger.info(f"  Thread Alive: {l1['thread_alive']}")
            self.logger.info(f"  Open Positions: {l1['open_positions']}")
            self.logger.info(f"  Alert History: {l1['alert_history_count']}")
            self.logger.info("")

        # Layer 2ステータス
        if status['layer2']:
            l2 = status['layer2']
            self.logger.info("[Layer 2] Anomaly Monitor")
            self.logger.info(f"  Running: {l2['is_running']}")
            self.logger.info(f"  Thread Alive: {l2['thread_alive']}")
            self.logger.info(f"  Tracked Positions: {l2['tracked_positions']}")
            self.logger.info(f"  Open Positions: {l2['open_positions']}")
            self.logger.info(f"  Alert History: {l2['alert_history_count']}")
            self.logger.info("")

        # Layer 3ステータス
        if status['layer3']:
            l3 = status['layer3']
            self.logger.info("[Layer 3] AI Review Monitor")
            self.logger.info(f"  Running: {l3['is_running']}")
            self.logger.info(f"  Thread Alive: {l3['thread_alive']}")
            self.logger.info(f"  Tracked Positions: {l3['tracked_positions']}")
            self.logger.info(f"  Open Positions: {l3['open_positions']}")
            self.logger.info(f"  Alert History: {l3['alert_history_count']}")
            self.logger.info("")

        self.logger.info("=" * 80)

    def is_running(self) -> bool:
        """
        いずれかのモニターが動作中か確認

        Returns:
            bool: True=動作中、False=停止中
        """
        running = False

        if self.enable_layer1 and self.layer1:
            running = running or self.layer1.is_running

        if self.enable_layer2 and self.layer2:
            running = running or self.layer2.is_running

        if self.enable_layer3 and self.layer3:
            running = running or self.layer3.is_running

        return running


# モジュールのエクスポート
__all__ = ['MonitorOrchestrator']
