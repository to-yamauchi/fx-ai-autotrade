"""
========================================
AI分析パッケージ（マルチLLMプロバイダー対応）
========================================

パッケージ名: ai_analysis
パス: src/ai_analysis/

【概要】
複数のLLMプロバイダー（Gemini/OpenAI/Anthropic）を使用したマーケット分析と
トレード判断を行うパッケージです。

【含まれるモジュール】
- base_llm_client.py: LLM共通インターフェース
- gemini_client.py: Google Gemini API連携
- openai_client.py: OpenAI ChatGPT API連携
- anthropic_client.py: Anthropic Claude API連携
- llm_client_factory.py: プロバイダー自動判定ファクトリー
- ai_analyzer.py: AI分析オーケストレーター

【主な機能】
1. マーケットデータのAI分析
2. BUY/SELL/HOLD判断
3. 信頼度の算出（0-100）
4. 判断理由の生成
5. 判断結果のDB保存
6. マルチプロバイダー対応（Phase別に異なるLLM使用可能）

【使用例】
```python
from src.ai_analysis import AIAnalyzer, create_llm_client

# マルチプロバイダー対応（モデル名から自動判定）
gemini_client = create_llm_client("gemini-2.5-flash")
openai_client = create_llm_client("gpt-4o")
claude_client = create_llm_client("claude-sonnet-4-5")

# アナライザーの初期化
analyzer = AIAnalyzer(symbol='USDJPY', model='flash')

# マーケット分析実行
result = analyzer.analyze_market(year=2024, month=9)

print(f"Action: {result['action']}")
print(f"Confidence: {result['confidence']}%")
print(f"Reasoning: {result['reasoning']}")
```

【対応プロバイダー】
- Google Gemini: gemini-*
- OpenAI ChatGPT: gpt-*, chatgpt-*, o1-*
- Anthropic Claude: claude-*

【モデル設定】
.envファイルで以下の環境変数を設定してPhase別にモデルを選択できます：
- MODEL_DAILY_ANALYSIS: デイリー分析用（Phase 1, 2, 5）
- MODEL_PERIODIC_UPDATE: 定期更新用（Phase 3）
- MODEL_POSITION_MONITOR: ポジション監視用（Phase 4）

例:
```
MODEL_DAILY_ANALYSIS=claude-sonnet-4-5
MODEL_PERIODIC_UPDATE=gemini-2.5-flash
MODEL_POSITION_MONITOR=gpt-4o-mini
```
"""

from src.ai_analysis.base_llm_client import BaseLLMClient
from src.ai_analysis.gemini_client import GeminiClient
from src.ai_analysis.openai_client import OpenAIClient
from src.ai_analysis.anthropic_client import AnthropicClient
from src.ai_analysis.llm_client_factory import create_llm_client, create_phase_clients
from src.ai_analysis.ai_analyzer import AIAnalyzer

__all__ = [
    'BaseLLMClient',
    'GeminiClient',
    'OpenAIClient',
    'AnthropicClient',
    'create_llm_client',
    'create_phase_clients',
    'AIAnalyzer'
]
