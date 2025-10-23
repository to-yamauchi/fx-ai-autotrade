"""
========================================
LLMクライアント基底クラス
========================================

ファイル名: base_llm_client.py
パス: src/ai_analysis/base_llm_client.py

【概要】
複数のLLMプロバイダー（Gemini/OpenAI/Anthropic）に対応するための
統一インターフェースを定義する基底クラスです。

【対応プロバイダー】
- Google Gemini (gemini-*)
- OpenAI ChatGPT (gpt-*, chatgpt-*, o1-*)
- Anthropic Claude (claude-*)

【使用例】
```python
from src.ai_analysis.base_llm_client import BaseLLMClient
from src.ai_analysis.gemini_client import GeminiClient

client: BaseLLMClient = GeminiClient(api_key="xxx")
response = client.generate_response(prompt="Hello", model="gemini-2.5-flash")
```

【作成日】2025-10-23
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional
import logging


class BaseLLMClient(ABC):
    """
    LLMクライアントの基底クラス

    全てのLLMクライアント（Gemini/OpenAI/Anthropic）はこのクラスを継承し、
    統一されたインターフェースを実装する必要があります。
    """

    def __init__(self, api_key: str):
        """
        LLMクライアントの初期化

        Args:
            api_key: APIキー
        """
        self.api_key = api_key
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def generate_response(
        self,
        prompt: str,
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        LLMからレスポンスを生成

        Args:
            prompt: プロンプトテキスト
            model: モデル名（例: gemini-2.5-flash, gpt-4o, claude-sonnet-4-5）
            temperature: 温度パラメータ（0.0-1.0、低いほど決定論的）
            max_tokens: 最大トークン数
            **kwargs: プロバイダー固有のパラメータ

        Returns:
            str: LLMの生成したテキスト

        Raises:
            ValueError: パラメータが不正な場合
            Exception: API呼び出しが失敗した場合
        """
        pass

    @abstractmethod
    def test_connection(self, verbose: bool = False) -> bool:
        """
        APIへの接続テスト

        簡単なプロンプトを送信してAPIが正常に動作するか確認します。

        Args:
            verbose: 詳細なログを出力するかどうか

        Returns:
            bool: True=接続成功, False=接続失敗
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """
        プロバイダー名を取得

        Returns:
            str: プロバイダー名（gemini/openai/anthropic）
        """
        pass

    def _handle_finish_reason(self, finish_reason: Optional[int], response: any) -> str:
        """
        finish_reasonを処理（プロバイダー共通）

        Args:
            finish_reason: 終了理由コード
            response: レスポンスオブジェクト

        Returns:
            str: レスポンステキスト

        Raises:
            ValueError: finish_reasonがエラーを示す場合
        """
        # サブクラスでオーバーライド可能
        return ""
