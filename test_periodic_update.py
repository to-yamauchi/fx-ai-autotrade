"""
========================================
定期更新テストスクリプト
========================================

目的: periodic_update()メソッドの動作確認
作成日: 2025-10-23
"""

import os
import sys
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 環境変数の読み込み
load_dotenv()

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from src.ai_analysis.ai_analyzer import AIAnalyzer

def main():
    """メイン処理"""
    print("=" * 80)
    print("定期更新テスト（periodic_update）")
    print("=" * 80)
    print()

    # サンプルの朝の戦略
    morning_strategy = {
        "daily_bias": "BUY",
        "confidence": 0.75,
        "reasoning": "EMAゴールデンクロス + RSI上昇トレンド",
        "market_environment": {
            "trend": "上昇",
            "strength": "強い",
            "phase": "トレンド継続"
        },
        "entry_conditions": {
            "should_trade": True,
            "direction": "BUY",
            "price_zone": {"min": 149.50, "max": 149.70},
            "required_signals": [
                "EMA短期 > EMA長期",
                "RSI > 50",
                "MACD ヒストグラム > 0"
            ],
            "avoid_if": ["RSI > 70", "重要レジスタンス到達"]
        },
        "exit_strategy": {
            "take_profit": [
                {"pips": 30, "close_percent": 50, "reason": "第1目標"},
                {"pips": 50, "close_percent": 50, "reason": "第2目標"}
            ],
            "stop_loss": {"initial": "149.20", "trailing": True},
            "indicator_exits": ["RSI < 50でイグジット"],
            "time_exits": {"max_holding": "24時間"}
        },
        "risk_management": {
            "position_size_multiplier": 1.0,
            "max_positions": 2,
            "reason": "通常リスク設定"
        }
    }

    # サンプルの現在市場データ（16:00時点）
    current_market_data = {
        "symbol": "USDJPY",
        "timestamp": "2024-09-15T16:00:00",
        "timeframes": {
            "D1": {
                "latest": {
                    "open": 149.20,
                    "high": 149.90,
                    "low": 149.10,
                    "close": 149.75,
                    "timestamp": "2024-09-15"
                }
            },
            "H4": {
                "latest": {
                    "open": 149.55,
                    "high": 149.80,
                    "low": 149.50,
                    "close": 149.75,
                    "timestamp": "2024-09-15T16:00:00"
                }
            },
            "H1": {
                "latest": {
                    "open": 149.70,
                    "high": 149.78,
                    "low": 149.65,
                    "close": 149.75,
                    "timestamp": "2024-09-15T16:00:00"
                }
            }
        },
        "indicators": {
            "ema_short": 149.60,
            "ema_long": 149.30,
            "rsi": 68.5,  # 朝より上昇（買われすぎに接近）
            "macd": {
                "macd": 0.20,
                "signal": 0.15,
                "histogram": 0.05
            },
            "atr": 0.40,
            "bollinger": {
                "upper": 149.90,
                "middle": 149.60,
                "lower": 149.30
            }
        }
    }

    # サンプルの本日トレード実績
    today_trades = [
        {
            "entry_time": "2024-09-15T09:30:00",
            "exit_time": "2024-09-15T14:00:00",
            "direction": "BUY",
            "entry_price": 149.55,
            "exit_price": 149.85,
            "pips": 30.0,
            "profit_loss": 3000,
            "exit_reason": "take_profit_1"
        }
    ]

    # サンプルの現在ポジション
    current_positions = [
        {
            "direction": "BUY",
            "entry_price": 149.60,
            "entry_time": "2024-09-15T10:00:00",
            "current_profit_pips": 15.0,
            "stop_loss": 149.20,
            "take_profit": 150.10
        }
    ]

    print("テストデータ:")
    print(f"  朝の戦略: {morning_strategy['daily_bias']}, 信頼度 {morning_strategy['confidence']}")
    print(f"  現在時刻: 16:00")
    print(f"  現在価格: 149.75円")
    print(f"  RSI: 68.5 (朝:52.3 → 買われすぎ接近)")
    print(f"  本日トレード: {len(today_trades)}件")
    print(f"  現在ポジション: {len(current_positions)}個 (含み益 +15pips)")
    print()

    # AIAnalyzer初期化（Gemini Flash使用）
    print("AIAnalyzer初期化中...")
    analyzer = AIAnalyzer(
        symbol='USDJPY',
        model='flash',  # 定期更新はFlash
        backtest_start_date='2024-09-01',
        backtest_end_date='2024-09-30'
    )
    print("✓ 初期化完了")
    print()

    # 定期更新を実行
    print("16:00 定期更新を実行中...")
    print("（Gemini Flash APIを呼び出します。数秒かかる場合があります）")
    print()

    try:
        update_result = analyzer.periodic_update(
            morning_strategy=morning_strategy,
            current_market_data=current_market_data,
            today_trades=today_trades,
            current_positions=current_positions,
            update_time="16:00"
        )

        print("=" * 80)
        print("更新結果")
        print("=" * 80)
        print()

        # 基本情報
        print(f"更新タイプ: {update_result.get('update_type', 'N/A')}")
        print(f"要約: {update_result.get('summary', 'N/A')}")
        print()

        # 市場評価
        assessment = update_result.get('market_assessment', {})
        print("市場評価:")
        print(f"  トレンド変化: {assessment.get('trend_change', 'N/A')}")
        print(f"  ボラティリティ変化: {assessment.get('volatility_change', 'N/A')}")
        key_events = assessment.get('key_events', [])
        if key_events:
            print(f"  重要イベント:")
            for event in key_events:
                print(f"    - {event}")
        print()

        # 戦略の妥当性
        validity = update_result.get('strategy_validity', {})
        print("戦略の妥当性:")
        print(f"  朝のバイアス有効: {validity.get('morning_bias_valid', 'N/A')}")
        print(f"  信頼度変化: {validity.get('confidence_change', 0):+.2f}")
        print(f"  理由: {validity.get('reasoning', 'N/A')}")
        print()

        # 推奨変更
        changes = update_result.get('recommended_changes', {})
        print("推奨変更:")

        # バイアス変更
        bias_change = changes.get('bias', {})
        if bias_change.get('apply', False):
            print(f"  ✓ バイアス変更: {bias_change.get('from')} → {bias_change.get('to')}")
        else:
            print(f"  - バイアス変更なし")

        # リスク調整
        risk_changes = changes.get('risk_management', {})
        if 'position_size_multiplier' in risk_changes:
            multiplier = risk_changes['position_size_multiplier']
            if multiplier.get('apply', False):
                print(f"  ✓ ポジションサイズ: {multiplier.get('from')} → {multiplier.get('to')} ({multiplier.get('reason')})")

        if 'max_positions' in risk_changes:
            max_pos = risk_changes['max_positions']
            if max_pos.get('apply', False):
                print(f"  ✓ 最大ポジション数: {max_pos.get('from')} → {max_pos.get('to')} ({max_pos.get('reason')})")

        # 決済戦略
        exit_changes = changes.get('exit_strategy', {})
        if 'stop_loss' in exit_changes:
            sl_change = exit_changes['stop_loss']
            if sl_change.get('apply', False):
                print(f"  ✓ ストップロス: {sl_change.get('action')} - {sl_change.get('reason')}")

        print()

        # 現在ポジションのアクション
        pos_action = update_result.get('current_positions_action', {})
        print("現在ポジションのアクション:")
        if pos_action.get('keep_open', True):
            print("  - ポジション継続")
            if pos_action.get('adjust_sl', {}).get('apply', False):
                new_sl = pos_action['adjust_sl'].get('new_sl_price')
                reason = pos_action['adjust_sl'].get('reason')
                print(f"    ✓ SL調整: {new_sl}円 ({reason})")
        else:
            print(f"  ✗ ポジションクローズ推奨: {pos_action.get('close_reason')}")
        print()

        # 新規エントリー推奨
        entry_rec = update_result.get('new_entry_recommendation', {})
        print("新規エントリー推奨:")
        if entry_rec.get('should_enter_now', False):
            print(f"  ✓ エントリー推奨: {entry_rec.get('direction')}")
            print(f"    理由: {entry_rec.get('reason')}")
            price_zone = entry_rec.get('entry_price_zone', {})
            print(f"    価格ゾーン: {price_zone.get('min')}円 ~ {price_zone.get('max')}円")
        else:
            print(f"  - エントリー推奨なし: {entry_rec.get('reason', '戦略に変更なし')}")
        print()

        # JSON出力
        print("=" * 80)
        print("完全なJSON結果")
        print("=" * 80)
        print(json.dumps(update_result, ensure_ascii=False, indent=2))
        print()

        # データベース確認
        print("=" * 80)
        print("データベース確認")
        print("=" * 80)
        print("以下のコマンドで保存されたデータを確認できます:")
        print()
        print("  psql -U postgres -d fx_autotrade")
        print("  SELECT update_date, update_time, symbol, update_type, summary")
        print("    FROM backtest_periodic_updates")
        print("    ORDER BY created_at DESC")
        print("    LIMIT 1;")
        print()

        print("=" * 80)
        print("テスト完了")
        print("=" * 80)

    except Exception as e:
        print()
        print("=" * 80)
        print("エラーが発生しました")
        print("=" * 80)
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
