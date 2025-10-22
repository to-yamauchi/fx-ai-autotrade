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
- pro: gemini-1.5-pro-latest（高精度、コスト高）
- flash: gemini-1.5-flash-latest（バランス型、推奨）
- flash-lite: gemini-1.5-flash-8b-latest（高速軽量）
"""

from src.ai_analysis.gemini_client import GeminiClient
from src.ai_analysis.ai_analyzer import AIAnalyzer

__all__ = [
    'GeminiClient',
    'AIAnalyzer'
]
