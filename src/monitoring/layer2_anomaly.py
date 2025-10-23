"""
========================================
Layer 2: 異常検知モニター
========================================

ファイル名: layer2_anomaly.py
パス: src/monitoring/layer2_anomaly.py

【概要】
ポジションの異常状態を検知し、人間に警告を発するモニター。
Layer 1よりも早い段階で問題を検知し、手動介入の機会を提供。

【監視条件】
1. ドローダウン: 最大益から10%下落
2. 逆行: エントリーから8pips以上逆行
3. スプレッド異常: 5pips以上に拡大

【監視間隔】
5分（300秒）

【処理】
異常検知時にアラート通知を送信し、人間に判断を促す

【作成日】2025-10-23
"""

import time
import threading
import logging
from typing import Dict, List, Optional
from datetime import datetime
import MetaTrader5 as mt5


class Layer2AnomalyMonitor:
    """
    Layer 2 異常検知モニタークラス

    ドローダウン、逆行、スプレッド異常を5分間隔で監視し、
    異常検知時にアラートを送信します。
    """

    # 異常検知条件
    MAX_DRAWDOWN_PCT = 10.0  # ドローダウン閾値（%）
    REVERSAL_THRESHOLD_PIPS = 8.0  # 逆行閾値（pips）
    MAX_SPREAD_PIPS = 5.0  # スプレッド異常閾値（pips）
    MONITOR_INTERVAL = 300  # 監視間隔（秒）= 5分

    def __init__(self, symbol: str = 'USDJPY'):
        """
        Layer 2モニターの初期化

        Args:
            symbol: 監視対象の通貨ペア
        """
        self.symbol = symbol
        self.logger = logging.getLogger(__name__)

        # モニタリング状態
        self.is_running = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

        # ポジション最大益の記録（ドローダウン計算用）
        self.position_max_profits: Dict[int, float] = {}

        # アラート履歴（同じアラートの重複送信を防ぐ）
        self.alert_history: Dict[str, datetime] = {}

        self.logger.info(
            f"Layer2AnomalyMonitor initialized: "
            f"dd={self.MAX_DRAWDOWN_PCT}%, "
            f"reversal={self.REVERSAL_THRESHOLD_PIPS}pips, "
            f"spread={self.MAX_SPREAD_PIPS}pips, "
            f"interval={self.MONITOR_INTERVAL}s"
        )

    def start(self):
        """
        監視を開始

        バックグラウンドスレッドで5分間隔の監視を開始します。
        """
        if self.is_running:
            self.logger.warning("Layer 2 monitor is already running")
            return

        self.logger.info("Starting Layer 2 Anomaly Monitor...")
        self.is_running = True
        self.stop_event.clear()

        # 監視スレッドを開始
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="Layer2Monitor"
        )
        self.monitor_thread.start()

        self.logger.info(
            f"Layer 2 Anomaly Monitor started "
            f"(interval: {self.MONITOR_INTERVAL}s)"
        )

    def stop(self):
        """
        監視を停止

        バックグラウンドスレッドを安全に停止します。
        """
        if not self.is_running:
            self.logger.warning("Layer 2 monitor is not running")
            return

        self.logger.info("Stopping Layer 2 Anomaly Monitor...")
        self.is_running = False
        self.stop_event.set()

        # スレッドの終了を待つ
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)

        self.logger.info("Layer 2 Anomaly Monitor stopped")

    def _monitor_loop(self):
        """
        監視ループ（バックグラウンドスレッド）

        5分間隔で全ポジションを監視し、異常検知条件をチェックします。
        """
        self.logger.info("Layer 2 monitor loop started")

        while self.is_running and not self.stop_event.is_set():
            try:
                # 全ポジションを取得
                positions = self._get_open_positions()

                if positions:
                    # 各ポジションをチェック
                    for position in positions:
                        self._check_position(position)

                    # スプレッドをチェック
                    self._check_spread()

                # 次の監視まで待機（5分）
                self.stop_event.wait(timeout=self.MONITOR_INTERVAL)

            except Exception as e:
                self.logger.error(
                    f"Layer 2 monitor loop error: {e}",
                    exc_info=True
                )
                # エラーが発生してもループを継続
                self.stop_event.wait(timeout=self.MONITOR_INTERVAL)

        self.logger.info("Layer 2 monitor loop ended")

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
        個別ポジションの異常検知条件をチェック

        Args:
            position: ポジション情報
        """
        ticket = position['ticket']
        current_profit = position['profit']

        # 最大益を更新
        if ticket not in self.position_max_profits:
            self.position_max_profits[ticket] = current_profit
        else:
            if current_profit > self.position_max_profits[ticket]:
                self.position_max_profits[ticket] = current_profit

        # ドローダウンチェック
        self._check_drawdown(position)

        # 逆行チェック
        self._check_reversal(position)

    def _check_drawdown(self, position: Dict):
        """
        ドローダウンチェック（最大益から10%下落）

        Args:
            position: ポジション情報
        """
        ticket = position['ticket']
        current_profit = position['profit']
        max_profit = self.position_max_profits.get(ticket, 0)

        # 最大益がプラスの場合のみチェック
        if max_profit > 0:
            drawdown_pct = ((max_profit - current_profit) / max_profit) * 100

            if drawdown_pct >= self.MAX_DRAWDOWN_PCT:
                alert_key = f"dd_{ticket}"

                # 重複アラートを防ぐ（10分以内に同じアラートを送信しない）
                if not self._should_send_alert(alert_key, cooldown_minutes=10):
                    return

                self.logger.warning(
                    f"[LAYER 2 ALERT] Drawdown detected! "
                    f"ticket={ticket}, "
                    f"drawdown={drawdown_pct:.2f}% "
                    f"(max_profit={max_profit:.2f}, "
                    f"current_profit={current_profit:.2f})"
                )

                # アラート送信
                self._send_alert(
                    alert_type='drawdown',
                    severity='WARNING',
                    message=(
                        f"Drawdown {drawdown_pct:.1f}% detected on position {ticket}. "
                        f"Consider manual intervention."
                    ),
                    details={
                        'ticket': ticket,
                        'drawdown_pct': drawdown_pct,
                        'max_profit': max_profit,
                        'current_profit': current_profit
                    }
                )

                # アラート履歴に記録
                self.alert_history[alert_key] = datetime.now()

    def _check_reversal(self, position: Dict):
        """
        逆行チェック（エントリーから8pips以上逆行）

        Args:
            position: ポジション情報
        """
        ticket = position['ticket']
        position_type = position['type']
        entry_price = position['price_open']
        current_price = position['price_current']

        # 逆行pipsを計算
        if position_type == 'BUY':
            pips_move = (current_price - entry_price) * 100
        else:
            pips_move = (entry_price - current_price) * 100

        # 逆行閾値チェック（マイナス方向）
        if pips_move <= -self.REVERSAL_THRESHOLD_PIPS:
            alert_key = f"rev_{ticket}"

            # 重複アラートを防ぐ
            if not self._should_send_alert(alert_key, cooldown_minutes=10):
                return

            self.logger.warning(
                f"[LAYER 2 ALERT] Reversal detected! "
                f"ticket={ticket}, "
                f"type={position_type}, "
                f"move={pips_move:.2f}pips"
            )

            # アラート送信
            self._send_alert(
                alert_type='reversal',
                severity='WARNING',
                message=(
                    f"Position {ticket} moved {pips_move:.1f}pips against entry. "
                    f"Consider manual intervention."
                ),
                details={
                    'ticket': ticket,
                    'type': position_type,
                    'entry_price': entry_price,
                    'current_price': current_price,
                    'pips_move': pips_move
                }
            )

            # アラート履歴に記録
            self.alert_history[alert_key] = datetime.now()

    def _check_spread(self):
        """
        スプレッド異常チェック（5pips以上）
        """
        tick = mt5.symbol_info_tick(self.symbol)

        if tick is None:
            self.logger.error("Failed to get tick info")
            return

        # スプレッドをpipsで計算（5桁）
        spread_pips = (tick.ask - tick.bid) * 100

        if spread_pips >= self.MAX_SPREAD_PIPS:
            alert_key = "spread_wide"

            # 重複アラートを防ぐ
            if not self._should_send_alert(alert_key, cooldown_minutes=15):
                return

            self.logger.warning(
                f"[LAYER 2 ALERT] Spread abnormally wide! "
                f"spread={spread_pips:.2f}pips "
                f"(threshold: {self.MAX_SPREAD_PIPS}pips)"
            )

            # アラート送信
            self._send_alert(
                alert_type='spread_wide',
                severity='WARNING',
                message=(
                    f"Spread widened to {spread_pips:.1f}pips. "
                    f"Trading conditions may be unfavorable."
                ),
                details={
                    'spread_pips': spread_pips,
                    'bid': tick.bid,
                    'ask': tick.ask
                }
            )

            # アラート履歴に記録
            self.alert_history[alert_key] = datetime.now()

    def _should_send_alert(
        self,
        alert_key: str,
        cooldown_minutes: int = 10
    ) -> bool:
        """
        アラートを送信すべきか判定（重複送信を防ぐ）

        Args:
            alert_key: アラートキー
            cooldown_minutes: クールダウン時間（分）

        Returns:
            bool: True=送信すべき、False=送信不要
        """
        if alert_key not in self.alert_history:
            return True

        last_sent = self.alert_history[alert_key]
        elapsed = (datetime.now() - last_sent).total_seconds() / 60

        return elapsed >= cooldown_minutes

    def _send_alert(
        self,
        alert_type: str,
        severity: str,
        message: str,
        details: Dict
    ):
        """
        アラートを送信

        Args:
            alert_type: アラートタイプ（drawdown/reversal/spread_wide）
            severity: 重要度（INFO/WARNING/DANGER）
            message: アラートメッセージ
            details: 詳細情報
        """
        # ログに記録
        self.logger.warning(
            f"[ALERT] type={alert_type}, severity={severity}, "
            f"message={message}"
        )

        # TODO: メール/SMS通知の実装
        # - SMTPでメール送信
        # - Twilio APIでSMS送信
        # - Slack/Discord Webhookで通知

        # 現在はログのみ
        self.logger.info(f"Alert details: {details}")

    def clear_position_tracking(self, ticket: int):
        """
        ポジションの追跡情報をクリア（ポジション決済時に呼び出す）

        Args:
            ticket: チケット番号
        """
        if ticket in self.position_max_profits:
            del self.position_max_profits[ticket]

        # アラート履歴もクリア
        keys_to_remove = [
            key for key in self.alert_history
            if str(ticket) in key
        ]
        for key in keys_to_remove:
            del self.alert_history[key]

        self.logger.info(f"Cleared tracking for position {ticket}")

    def get_status(self) -> Dict:
        """
        モニターの現在の状態を取得

        Returns:
            Dict: ステータス情報
        """
        positions = self._get_open_positions()

        return {
            'is_running': self.is_running,
            'monitor_interval_sec': self.MONITOR_INTERVAL,
            'max_drawdown_pct': self.MAX_DRAWDOWN_PCT,
            'reversal_threshold_pips': self.REVERSAL_THRESHOLD_PIPS,
            'max_spread_pips': self.MAX_SPREAD_PIPS,
            'tracked_positions': len(self.position_max_profits),
            'open_positions': len(positions),
            'alert_history_count': len(self.alert_history),
            'thread_alive': self.monitor_thread.is_alive() if self.monitor_thread else False
        }


# モジュールのエクスポート
__all__ = ['Layer2AnomalyMonitor']
