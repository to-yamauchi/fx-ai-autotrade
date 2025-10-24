"""
========================================
構造化ルールエンジン
========================================

ファイル名: structured_rule_engine.py
パス: src/rule_engine/structured_rule_engine.py

【概要】
構造化されたトレードルールを解釈して、エントリー・決済判断を行うエンジン。
自然言語ではなく、プログラムが直接解釈できる構造化データを処理します。

【主な機能】
1. エントリー条件の検証（価格ゾーン、インジケーター、時間フィルター）
2. 決済条件の検証（TP、SL、インジケーター決済、時間制約）
3. リスク管理パラメータの適用

【使用例】
```python
from src.rule_engine import StructuredRuleEngine

engine = StructuredRuleEngine()
rule = load_latest_rule_from_db()
market_data = get_current_market_data()

if engine.check_entry_conditions(market_data, rule):
    execute_trade()
```

【作成日】2025-01-15
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, time
import logging


class StructuredRuleEngine:
    """
    構造化トレードルールを解釈するエンジン

    自然言語を含まない、完全に構造化されたルールを処理します。
    """

    def __init__(self):
        """StructuredRuleEngineの初期化"""
        self.logger = logging.getLogger(__name__)
        self.logger.info("StructuredRuleEngine initialized")

    def check_entry_conditions(
        self,
        market_data: Dict,
        rule: Dict
    ) -> Tuple[bool, str]:
        """
        エントリー条件をチェック

        Args:
            market_data: 市場データ
                {
                    'current_price': 149.55,
                    'spread': 2.5,
                    'current_time': '14:30',
                    'M15': {'rsi': 55, 'ema_20': 149.40, 'macd_histogram': 0.05},
                    'H1': {...},
                    'H4': {...},
                    'D1': {...}
                }
            rule: 構造化トレードルール
                {
                    'entry_conditions': {...},
                    'risk_management': {...},
                    ...
                }

        Returns:
            Tuple[bool, str]: (可否, 理由)
        """
        entry_cond = rule.get('entry_conditions', {})

        # 1. should_tradeチェック
        if not entry_cond.get('should_trade', False):
            return False, "should_trade is False"

        # 2. 価格ゾーンチェック
        current_price = market_data.get('current_price')
        if current_price is None:
            return False, "current_price not available"

        price_zone = entry_cond.get('price_zone', {})
        min_price = price_zone.get('min')
        max_price = price_zone.get('max')

        if min_price and max_price:
            if not (min_price <= current_price <= max_price):
                return False, f"Price {current_price} outside zone [{min_price}, {max_price}]"

        # 3. スプレッドチェック
        spread = market_data.get('spread')
        if spread is not None:
            max_spread = entry_cond.get('spread', {}).get('max_pips')
            if max_spread and spread > max_spread:
                return False, f"Spread {spread} > max {max_spread}"

        # 4. インジケーターチェック
        indicators = entry_cond.get('indicators', {})

        # RSIチェック
        if 'rsi' in indicators:
            ok, msg = self._check_rsi(market_data, indicators['rsi'])
            if not ok:
                return False, msg

        # EMAチェック
        if 'ema' in indicators:
            ok, msg = self._check_ema(market_data, indicators['ema'], current_price)
            if not ok:
                return False, msg

        # MACDチェック
        if 'macd' in indicators:
            ok, msg = self._check_macd(market_data, indicators['macd'])
            if not ok:
                return False, msg

        # 5. 時間フィルターチェック
        current_time = market_data.get('current_time')
        if current_time:
            time_filter = entry_cond.get('time_filter', {})
            avoid_times = time_filter.get('avoid_times', [])

            for avoid in avoid_times:
                if self._is_time_in_range(current_time, avoid['start'], avoid['end']):
                    return False, f"Time filter: {avoid.get('reason', 'Avoid time')}"

        # すべてクリア
        self.logger.info("All entry conditions passed")
        return True, "All entry conditions met"

    def _check_rsi(
        self,
        market_data: Dict,
        rsi_rule: Dict
    ) -> Tuple[bool, str]:
        """RSI条件をチェック"""
        timeframe = rsi_rule.get('timeframe', 'M15')
        min_val = rsi_rule.get('min')
        max_val = rsi_rule.get('max')

        tf_data = market_data.get(timeframe, {})
        current_rsi = tf_data.get('rsi')

        if current_rsi is None:
            return False, f"RSI not available for {timeframe}"

        if min_val is not None and current_rsi < min_val:
            return False, f"RSI {current_rsi} < min {min_val} ({timeframe})"

        if max_val is not None and current_rsi > max_val:
            return False, f"RSI {current_rsi} > max {max_val} ({timeframe})"

        return True, "RSI OK"

    def _check_ema(
        self,
        market_data: Dict,
        ema_rule: Dict,
        current_price: float
    ) -> Tuple[bool, str]:
        """EMA条件をチェック"""
        timeframe = ema_rule.get('timeframe', 'M15')
        condition = ema_rule.get('condition')
        period = ema_rule.get('period')

        tf_data = market_data.get(timeframe, {})
        ema_key = f'ema_{period}'
        ema_value = tf_data.get(ema_key)

        if ema_value is None:
            return False, f"EMA{period} not available for {timeframe}"

        if condition == 'price_above':
            if current_price <= ema_value:
                return False, f"Price {current_price} not above EMA{period} {ema_value} ({timeframe})"
        elif condition == 'price_below':
            if current_price >= ema_value:
                return False, f"Price {current_price} not below EMA{period} {ema_value} ({timeframe})"
        elif condition == 'cross_above':
            # 前回の足で下、今回の足で上
            prev_price = tf_data.get('prev_close')
            if prev_price is None or not (prev_price <= ema_value < current_price):
                return False, f"Price did not cross above EMA{period} ({timeframe})"
        elif condition == 'cross_below':
            # 前回の足で上、今回の足で下
            prev_price = tf_data.get('prev_close')
            if prev_price is None or not (prev_price >= ema_value > current_price):
                return False, f"Price did not cross below EMA{period} ({timeframe})"

        return True, "EMA OK"

    def _check_macd(
        self,
        market_data: Dict,
        macd_rule: Dict
    ) -> Tuple[bool, str]:
        """MACD条件をチェック"""
        timeframe = macd_rule.get('timeframe', 'M15')
        condition = macd_rule.get('condition')

        tf_data = market_data.get(timeframe, {})

        if condition == 'histogram_positive':
            histogram = tf_data.get('macd_histogram')
            if histogram is None or histogram <= 0:
                return False, f"MACD histogram not positive ({timeframe})"
        elif condition == 'histogram_negative':
            histogram = tf_data.get('macd_histogram')
            if histogram is None or histogram >= 0:
                return False, f"MACD histogram not negative ({timeframe})"
        elif condition == 'signal_cross_above':
            macd_line = tf_data.get('macd_line')
            signal_line = tf_data.get('macd_signal')
            prev_macd = tf_data.get('prev_macd_line')
            prev_signal = tf_data.get('prev_macd_signal')

            if None in [macd_line, signal_line, prev_macd, prev_signal]:
                return False, f"MACD data incomplete ({timeframe})"

            if not (prev_macd <= prev_signal and macd_line > signal_line):
                return False, f"MACD did not cross above signal ({timeframe})"
        elif condition == 'signal_cross_below':
            macd_line = tf_data.get('macd_line')
            signal_line = tf_data.get('macd_signal')
            prev_macd = tf_data.get('prev_macd_line')
            prev_signal = tf_data.get('prev_macd_signal')

            if None in [macd_line, signal_line, prev_macd, prev_signal]:
                return False, f"MACD data incomplete ({timeframe})"

            if not (prev_macd >= prev_signal and macd_line < signal_line):
                return False, f"MACD did not cross below signal ({timeframe})"

        return True, "MACD OK"

    def _is_time_in_range(
        self,
        current_time: str,
        start_time: str,
        end_time: str
    ) -> bool:
        """現在時刻が指定範囲内かチェック"""
        try:
            current = datetime.strptime(current_time, "%H:%M").time()
            start = datetime.strptime(start_time, "%H:%M").time()
            end = datetime.strptime(end_time, "%H:%M").time()

            if start <= end:
                return start <= current <= end
            else:
                # 日付をまたぐ場合（例: 23:00-01:00）
                return current >= start or current <= end
        except Exception as e:
            self.logger.error(f"Time parsing error: {e}")
            return False

    def check_exit_conditions(
        self,
        position: Dict,
        market_data: Dict,
        rule: Dict
    ) -> Tuple[bool, str, str]:
        """
        決済条件をチェック

        Args:
            position: ポジション情報
                {
                    'ticket': 12345,
                    'entry_price': 149.50,
                    'entry_time': '2025-01-15 12:00:00',
                    'direction': 'BUY',
                    'volume': 0.1
                }
            market_data: 市場データ
            rule: 構造化トレードルール

        Returns:
            Tuple[bool, str, str]: (決済すべきか, 理由, アクション)
                アクション: "close_all", "close_50", "close_75"
        """
        exit_strat = rule.get('exit_strategy', {})
        current_price = market_data.get('current_price')
        entry_price = position.get('entry_price')

        if current_price is None or entry_price is None:
            return False, "Price data incomplete", "none"

        direction = position.get('direction')
        pips_profit = self._calculate_pips(entry_price, current_price, direction)

        # 1. Take Profitチェック
        tp_levels = exit_strat.get('take_profit', [])
        for tp in tp_levels:
            if pips_profit >= tp.get('pips', 999999):
                close_percent = tp.get('close_percent', 100)
                action = f"close_{close_percent}"
                return True, f"TP reached: {pips_profit}pips >= {tp['pips']}pips", action

        # 2. Stop Lossチェック
        sl = exit_strat.get('stop_loss', {})
        sl_price = sl.get('price_level')
        if sl_price:
            if direction == 'BUY' and current_price <= sl_price:
                return True, f"SL hit: {current_price} <= {sl_price}", "close_all"
            elif direction == 'SELL' and current_price >= sl_price:
                return True, f"SL hit: {current_price} >= {sl_price}", "close_all"

        # 3. Trailing SLチェック
        trailing = sl.get('trailing', {})
        activate_pips = trailing.get('activate_at_pips')
        if activate_pips and pips_profit >= activate_pips:
            trail_distance = trailing.get('trail_distance_pips', 10)
            new_sl = self._calculate_trailing_sl(entry_price, current_price, direction, trail_distance)
            # Trailing SLは別途ポジション更新ロジックで処理
            # ここでは決済判定のみ

        # 4. インジケーター決済チェック
        indicator_exits = exit_strat.get('indicator_exits', [])
        for exit_rule in indicator_exits:
            met, reason = self._check_indicator_exit(market_data, exit_rule)
            if met:
                action = exit_rule.get('action', 'close_all')
                return True, reason, action

        # 5. 時間制約チェック
        time_exits = exit_strat.get('time_exits', {})
        max_hold = time_exits.get('max_hold_minutes')
        force_close_time = time_exits.get('force_close_time')

        if max_hold:
            entry_time = datetime.fromisoformat(position.get('entry_time'))
            now = datetime.now()
            minutes_held = (now - entry_time).total_seconds() / 60
            if minutes_held >= max_hold:
                return True, f"Max holding time reached: {minutes_held}min >= {max_hold}min", "close_all"

        if force_close_time:
            current_time = market_data.get('current_time')
            if current_time and current_time >= force_close_time:
                return True, f"Force close time: {current_time}", "close_all"

        return False, "No exit conditions met", "none"

    def _check_indicator_exit(
        self,
        market_data: Dict,
        exit_rule: Dict
    ) -> Tuple[bool, str]:
        """インジケーター決済条件をチェック"""
        exit_type = exit_rule.get('type')
        timeframe = exit_rule.get('timeframe', 'M15')
        tf_data = market_data.get(timeframe, {})

        if exit_type == 'macd_cross':
            direction = exit_rule.get('direction')  # "bearish" or "bullish"
            macd_line = tf_data.get('macd_line')
            signal_line = tf_data.get('macd_signal')
            prev_macd = tf_data.get('prev_macd_line')
            prev_signal = tf_data.get('prev_macd_signal')

            if None in [macd_line, signal_line, prev_macd, prev_signal]:
                return False, ""

            if direction == 'bearish':
                # デッドクロス
                if prev_macd >= prev_signal and macd_line < signal_line:
                    return True, f"MACD bearish cross ({timeframe})"
            elif direction == 'bullish':
                # ゴールデンクロス
                if prev_macd <= prev_signal and macd_line > signal_line:
                    return True, f"MACD bullish cross ({timeframe})"

        elif exit_type == 'ema_break':
            period = exit_rule.get('period')
            direction = exit_rule.get('direction')  # "below" or "above"
            consecutive = exit_rule.get('consecutive_candles', 1)

            ema_key = f'ema_{period}'
            ema_value = tf_data.get(ema_key)
            current_price = market_data.get('current_price')

            if ema_value is None or current_price is None:
                return False, ""

            # 簡易実装: 連続足のチェックは省略（TODO: 足の履歴データが必要）
            if direction == 'below':
                if current_price < ema_value:
                    return True, f"Price below EMA{period} ({timeframe})"
            elif direction == 'above':
                if current_price > ema_value:
                    return True, f"Price above EMA{period} ({timeframe})"

        elif exit_type == 'rsi_threshold':
            threshold = exit_rule.get('threshold')
            direction = exit_rule.get('direction')  # "above" or "below"
            rsi = tf_data.get('rsi')

            if rsi is None or threshold is None:
                return False, ""

            if direction == 'above' and rsi > threshold:
                return True, f"RSI {rsi} > {threshold} ({timeframe})"
            elif direction == 'below' and rsi < threshold:
                return True, f"RSI {rsi} < {threshold} ({timeframe})"

        return False, ""

    def _calculate_pips(
        self,
        entry_price: float,
        current_price: float,
        direction: str
    ) -> float:
        """pips利益を計算"""
        if direction == 'BUY':
            return (current_price - entry_price) * 100  # USDJPY: 0.01 = 1pip
        else:  # SELL
            return (entry_price - current_price) * 100

    def _calculate_trailing_sl(
        self,
        entry_price: float,
        current_price: float,
        direction: str,
        trail_distance_pips: float
    ) -> float:
        """Trailing SL価格を計算"""
        trail_distance = trail_distance_pips / 100  # pips to price

        if direction == 'BUY':
            return current_price - trail_distance
        else:  # SELL
            return current_price + trail_distance


# モジュールのエクスポート
__all__ = ['StructuredRuleEngine']
