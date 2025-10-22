"""
========================================
トレードルールエンジンモジュール
========================================

ファイル名: trading_rules.py
パス: src/rule_engine/trading_rules.py

【概要】
AI判断に基づいてトレード実行の可否を判定するルールエンジンです。
リスク管理のための各種チェックを実施し、安全なトレード実行を保証します。

【主な機能】
1. AI信頼度チェック
2. スプレッドチェック
3. ポジション数制限
4. トレーディング時間チェック
5. ボラティリティチェック

【ルール一覧】
- 最小信頼度: 60%以上
- 最大スプレッド: 3.0 pips以内
- 最大同時ポジション数: 3つまで
- トレード禁止時間: 金曜22:00以降、週末
- 最大ボラティリティ: 通常時の3倍まで

【使用例】
```python
from src.rule_engine import TradingRules

rules = TradingRules()
ai_judgment = {'action': 'BUY', 'confidence': 75}

if rules.validate_trade(ai_judgment, current_positions=2, spread=2.0):
    # トレード実行
    pass
```

【作成日】2025-10-22
"""

from typing import Dict, Optional
from datetime import datetime, time
import logging


class TradingRules:
    """
    トレードルールを管理するクラス

    AI判断に対して複数のルールを適用し、トレード実行の可否を判定します。
    リスク管理とポジション管理を統合的に行います。
    """

    # ルール設定（定数）
    MIN_CONFIDENCE = 60  # 最小信頼度（%）
    MAX_SPREAD = 3.0     # 最大スプレッド（pips）
    MAX_POSITIONS = 3    # 最大同時ポジション数
    MAX_VOLATILITY_MULTIPLIER = 3.0  # 最大ボラティリティ倍率

    # トレード禁止時間
    TRADING_FORBIDDEN_START = time(22, 0)  # 金曜22:00以降
    TRADING_FORBIDDEN_DAY = 4  # 金曜日 (0=月曜)

    def __init__(self,
                 min_confidence: Optional[float] = None,
                 max_spread: Optional[float] = None,
                 max_positions: Optional[int] = None):
        """
        TradingRulesの初期化

        Args:
            min_confidence: 最小信頼度（カスタム設定）
            max_spread: 最大スプレッド（カスタム設定）
            max_positions: 最大ポジション数（カスタム設定）
        """
        self.logger = logging.getLogger(__name__)

        # カスタム設定があれば上書き
        self.min_confidence = min_confidence or self.MIN_CONFIDENCE
        self.max_spread = max_spread or self.MAX_SPREAD
        self.max_positions = max_positions or self.MAX_POSITIONS

        self.logger.info(
            f"TradingRules initialized: "
            f"min_confidence={self.min_confidence}%, "
            f"max_spread={self.max_spread}pips, "
            f"max_positions={self.max_positions}"
        )

    def validate_trade(self,
                      ai_judgment: Dict,
                      current_positions: int,
                      spread: float,
                      current_volatility: Optional[float] = None,
                      avg_volatility: Optional[float] = None) -> tuple[bool, str]:
        """
        トレード実行可否を総合判定

        Args:
            ai_judgment: AI判断結果
                {
                    'action': 'BUY' | 'SELL' | 'HOLD',
                    'confidence': 0-100,
                    'reasoning': '判断理由'
                }
            current_positions: 現在のポジション数
            spread: 現在のスプレッド（pips）
            current_volatility: 現在のボラティリティ（ATR等）
            avg_volatility: 平均ボラティリティ

        Returns:
            tuple[bool, str]: (実行可否, 理由)
                True: 実行可能
                False: 実行不可
        """
        # 1. アクションチェック
        action = ai_judgment.get('action', 'HOLD')
        if action == 'HOLD':
            return False, "AI判断がHOLDのため実行不可"

        if action not in ['BUY', 'SELL']:
            return False, f"無効なアクション: {action}"

        # 2. 信頼度チェック
        confidence = ai_judgment.get('confidence', 0)
        if confidence < self.min_confidence:
            return False, f"信頼度不足: {confidence}% < {self.min_confidence}%"

        # 3. スプレッドチェック
        if spread > self.max_spread:
            return False, f"スプレッド超過: {spread}pips > {self.max_spread}pips"

        # 4. ポジション数チェック
        if current_positions >= self.max_positions:
            return False, f"ポジション数上限: {current_positions} >= {self.max_positions}"

        # 5. トレーディング時間チェック
        if not self._check_trading_hours():
            return False, "トレード禁止時間帯"

        # 6. ボラティリティチェック
        if current_volatility is not None and avg_volatility is not None:
            if not self._check_volatility(current_volatility, avg_volatility):
                return False, "ボラティリティ異常（市場が不安定）"

        # 全てのチェックをパス
        self.logger.info(
            f"Trade validation passed: {action} "
            f"(confidence={confidence}%, spread={spread}pips)"
        )
        return True, "全てのルールチェックをパス"

    def _check_trading_hours(self) -> bool:
        """
        トレーディング時間チェック

        金曜22:00以降および週末はトレード禁止

        Returns:
            True: トレード可能時間
            False: トレード禁止時間
        """
        now = datetime.now()
        current_day = now.weekday()  # 0=月曜, 6=日曜
        current_time = now.time()

        # 土日はトレード禁止
        if current_day in [5, 6]:  # 土曜、日曜
            self.logger.warning("Weekend trading is forbidden")
            return False

        # 金曜22:00以降はトレード禁止
        if current_day == self.TRADING_FORBIDDEN_DAY:
            if current_time >= self.TRADING_FORBIDDEN_START:
                self.logger.warning("Friday late trading is forbidden")
                return False

        return True

    def _check_volatility(self,
                         current_volatility: float,
                         avg_volatility: float) -> bool:
        """
        ボラティリティチェック

        現在のボラティリティが平均の一定倍率を超えていないか確認

        Args:
            current_volatility: 現在のボラティリティ
            avg_volatility: 平均ボラティリティ

        Returns:
            True: 正常範囲内
            False: 異常値
        """
        if avg_volatility == 0:
            return True  # ゼロ除算回避

        volatility_ratio = current_volatility / avg_volatility

        if volatility_ratio > self.MAX_VOLATILITY_MULTIPLIER:
            self.logger.warning(
                f"Volatility too high: {volatility_ratio:.2f}x "
                f"> {self.MAX_VOLATILITY_MULTIPLIER}x"
            )
            return False

        return True

    def calculate_position_size(self,
                               account_balance: float,
                               risk_percent: float,
                               stop_loss_pips: float,
                               pip_value: float = 1000.0) -> float:
        """
        ポジションサイズを計算（リスク管理）

        Args:
            account_balance: 口座残高
            risk_percent: リスク許容率（例: 1.0 = 1%）
            stop_loss_pips: ストップロスのpips数
            pip_value: 1pipの価値（USDJPY 0.01ロットの場合: 1000円）

        Returns:
            推奨ロットサイズ
        """
        # リスク金額 = 口座残高 × リスク率
        risk_amount = account_balance * (risk_percent / 100)

        # ポジションサイズ = リスク金額 / (SLpips × pip価値)
        if stop_loss_pips == 0:
            return 0.01  # 最小ロット

        position_size = risk_amount / (stop_loss_pips * pip_value)

        # 最小ロット: 0.01, 最大ロット: 10.0
        position_size = max(0.01, min(position_size, 10.0))

        # 0.01刻みに丸める
        position_size = round(position_size / 0.01) * 0.01

        self.logger.info(
            f"Position size calculated: {position_size:.2f} lots "
            f"(risk={risk_percent}%, SL={stop_loss_pips}pips)"
        )

        return position_size

    def get_validation_summary(self, ai_judgment: Dict) -> Dict:
        """
        バリデーション結果のサマリーを取得

        Args:
            ai_judgment: AI判断結果

        Returns:
            バリデーションサマリー
        """
        action = ai_judgment.get('action', 'HOLD')
        confidence = ai_judgment.get('confidence', 0)

        return {
            'action': action,
            'confidence': confidence,
            'rules': {
                'min_confidence': self.min_confidence,
                'max_spread': self.max_spread,
                'max_positions': self.max_positions
            },
            'checks': {
                'confidence_pass': confidence >= self.min_confidence,
                'action_valid': action in ['BUY', 'SELL'],
                'trading_hours_ok': self._check_trading_hours()
            }
        }


# モジュールのエクスポート
__all__ = ['TradingRules']
