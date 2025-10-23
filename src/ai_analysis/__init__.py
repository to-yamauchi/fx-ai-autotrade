"""
========================================
AI分析パッケージ
========================================

パッケージ名: ai_analysis
パス: src/ai_analysis/

【概要】
Gemini APIを使用したマーケット分析とトレード判断を行うパッケージです。
フェーズ3で実装完了。

【含まれるモジュール】
- gemini_client.py: Gemini API連携（3モデル対応）
- ai_analyzer.py: AI分析オーケストレーター

【主な機能】
1. マーケットデータのAI分析
2. BUY/SELL/HOLD判断
3. 信頼度の算出（0-100）
4. 判断理由の生成
5. 判断結果のDB保存

【使用例】
```python
from src.ai_analysis import AIAnalyzer

# アナライザーの初期化
analyzer = AIAnalyzer(symbol='USDJPY', model='flash')

# マーケット分析実行
result = analyzer.analyze_market(year=2024, month=9)

print(f"Action: {result['action']}")
print(f"Confidence: {result['confidence']}%")
print(f"Reasoning: {result['reasoning']}")
```

【サポートモデル】
- daily_analysis: デイリー分析用（Phase 1, 2, 5）
- periodic_update: 定期更新用（Phase 3）
- position_monitor: ポジション監視用（Phase 4）

※後方互換性のため、旧名称（pro/flash/flash-lite/flash-8b）もサポート

【モデル設定】
.envファイルで以下の環境変数を設定してモデルを選択できます：
- GEMINI_MODEL_DAILY_ANALYSIS: デイリー分析用（デフォルト: gemini-2.5-flash）
- GEMINI_MODEL_PERIODIC_UPDATE: 定期更新用（デフォルト: gemini-2.5-flash）
- GEMINI_MODEL_POSITION_MONITOR: ポジション監視用（デフォルト: gemini-2.5-flash）
"""

from src.ai_analysis.gemini_client import GeminiClient
from src.ai_analysis.ai_analyzer import AIAnalyzer

__all__ = [
    'GeminiClient',
    'AIAnalyzer'
]
