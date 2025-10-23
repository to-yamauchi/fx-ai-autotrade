"""
========================================
朝の詳細分析テストスクリプト
========================================

目的: morning_analysis()メソッドの動作確認
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
    print("朝の詳細分析テスト（morning_analysis）")
    print("=" * 80)
    print()

    # サンプルの市場データ（標準化済み形式）
    market_data = {
        "symbol": "USDJPY",
        "timestamp": "2024-09-15T08:00:00",
        "timeframes": {
            "D1": {
                "latest": {
                    "open": 149.20,
                    "high": 149.80,
                    "low": 149.10,
                    "close": 149.55,
                    "timestamp": "2024-09-15"
                }
            },
            "H4": {
                "latest": {
                    "open": 149.30,
                    "high": 149.65,
                    "low": 149.25,
                    "close": 149.55,
                    "timestamp": "2024-09-15T08:00:00"
                }
            },
            "H1": {
                "latest": {
                    "open": 149.45,
                    "high": 149.60,
                    "low": 149.40,
                    "close": 149.55,
                    "timestamp": "2024-09-15T08:00:00"
                }
            },
            "M15": {
                "latest": {
                    "open": 149.50,
                    "high": 149.57,
                    "low": 149.48,
                    "close": 149.55,
                    "timestamp": "2024-09-15T08:00:00"
                }
            }
        },
        "indicators": {
            "ema_short": 149.40,
            "ema_long": 149.20,
            "rsi": 52.3,
            "macd": {
                "macd": 0.15,
                "signal": 0.10,
                "histogram": 0.05
            },
            "atr": 0.35,
            "bollinger": {
                "upper": 149.80,
                "middle": 149.50,
                "lower": 149.20
            },
            "support_resistance": {
                "support": [149.20, 149.00, 148.80],
                "resistance": [149.70, 149.90, 150.10]
            }
        }
    }

    # サンプルの前日振り返り結果
    review_result = {
        "score": {
            "total": "75/100点",
            "direction": "32/40点",
            "entry_timing": "15/20点",
            "exit_timing": "18/20点",
            "risk_management": "10/20点"
        },
        "analysis": {
            "what_worked": [
                "EMAゴールデンクロス後のエントリーが的確だった",
                "レンジブレイク後の順張りが成功"
            ],
            "what_failed": [
                "早期利確で大きな波を逃した（+10pipsで決済→その後+30pipsまで伸びた）"
            ],
            "missed_signals": [
                "RSI 70超えの買われすぎシグナルを見逃した"
            ]
        },
        "lessons_for_today": [
            "トレンド継続時は早期利確を避け、トレーリングストップを活用する",
            "RSI 70超え時は新規買いエントリーを控える",
            "東京時間のレンジ相場では欧州時間まで様子見"
        ],
        "pattern_recognition": {
            "success_patterns": [
                "EMAクロス + RSI 50超え + MACDゴールデンクロス"
            ],
            "failure_patterns": [
                "東京時間早朝のレンジブレイクダマシ"
            ]
        }
    }

    # サンプルの過去5日統計
    past_statistics = {
        "last_5_days": {
            "total_pips": 45.5,
            "win_rate": "60.0%",
            "avg_holding_time": "180分",
            "total_trades": 10,
            "win_trades": 6,
            "loss_trades": 4
        }
    }

    print("テストデータ:")
    print(f"  市場データ: {market_data['symbol']} @ {market_data['timestamp']}")
    print(f"  前日レビュー: {review_result['score']['total']}")
    print(f"  過去5日統計: {past_statistics['last_5_days']['total_pips']}pips, 勝率{past_statistics['last_5_days']['win_rate']}")
    print()

    # AIAnalyzer初期化（Gemini Pro使用）
    print("AIAnalyzer初期化中...")
    analyzer = AIAnalyzer(
        symbol='USDJPY',
        model='pro',
        backtest_start_date='2024-09-01',
        backtest_end_date='2024-09-30'
    )
    print("✓ 初期化完了")
    print()

    # 朝の詳細分析を実行
    print("朝の詳細分析を実行中...")
    print("（Gemini Pro APIを呼び出します。数秒かかる場合があります）")
    print()

    try:
        strategy_result = analyzer.morning_analysis(
            market_data=market_data,
            review_result=review_result,
            past_statistics=past_statistics
        )

        print("=" * 80)
        print("分析結果")
        print("=" * 80)
        print()

        # 基本情報
        print(f"日次バイアス: {strategy_result.get('daily_bias', 'N/A')}")
        print(f"信頼度: {strategy_result.get('confidence', 0):.2f}")
        print()

        # 判断理由
        print("判断理由:")
        print(f"  {strategy_result.get('reasoning', 'N/A')}")
        print()

        # 市場環境
        env = strategy_result.get('market_environment', {})
        print("市場環境:")
        print(f"  トレンド: {env.get('trend', 'N/A')}")
        print(f"  強度: {env.get('strength', 'N/A')}")
        print(f"  フェーズ: {env.get('phase', 'N/A')}")
        print()

        # エントリー条件
        entry = strategy_result.get('entry_conditions', {})
        print("エントリー条件:")
        print(f"  取引すべきか: {entry.get('should_trade', False)}")
        print(f"  方向: {entry.get('direction', 'N/A')}")
        price_zone = entry.get('price_zone', {})
        print(f"  価格ゾーン: {price_zone.get('min', 0):.2f} ~ {price_zone.get('max', 0):.2f}")
        print(f"  必須シグナル: {len(entry.get('required_signals', []))}個")
        for i, signal in enumerate(entry.get('required_signals', []), 1):
            print(f"    {i}. {signal}")
        print()

        # 決済戦略
        exit_strat = strategy_result.get('exit_strategy', {})
        print("決済戦略:")
        tp_levels = exit_strat.get('take_profit', [])
        print(f"  利確レベル: {len(tp_levels)}段階")
        for level in tp_levels:
            print(f"    +{level.get('pips', 0)}pips: {level.get('close_percent', 0)}%決済 ({level.get('reason', '')})")
        print()

        # リスク管理
        risk = strategy_result.get('risk_management', {})
        print("リスク管理:")
        print(f"  ポジションサイズ倍率: {risk.get('position_size_multiplier', 1.0):.2f}")
        print(f"  最大ポジション数: {risk.get('max_positions', 1)}")
        print(f"  理由: {risk.get('reason', 'N/A')}")
        print()

        # 重要レベル
        levels = strategy_result.get('key_levels', {})
        print("重要価格レベル:")
        print(f"  エントリー目標: {levels.get('entry_target', 'N/A')}")
        print(f"  無効化レベル: {levels.get('invalidation_level', 'N/A')}")
        print(f"  重要サポート: {levels.get('critical_support', 'N/A')}")
        print(f"  重要レジスタンス: {levels.get('critical_resistance', 'N/A')}")
        print()

        # 教訓の適用
        lessons = strategy_result.get('lessons_applied', [])
        print(f"適用された教訓: {len(lessons)}個")
        for i, lesson in enumerate(lessons, 1):
            print(f"  {i}. {lesson}")
        print()

        # JSON出力
        print("=" * 80)
        print("完全なJSON結果")
        print("=" * 80)
        print(json.dumps(strategy_result, ensure_ascii=False, indent=2))
        print()

        # データベース確認
        print("=" * 80)
        print("データベース確認")
        print("=" * 80)
        print("以下のコマンドで保存されたデータを確認できます:")
        print()
        print("  psql -U postgres -d fx_autotrade")
        print("  SELECT strategy_date, symbol, daily_bias, confidence")
        print("    FROM backtest_daily_strategies")
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
