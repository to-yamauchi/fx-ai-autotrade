"""
========================================
Layer 3: AI再評価モニター
========================================

ファイル名: layer3_ai_review.py
パス: src/monitoring/layer3_ai_review.py

【概要】
30分間隔でAI判断を再評価し、判断反転や信頼度低下を検知するモニター。
Layer 1/2よりも高度な分析を行い、トレンド変化を早期に捕捉します。

【監視条件】
1. 判断反転: BUY→SELL または SELL→BUY
2. 信頼度低下: 60%未満に低下
3. 自動決済: 判断反転時に自動決済を実行

【監視間隔】
30分（1800秒）

【処理】
- ポジション保持中に30分ごとにAI分析を再実行
- エントリー時の判断と比較して反転を検知
- 判断反転時は自動決済を実行
- 信頼度低下時はアラート送信

【作成日】2025-10-23
"""

import time
import threading
import logging
from typing import Dict, List, Optional
from datetime import datetime
import MetaTrader5 as mt5

from src.ai_analysis.ai_analyzer import AIAnalyzer


class Layer3AIReviewMonitor:
    """
    Layer 3 AI再評価モニタークラス

    30分間隔でポジションに対するAI判断を再評価し、
    判断反転や信頼度低下を検知します。
    """

    # 監視条件
    MIN_CONFIDENCE_PCT = 60.0  # 信頼度閾値（%）
    MONITOR_INTERVAL = 1800  # 監視間隔（秒）= 30分

    def __init__(self, symbol: str = 'USDJPY', ai_model: str = 'flash'):
        """
        Layer 3モニターの初期化

        Args:
            symbol: 監視対象の通貨ペア
            ai_model: 使用するAIモデル（flash/pro/flash-8b）
        """
        self.symbol = symbol
        self.ai_model = ai_model
        self.logger = logging.getLogger(__name__)

        # AIアナライザー
        self.analyzer = AIAnalyzer(symbol=symbol, model=ai_model)

        # モニタリング状態
        self.is_running = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

        # ポジションのエントリー判断を記録（判断反転検知用）
        self.position_entry_judgments: Dict[int, Dict] = {}

        # アラート履歴（重複送信を防ぐ）
        self.alert_history: Dict[str, datetime] = {}

        self.logger.info(
            f"Layer3AIReviewMonitor initialized: "
            f"model={ai_model}, "
            f"confidence_threshold={self.MIN_CONFIDENCE_PCT}%, "
            f"interval={self.MONITOR_INTERVAL}s"
        )

    def start(self):
        """
        監視を開始

        バックグラウンドスレッドで30分間隔の監視を開始します。
        """
        if self.is_running:
            self.logger.warning("Layer 3 monitor is already running")
            return

        self.logger.info("Starting Layer 3 AI Review Monitor...")
        self.is_running = True
        self.stop_event.clear()

        # 監視スレッドを開始
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="Layer3Monitor"
        )
        self.monitor_thread.start()

        self.logger.info(
            f"Layer 3 AI Review Monitor started "
            f"(interval: {self.MONITOR_INTERVAL}s)"
        )

    def stop(self):
        """
        監視を停止

        バックグラウンドスレッドを安全に停止します。
        """
        if not self.is_running:
            self.logger.warning("Layer 3 monitor is not running")
            return

        self.logger.info("Stopping Layer 3 AI Review Monitor...")
        self.is_running = False
        self.stop_event.set()

        # スレッドの終了を待つ
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)

        self.logger.info("Layer 3 AI Review Monitor stopped")

    def _monitor_loop(self):
        """
        監視ループ（バックグラウンドスレッド）

        30分間隔で全ポジションを監視し、AI判断を再評価します。
        """
        self.logger.info("Layer 3 monitor loop started")

        while self.is_running and not self.stop_event.is_set():
            try:
                # 全ポジションを取得
                positions = self._get_open_positions()

                if positions:
                    # 各ポジションをAI再評価
                    for position in positions:
                        self._review_position(position)

                # 次の監視まで待機（30分）
                self.stop_event.wait(timeout=self.MONITOR_INTERVAL)

            except Exception as e:
                self.logger.error(
                    f"Layer 3 monitor loop error: {e}",
                    exc_info=True
                )
                # エラーが発生してもループを継続
                self.stop_event.wait(timeout=self.MONITOR_INTERVAL)

        self.logger.info("Layer 3 monitor loop ended")

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
                'time': datetime.fromtimestamp(pos.time),
                'comment': pos.comment
            }
            for pos in positions
        ]

    def _review_position(self, position: Dict):
        """
        個別ポジションのAI再評価

        Args:
            position: ポジション情報
        """
        ticket = position['ticket']
        position_type = position['type']

        self.logger.info(
            f"Re-evaluating position {ticket} ({position_type})..."
        )

        try:
            # AI分析を再実行
            ai_result = self.analyzer.analyze_market()

            current_action = ai_result.get('action', 'HOLD')
            current_confidence = ai_result.get('confidence', 0)

            self.logger.info(
                f"Position {ticket}: "
                f"AI says {current_action} (confidence: {current_confidence}%)"
            )

            # エントリー時の判断と比較
            if ticket in self.position_entry_judgments:
                self._check_judgment_reversal(
                    position,
                    ai_result
                )

            # 信頼度チェック
            self._check_confidence_drop(
                position,
                ai_result
            )

        except Exception as e:
            self.logger.error(
                f"Failed to review position {ticket}: {e}",
                exc_info=True
            )

    def _check_judgment_reversal(self, position: Dict, ai_result: Dict):
        """
        判断反転チェック（BUY→SELL または SELL→BUY）

        Args:
            position: ポジション情報
            ai_result: 現在のAI分析結果
        """
        ticket = position['ticket']
        position_type = position['type']
        current_action = ai_result.get('action', 'HOLD')

        # エントリー時の判断を取得
        entry_judgment = self.position_entry_judgments.get(ticket, {})
        entry_action = entry_judgment.get('action', position_type)

        # 判断反転を検知
        is_reversal = False

        if position_type == 'BUY' and current_action == 'SELL':
            is_reversal = True
        elif position_type == 'SELL' and current_action == 'BUY':
            is_reversal = True

        if is_reversal:
            alert_key = f"reversal_{ticket}"

            # 重複アラートを防ぐ
            if not self._should_send_alert(alert_key, cooldown_minutes=60):
                return

            self.logger.warning(
                f"[LAYER 3 ALERT] Judgment reversal detected! "
                f"ticket={ticket}, "
                f"entry={entry_action}, "
                f"current={current_action}, "
                f"confidence={ai_result.get('confidence', 0)}%"
            )

            # アラート送信
            self._send_alert(
                alert_type='judgment_reversal',
                severity='DANGER',
                message=(
                    f"AI judgment reversed on position {ticket}: "
                    f"{entry_action} -> {current_action}. "
                    f"Auto-closing position."
                ),
                details={
                    'ticket': ticket,
                    'entry_action': entry_action,
                    'current_action': current_action,
                    'confidence': ai_result.get('confidence', 0),
                    'reasoning': ai_result.get('reasoning', '')
                }
            )

            # アラート履歴に記録
            self.alert_history[alert_key] = datetime.now()

            # 自動決済を実行
            self._auto_close_position(
                position,
                reason=f"AI judgment reversal: {entry_action} -> {current_action}"
            )

    def _check_confidence_drop(self, position: Dict, ai_result: Dict):
        """
        信頼度低下チェック（60%未満）

        Args:
            position: ポジション情報
            ai_result: 現在のAI分析結果
        """
        ticket = position['ticket']
        current_confidence = ai_result.get('confidence', 0)

        if current_confidence < self.MIN_CONFIDENCE_PCT:
            alert_key = f"confidence_{ticket}"

            # 重複アラートを防ぐ
            if not self._should_send_alert(alert_key, cooldown_minutes=60):
                return

            self.logger.warning(
                f"[LAYER 3 ALERT] Confidence drop detected! "
                f"ticket={ticket}, "
                f"confidence={current_confidence}% "
                f"(threshold: {self.MIN_CONFIDENCE_PCT}%)"
            )

            # アラート送信
            self._send_alert(
                alert_type='confidence_drop',
                severity='WARNING',
                message=(
                    f"AI confidence dropped to {current_confidence}% "
                    f"on position {ticket}. "
                    f"Consider manual review."
                ),
                details={
                    'ticket': ticket,
                    'confidence': current_confidence,
                    'threshold': self.MIN_CONFIDENCE_PCT,
                    'reasoning': ai_result.get('reasoning', '')
                }
            )

            # アラート履歴に記録
            self.alert_history[alert_key] = datetime.now()

    def _auto_close_position(self, position: Dict, reason: str):
        """
        ポジションを自動決済

        Args:
            position: ポジション情報
            reason: 決済理由
        """
        ticket = position['ticket']

        self.logger.warning(
            f"[AUTO CLOSE] Closing position {ticket}: {reason}"
        )

        try:
            # 決済リクエストを作成
            close_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": self.symbol,
                "volume": position['volume'],
                "type": mt5.ORDER_TYPE_SELL if position['type'] == 'BUY' else mt5.ORDER_TYPE_BUY,
                "position": ticket,
                "deviation": 20,
                "magic": 0,
                "comment": f"Layer3_AutoClose: {reason[:50]}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            # 決済実行
            result = mt5.order_send(close_request)

            if result is None:
                error = mt5.last_error()
                self.logger.error(
                    f"Failed to close position {ticket}: {error}"
                )
                return

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                self.logger.error(
                    f"Failed to close position {ticket}: "
                    f"retcode={result.retcode}, comment={result.comment}"
                )
                return

            self.logger.info(
                f"[SUCCESS] Position {ticket} closed successfully. "
                f"Profit: {position['profit']:.2f}"
            )

            # 追跡情報をクリア
            self.clear_position_tracking(ticket)

        except Exception as e:
            self.logger.error(
                f"Error closing position {ticket}: {e}",
                exc_info=True
            )

    def _should_send_alert(
        self,
        alert_key: str,
        cooldown_minutes: int = 60
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
            alert_type: アラートタイプ（judgment_reversal/confidence_drop）
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

    def register_position_entry(
        self,
        ticket: int,
        action: str,
        confidence: float,
        reasoning: str
    ):
        """
        ポジションのエントリー判断を登録

        Args:
            ticket: チケット番号
            action: エントリー時のアクション（BUY/SELL）
            confidence: エントリー時の信頼度
            reasoning: エントリー時の理由
        """
        self.position_entry_judgments[ticket] = {
            'action': action,
            'confidence': confidence,
            'reasoning': reasoning,
            'entry_time': datetime.now()
        }

        self.logger.info(
            f"Registered entry judgment for position {ticket}: "
            f"{action} (confidence: {confidence}%)"
        )

    def clear_position_tracking(self, ticket: int):
        """
        ポジションの追跡情報をクリア（ポジション決済時に呼び出す）

        Args:
            ticket: チケット番号
        """
        if ticket in self.position_entry_judgments:
            del self.position_entry_judgments[ticket]

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
            'min_confidence_pct': self.MIN_CONFIDENCE_PCT,
            'ai_model': self.ai_model,
            'tracked_positions': len(self.position_entry_judgments),
            'open_positions': len(positions),
            'alert_history_count': len(self.alert_history),
            'thread_alive': self.monitor_thread.is_alive() if self.monitor_thread else False
        }


# モジュールのエクスポート
__all__ = ['Layer3AIReviewMonitor']
