"""
========================================
Layer 1: 緊急停止モニター
========================================

ファイル名: layer1_emergency.py
パス: src/monitoring/layer1_emergency.py

【概要】
最優先の安全装置として、重大な損失を即座に防ぐ緊急停止モニター。
ハードストップロスと口座損失閾値を監視し、条件に達したら問答無用で決済。

【監視条件】
1. ハードストップロス: エントリーから50pips逆行
2. 口座損失: 口座残高の2%損失

【監視間隔】
100ms（0.1秒）- 超高頻度監視

【処理】
条件に達した場合、即座に強制決済を実行

【作成日】2025-10-23
"""

import time
import threading
import logging
from typing import Dict, List, Optional
from datetime import datetime
import MetaTrader5 as mt5

from src.trade_execution.mt5_executor import MT5Executor


class Layer1EmergencyMonitor:
    """
    Layer 1 緊急停止モニタークラス

    ハードストップロスと口座損失閾値を100ms間隔で監視し、
    条件に達したら即座に強制決済を実行します。
    """

    # 緊急停止条件
    HARD_STOP_LOSS_PIPS = 50  # ハードストップロス（pips）
    MAX_ACCOUNT_LOSS_PCT = 2.0  # 口座損失閾値（%）
    MONITOR_INTERVAL = 0.1  # 監視間隔（秒）= 100ms

    def __init__(self, symbol: str = 'USDJPY'):
        """
        Layer 1モニターの初期化

        Args:
            symbol: 監視対象の通貨ペア
        """
        self.symbol = symbol
        self.logger = logging.getLogger(__name__)
        self.mt5_executor = MT5Executor()

        # モニタリング状態
        self.is_running = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

        # 初期口座残高を記録
        self.initial_balance = self._get_account_balance()

        # アラート履歴（重複送信を防ぐ）
        self.alert_history: Dict[str, datetime] = {}

        self.logger.info(
            f"Layer1EmergencyMonitor initialized: "
            f"hard_sl={self.HARD_STOP_LOSS_PIPS}pips, "
            f"max_loss={self.MAX_ACCOUNT_LOSS_PCT}%, "
            f"interval={self.MONITOR_INTERVAL * 1000}ms"
        )

    def start(self):
        """
        監視を開始

        バックグラウンドスレッドで100ms間隔の監視を開始します。
        """
        if self.is_running:
            self.logger.warning("Layer 1 monitor is already running")
            return

        self.logger.info("Starting Layer 1 Emergency Monitor...")
        self.is_running = True
        self.stop_event.clear()

        # 監視スレッドを開始
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="Layer1Monitor"
        )
        self.monitor_thread.start()

        self.logger.info(
            f"Layer 1 Emergency Monitor started "
            f"(interval: {self.MONITOR_INTERVAL * 1000}ms)"
        )

    def stop(self):
        """
        監視を停止

        バックグラウンドスレッドを安全に停止します。
        """
        if not self.is_running:
            self.logger.warning("Layer 1 monitor is not running")
            return

        self.logger.info("Stopping Layer 1 Emergency Monitor...")
        self.is_running = False
        self.stop_event.set()

        # スレッドの終了を待つ
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)

        self.logger.info("Layer 1 Emergency Monitor stopped")

    def _monitor_loop(self):
        """
        監視ループ（バックグラウンドスレッド）

        100ms間隔で全ポジションを監視し、緊急停止条件をチェックします。
        """
        self.logger.info("Layer 1 monitor loop started")

        while self.is_running and not self.stop_event.is_set():
            try:
                # 全ポジションを取得
                positions = self._get_open_positions()

                if positions:
                    # 各ポジションをチェック
                    for position in positions:
                        self._check_position(position)

                    # 口座全体の損失をチェック
                    self._check_account_loss()

                # 次の監視まで待機
                time.sleep(self.MONITOR_INTERVAL)

            except Exception as e:
                self.logger.error(
                    f"Layer 1 monitor loop error: {e}",
                    exc_info=True
                )
                # エラーが発生してもループを継続
                time.sleep(self.MONITOR_INTERVAL)

        self.logger.info("Layer 1 monitor loop ended")

    def _get_open_positions(self) -> List[Dict]:
        """
        オープン中のポジションを取得

        Returns:
            List[Dict]: ポジション情報のリスト
        """
        positions = mt5.positions_get(symbol=self.symbol)

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
                'sl': pos.sl,
                'tp': pos.tp,
                'time': datetime.fromtimestamp(pos.time)
            }
            for pos in positions
        ]

    def _check_position(self, position: Dict):
        """
        個別ポジションの緊急停止条件をチェック

        Args:
            position: ポジション情報
        """
        ticket = position['ticket']
        position_type = position['type']
        entry_price = position['price_open']
        current_price = position['price_current']
        profit = position['profit']

        # 逆行pipsを計算
        if position_type == 'BUY':
            # 買いポジション: 現在価格がエントリーより低い場合に逆行
            pips_move = (current_price - entry_price) * 100
        else:
            # 売りポジション: 現在価格がエントリーより高い場合に逆行
            pips_move = (entry_price - current_price) * 100

        # ハードストップロスチェック（50pips逆行）
        if pips_move <= -self.HARD_STOP_LOSS_PIPS:
            self.logger.critical(
                f"[LAYER 1 EMERGENCY] Hard stop loss triggered! "
                f"ticket={ticket}, type={position_type}, "
                f"move={pips_move:.2f}pips (threshold: -{self.HARD_STOP_LOSS_PIPS}pips)"
            )
            self._emergency_close_position(
                position,
                reason=f"Hard SL: {pips_move:.2f}pips"
            )

    def _check_account_loss(self):
        """
        口座全体の損失をチェック

        初期残高から2%以上損失している場合、全ポジションを強制決済。
        """
        current_balance = self._get_account_balance()

        if current_balance is None or self.initial_balance is None:
            return

        # 損失率を計算
        loss_amount = self.initial_balance - current_balance
        loss_pct = (loss_amount / self.initial_balance) * 100

        # 2%以上の損失で緊急停止
        if loss_pct >= self.MAX_ACCOUNT_LOSS_PCT:
            self.logger.critical(
                f"[LAYER 1 EMERGENCY] Account loss threshold exceeded! "
                f"loss={loss_pct:.2f}% (threshold: {self.MAX_ACCOUNT_LOSS_PCT}%), "
                f"amount={loss_amount:,.0f}"
            )
            self._emergency_close_all_positions(
                reason=f"Account loss: {loss_pct:.2f}%"
            )

    def _emergency_close_position(self, position: Dict, reason: str):
        """
        緊急決済: 個別ポジションを即座に決済

        Args:
            position: ポジション情報
            reason: 決済理由
        """
        ticket = position['ticket']

        try:
            self.logger.critical(
                f"[EMERGENCY CLOSE] Closing position {ticket}: {reason}"
            )

            # MT5Executorで決済
            success = self.mt5_executor.close_position(ticket)

            if success:
                self.logger.critical(
                    f"[EMERGENCY CLOSE] Position {ticket} closed successfully"
                )

                # 緊急停止ログをDBに記録（オプション）
                self._log_emergency_action(
                    action_type='position_close',
                    ticket=ticket,
                    reason=reason,
                    position=position
                )
            else:
                self.logger.error(
                    f"[EMERGENCY CLOSE] Failed to close position {ticket}"
                )

        except Exception as e:
            self.logger.error(
                f"[EMERGENCY CLOSE] Error closing position {ticket}: {e}",
                exc_info=True
            )

    def _emergency_close_all_positions(self, reason: str):
        """
        緊急決済: 全ポジションを即座に決済

        Args:
            reason: 決済理由
        """
        positions = self._get_open_positions()

        if not positions:
            self.logger.warning("No positions to close")
            return

        self.logger.critical(
            f"[EMERGENCY CLOSE ALL] Closing {len(positions)} positions: {reason}"
        )

        for position in positions:
            self._emergency_close_position(position, reason)

    def _get_account_balance(self) -> Optional[float]:
        """
        現在の口座残高を取得

        Returns:
            float: 口座残高
            None: 取得失敗
        """
        account_info = mt5.account_info()

        if account_info is None:
            self.logger.error("Failed to get account info")
            return None

        return account_info.balance

    def _log_emergency_action(
        self,
        action_type: str,
        ticket: int,
        reason: str,
        position: Dict
    ):
        """
        緊急停止アクションをログに記録

        Args:
            action_type: アクションタイプ（position_close/all_close）
            ticket: チケット番号
            reason: 決済理由
            position: ポジション情報
        """
        # データベースに記録する場合はここに実装
        # 現在はログファイルのみ
        self.logger.critical(
            f"[EMERGENCY LOG] "
            f"action={action_type}, "
            f"ticket={ticket}, "
            f"reason={reason}, "
            f"type={position.get('type')}, "
            f"profit={position.get('profit', 0):.2f}"
        )

    def get_status(self) -> Dict:
        """
        モニターの現在の状態を取得

        Returns:
            Dict: ステータス情報
        """
        positions = self._get_open_positions()
        current_balance = self._get_account_balance()

        return {
            'is_running': self.is_running,
            'monitor_interval_ms': self.MONITOR_INTERVAL * 1000,
            'hard_stop_loss_pips': self.HARD_STOP_LOSS_PIPS,
            'max_account_loss_pct': self.MAX_ACCOUNT_LOSS_PCT,
            'initial_balance': self.initial_balance,
            'current_balance': current_balance,
            'open_positions': len(positions),
            'alert_history_count': len(self.alert_history),
            'thread_alive': self.monitor_thread.is_alive() if self.monitor_thread else False
        }

    def clear_position_tracking(self, ticket: int):
        """
        ポジションの追跡情報をクリア（ポジション決済時に呼び出す）

        Args:
            ticket: チケット番号
        """
        # アラート履歴をクリア
        keys_to_remove = [
            key for key in self.alert_history
            if str(ticket) in key
        ]
        for key in keys_to_remove:
            del self.alert_history[key]

        self.logger.info(f"Cleared tracking for position {ticket}")


# モジュールのエクスポート
__all__ = ['Layer1EmergencyMonitor']
