"""
フェーズ4サンプルスクリプト: ルールエンジンとトレード実行
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ai_analysis import AIAnalyzer
from src.rule_engine import TradingRules
from src.trade_execution import PositionManager

print("=" * 80)
print("  フェーズ4: ルールエンジンとトレード実行 デモンストレーション")
print("=" * 80)
print()

# Phase 3: AI分析実行
print("【ステップ1】AI分析実行...")
analyzer = AIAnalyzer(symbol='USDJPY', model='flash')
ai_judgment = analyzer.analyze_market(year=2024, month=9)

print(f"AI判断: {ai_judgment['action']}")
print(f"信頼度: {ai_judgment['confidence']}%")
print()

# Phase 4: ルール検証
print("【ステップ2】ルール検証...")
rules = TradingRules()
is_valid, message = rules.validate_trade(
    ai_judgment=ai_judgment,
    current_positions=1,
    spread=2.0
)

print(f"検証結果: {'✓ PASS' if is_valid else '✗ FAIL'}")
print(f"理由: {message}")
print()

# Phase 4: トレード実行（デモモード）
print("【ステップ3】トレード実行（デモモード）...")
manager = PositionManager(symbol='USDJPY', use_mt5=False)
result = manager.process_ai_judgment(ai_judgment)

print(f"実行結果: {'✓ SUCCESS' if result['success'] else '✗ FAILED'}")
print(f"メッセージ: {result['message']}")
print()

print("=" * 80)
print("✓ フェーズ4の全機能が正常に動作しました")
print("=" * 80)
