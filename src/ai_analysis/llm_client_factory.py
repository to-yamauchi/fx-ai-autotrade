"""
========================================
LLMクライアントファクトリー
========================================

ファイル名: llm_client_factory.py
パス: src/ai_analysis/llm_client_factory.py

【概要】
モデル名からプロバイダーを自動判定し、適切なLLMクライアントを生成します。
ファクトリーパターンを使用して、Phase別に異なるLLMを使用できるようにします。

【対応プロバイダー】
- Google Gemini: gemini-* モデル
- OpenAI ChatGPT: gpt-*, chatgpt-*, o1-* モデル
- Anthropic Claude: claude-* モデル

【使用例】
```python
from src.ai_analysis.llm_client_factory import create_llm_client

# モデル名から自動判定
client = create_llm_client(model_name="gemini-2.5-flash")
client = create_llm_client(model_name="gpt-4o")
client = create_llm_client(model_name="claude-sonnet-4-5")
```

【作成日】2025-10-23
"""

from typing import Optional
import logging
from src.utils.config import get_config
from src.ai_analysis.base_llm_client import BaseLLMClient


logger = logging.getLogger(__name__)


def detect_provider_from_model(model_name: str) -> str:
    """
    モデル名からプロバイダーを自動判定

    Args:
        model_name: モデル名（例: gemini-2.5-flash, gpt-4o, claude-sonnet-4-5）

    Returns:
        str: プロバイダー名（gemini/openai/anthropic）

    Raises:
        ValueError: 未対応のモデル名の場合
    """
    model_lower = model_name.lower()

    if model_lower.startswith('gemini-'):
        return 'gemini'
    elif model_lower.startswith(('gpt-', 'chatgpt-', 'o1-')):
        return 'openai'
    elif model_lower.startswith('claude-'):
        return 'anthropic'
    else:
        raise ValueError(
            f"未対応のモデル名: {model_name}\n"
            "対応プロバイダー:\n"
            "  - Gemini: gemini-*\n"
            "  - OpenAI: gpt-*, chatgpt-*, o1-*\n"
            "  - Anthropic: claude-*"
        )


def create_llm_client(
    model_name: str,
    api_key: Optional[str] = None
) -> BaseLLMClient:
    """
    モデル名からLLMクライアントを生成

    モデル名のプレフィックスからプロバイダーを自動判定し、
    適切なLLMクライアントを生成します。

    Args:
        model_name: モデル名
        api_key: APIキー（省略時は環境変数から取得）

    Returns:
        BaseLLMClient: LLMクライアントインスタンス

    Raises:
        ValueError: 未対応のモデル名の場合
        ValueError: APIキーが設定されていない場合
    """
    provider = detect_provider_from_model(model_name)
    config = get_config()

    # API Keyの取得
    if api_key is None:
        if provider == 'gemini':
            api_key = config.gemini_api_key
        elif provider == 'openai':
            api_key = config.openai_api_key
        elif provider == 'anthropic':
            api_key = config.anthropic_api_key

    # API Key検証
    if not api_key:
        raise ValueError(
            f"{provider.upper()}_API_KEYが設定されていません。\n"
            f".envファイルで{provider.upper()}_API_KEYを設定してください。"
        )

    # プロバイダー別にクライアント生成
    if provider == 'gemini':
        from src.ai_analysis.gemini_client import GeminiClient
        logger.info(f"Creating Gemini client for model: {model_name}")
        return GeminiClient(api_key=api_key)

    elif provider == 'openai':
        from src.ai_analysis.openai_client import OpenAIClient
        logger.info(f"Creating OpenAI client for model: {model_name}")
        return OpenAIClient(api_key=api_key)

    elif provider == 'anthropic':
        from src.ai_analysis.anthropic_client import AnthropicClient
        logger.info(f"Creating Anthropic client for model: {model_name}")
        return AnthropicClient(api_key=api_key)

    else:
        # ここには到達しないはず（detect_provider_from_modelでエラーになる）
        raise ValueError(f"Unknown provider: {provider}")


def create_phase_clients() -> dict:
    """
    各Phase用のLLMクライアントを生成

    環境変数で設定されたモデル名に基づいて、
    各Phaseで使用するLLMクライアントを生成します。

    Returns:
        dict: Phase名をキーとするクライアント辞書
            {
                'daily_analysis': BaseLLMClient,
                'periodic_update': BaseLLMClient,
                'position_monitor': BaseLLMClient
            }
    """
    config = get_config()

    clients = {
        'daily_analysis': create_llm_client(config.model_daily_analysis),
        'periodic_update': create_llm_client(config.model_periodic_update),
        'position_monitor': create_llm_client(config.model_position_monitor),
    }

    logger.info(
        f"Phase clients created:\n"
        f"  Daily Analysis: {config.model_daily_analysis}\n"
        f"  Periodic Update: {config.model_periodic_update}\n"
        f"  Position Monitor: {config.model_position_monitor}"
    )

    return clients
