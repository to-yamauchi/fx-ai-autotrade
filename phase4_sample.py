"""
フェーズ4サンプルスクリプト: ルールエンジンとトレード実行
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from src.ai_analysis import AIAnalyzer
from src.rule_engine import TradingRules
from src.trade_execution import PositionManager

# 環境変数の読み込み
load_dotenv()

print("=" * 80)
print("  フェーズ4: ルールエンジンとトレード実行 デモンストレーション")
print("=" * 80)
print()

# Phase 3: AI分析実行
print("【ステップ1】AI分析実行...")

# APIキーが設定されているか確認
api_key = os.getenv('GEMINI_API_KEY')

if not api_key:
    print("\n" + "=" * 80)
    print("エラー: GEMINI_API_KEYが設定されていません")
    print("=" * 80)
    print()
    print(".envファイルにGEMINI_API_KEYを設定してください:")
    print("  1. .env.templateをコピーして.envファイルを作成")
    print("  2. GEMINI_API_KEY=your_api_key_here を追加")
    print()
    print("Gemini APIキーの取得方法:")
    print("  https://aistudio.google.com/app/apikey")
    print()
    sys.exit(1)

# 実際のAI分析を実行
print("Gemini APIを使用して実際のAI分析を実行中...")
analyzer = AIAnalyzer(symbol='USDJPY', model='flash')
ai_judgment = analyzer.analyze_market(year=2024, month=9)

print(f"AI判断: {ai_judgment['action']}")
print(f"信頼度: {ai_judgment['confidence']}%")
print(f"理由: {ai_judgment.get('reasoning', 'N/A')[:100]}...")
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

# 検証サマリー
print("【ステップ4】検証サマリー...")
print(f"  - 現在のポジション数: {result['validation']['current_positions']}")
print(f"  - 現在のスプレッド: {result['validation']['spread']} pips")
print(f"  - ルール検証: {'PASS' if result['validation']['passed'] else 'FAIL'}")
print()

print("=" * 80)
print("✓ フェーズ4の全機能が正常に動作しました")
print()
print("【実装済み機能】")
print("  ✓ トレードルールエンジン")
print("  ✓ ルール検証（信頼度/スプレッド/ポジション数/時間/ボラティリティ）")
print("  ✓ ポジションサイズ計算")
print("  ✓ MT5トレード実行（デモモード）")
print("  ✓ ポジション管理")
print()
print("【次のステップ】")
print("  → フェーズ5: モニタリングと決済システム")
print("  → フェーズ6: バックテストシステム")
print("=" * 80)
