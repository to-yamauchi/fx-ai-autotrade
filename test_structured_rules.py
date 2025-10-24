"""
構造化トレードルールのテストスクリプト

【概要】
構造化ルールエンジンの動作確認を行います。

【使用方法】
python test_structured_rules.py

【テスト内容】
1. エントリー条件のチェック（価格ゾーン、RSI、EMA、MACD）
2. 決済条件のチェック（TP、SL、インジケーター決済）
3. 時間フィルターのチェック

【作成日】2025-01-15
"""

from src.rule_engine import StructuredRuleEngine
import json


def test_entry_conditions():
    """エントリー条件のテスト"""
    print("=" * 80)
    print("エントリー条件テスト")
    print("=" * 80)

    engine = StructuredRuleEngine()

    # テスト用の市場データ
    market_data = {
        'current_price': 149.55,
        'spread': 2.5,
        'current_time': '14:30',
        'M15': {
            'rsi': 55,
            'ema_20': 149.40,
            'ema_50': 149.30,
            'macd_histogram': 0.05,
            'macd_line': 0.10,
            'macd_signal': 0.08,
            'prev_close': 149.50,
            'prev_macd_line': 0.07,
            'prev_macd_signal': 0.09,
        }
    }

    # テスト用のルール
    rule = {
        'entry_conditions': {
            'should_trade': True,
            'direction': 'BUY',
            'price_zone': {
                'min': 149.50,
                'max': 149.65
            },
            'indicators': {
                'rsi': {
                    'timeframe': 'M15',
                    'min': 50,
                    'max': 70
                },
                'ema': {
                    'timeframe': 'M15',
                    'condition': 'price_above',
                    'period': 20
                },
                'macd': {
                    'timeframe': 'M15',
                    'condition': 'histogram_positive'
                }
            },
            'spread': {
                'max_pips': 10
            },
            'time_filter': {
                'avoid_times': [
                    {'start': '09:50', 'end': '10:00', 'reason': 'Tokyo fixing'}
                ]
            }
        }
    }

    # テスト実行
    print("\n【市場データ】")
    print(f"  価格: {market_data['current_price']}")
    print(f"  RSI(M15): {market_data['M15']['rsi']}")
    print(f"  EMA20(M15): {market_data['M15']['ema_20']}")
    print(f"  MACDヒストグラム(M15): {market_data['M15']['macd_histogram']}")
    print(f"  スプレッド: {market_data['spread']}pips")
    print(f"  現在時刻: {market_data['current_time']}")

    print("\n【ルール】")
    print(f"  価格ゾーン: {rule['entry_conditions']['price_zone']['min']} ~ {rule['entry_conditions']['price_zone']['max']}")
    print(f"  RSI: {rule['entry_conditions']['indicators']['rsi']['min']} ~ {rule['entry_conditions']['indicators']['rsi']['max']}")
    print(f"  EMA20: {rule['entry_conditions']['indicators']['ema']['condition']}")
    print(f"  MACD: {rule['entry_conditions']['indicators']['macd']['condition']}")

    print("\n【判定結果】")
    is_valid, message = engine.check_entry_conditions(market_data, rule)
    if is_valid:
        print(f"  ✅ エントリー可能: {message}")
    else:
        print(f"  ❌ エントリー不可: {message}")

    # 失敗ケースのテスト
    print("\n" + "-" * 80)
    print("【失敗ケース1: RSIが範囲外】")
    market_data_fail = market_data.copy()
    market_data_fail['M15'] = market_data['M15'].copy()
    market_data_fail['M15']['rsi'] = 75  # 70を超える

    is_valid, message = engine.check_entry_conditions(market_data_fail, rule)
    print(f"  RSI: {market_data_fail['M15']['rsi']}")
    if is_valid:
        print(f"  ✅ エントリー可能: {message}")
    else:
        print(f"  ❌ エントリー不可: {message}")

    print("\n" + "-" * 80)
    print("【失敗ケース2: 価格がゾーン外】")
    market_data_fail2 = market_data.copy()
    market_data_fail2['current_price'] = 149.70  # 149.65を超える

    is_valid, message = engine.check_entry_conditions(market_data_fail2, rule)
    print(f"  価格: {market_data_fail2['current_price']}")
    if is_valid:
        print(f"  ✅ エントリー可能: {message}")
    else:
        print(f"  ❌ エントリー不可: {message}")


def test_exit_conditions():
    """決済条件のテスト"""
    print("\n\n" + "=" * 80)
    print("決済条件テスト")
    print("=" * 80)

    engine = StructuredRuleEngine()

    # テスト用のポジション
    position = {
        'ticket': 12345,
        'entry_price': 149.50,
        'entry_time': '2025-01-15 12:00:00',
        'direction': 'BUY',
        'volume': 0.1
    }

    # テスト用の市場データ
    market_data = {
        'current_price': 149.70,  # +20pips
        'current_time': '14:30',
        'M15': {
            'macd_line': 0.05,
            'macd_signal': 0.08,
            'prev_macd_line': 0.10,
            'prev_macd_signal': 0.07,
        }
    }

    # テスト用のルール
    rule = {
        'exit_strategy': {
            'take_profit': [
                {'pips': 10, 'close_percent': 30},
                {'pips': 20, 'close_percent': 40},
                {'pips': 30, 'close_percent': 100}
            ],
            'stop_loss': {
                'price_level': 149.40,
                'trailing': {
                    'activate_at_pips': 15,
                    'trail_distance_pips': 10
                }
            },
            'indicator_exits': [
                {
                    'type': 'macd_cross',
                    'timeframe': 'M15',
                    'direction': 'bearish',
                    'action': 'close_50'
                }
            ],
            'time_exits': {
                'max_hold_minutes': 240,
                'force_close_time': '23:00'
            }
        }
    }

    # テスト実行
    print("\n【ポジション】")
    print(f"  エントリー価格: {position['entry_price']}")
    print(f"  現在価格: {market_data['current_price']}")
    print(f"  損益: +{(market_data['current_price'] - position['entry_price']) * 100:.1f}pips")

    print("\n【判定結果】")
    should_exit, reason, action = engine.check_exit_conditions(position, market_data, rule)
    if should_exit:
        print(f"  ✅ 決済すべき: {reason}")
        print(f"  アクション: {action}")
    else:
        print(f"  ❌ 保有継続: {reason}")


def main():
    """メイン処理"""
    print("\n構造化トレードルールエンジン テスト")
    print("=" * 80)

    test_entry_conditions()
    test_exit_conditions()

    print("\n" + "=" * 80)
    print("テスト完了")
    print("=" * 80)


if __name__ == '__main__':
    main()
