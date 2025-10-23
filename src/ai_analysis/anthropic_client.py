"""
========================================
Anthropic Claude APIクライアント
========================================

ファイル名: anthropic_client.py
パス: src/ai_analysis/anthropic_client.py

【概要】
Anthropic Claude APIを使用してLLMレスポンスを生成するクライアントです。
BaseLLMClientを継承し、統一インターフェースを実装します。

【対応モデル】
- claude-sonnet-4-5 (最新・最高性能)
- claude-sonnet-4
- claude-haiku-4
- claude-opus-4

最新のモデル一覧: https://docs.anthropic.com/en/docs/about-claude/models

【使用例】
```python
from src.ai_analysis.anthropic_client import AnthropicClient

client = AnthropicClient(api_key="your_api_key")
response = client.generate_response(
    prompt="Analyze this market data...",
    model="claude-sonnet-4-5",
    temperature=0.3,
    max_tokens=2000
)
```

【作成日】2025-10-23
"""

from typing import Optional
import logging
from anthropic import Anthropic
from src.ai_analysis.base_llm_client import BaseLLMClient


class AnthropicClient(BaseLLMClient):
    """
    Anthropic Claude APIクライアント

    Anthropic APIを使用してLLMレスポンスを生成します。
    """

    def __init__(self, api_key: str):
        """
        AnthropicClientの初期化

        Args:
            api_key: Anthropic APIキー
        """
        super().__init__(api_key)
        self.client = Anthropic(api_key=api_key)
        self.logger.info("Anthropic client initialized")

    def generate_response(
        self,
        prompt: str,
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Anthropic APIからレスポンスを生成

        Args:
            prompt: プロンプトテキスト
            model: モデル名（例: claude-sonnet-4-5, claude-haiku-4）
            temperature: 温度パラメータ（0.0-1.0、デフォルト: 1.0）
            max_tokens: 最大トークン数（Noneの場合: 4096）
            **kwargs: その他のパラメータ（top_p, top_k, etc.）

        Returns:
            str: 生成されたテキスト

        Raises:
            Exception: API呼び出しが失敗した場合
        """
        try:
            # パラメータ設定
            params = {
                "model": model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                # Anthropic APIはmax_tokensが必須
                # Noneの場合は4096（Claude-4の推奨最大値）を使用
                "max_tokens": max_tokens if max_tokens is not None else 4096,
            }

            if temperature is not None:
                params["temperature"] = temperature

            # その他のパラメータをマージ
            params.update(kwargs)

            self.logger.debug(
                f"Anthropic API request: model={model}, "
                f"temperature={temperature}, max_tokens={max_tokens}"
            )

            # API呼び出し
            response = self.client.messages.create(**params)

            # レスポンスからテキストを取得
            if not response.content:
                raise ValueError("Anthropic API returned no content")

            # Claudeは複数のcontent blockを返す可能性があるが、通常は1つ
            text = "".join([block.text for block in response.content if hasattr(block, 'text')])

            # stop_reasonをチェック
            stop_reason = response.stop_reason
            if stop_reason == "max_tokens":
                self.logger.warning(
                    f"Response was truncated due to max_tokens limit. "
                    f"Current max_tokens: {max_tokens}. "
                    f"Consider increasing max_tokens in .env"
                )
            elif stop_reason == "stop_sequence":
                # 正常終了（stop sequenceに達した）
                pass
            elif stop_reason == "end_turn":
                # 正常終了（会話が終了）
                pass

            self.logger.debug(
                f"Anthropic API response received: "
                f"stop_reason={stop_reason}, "
                f"length={len(text)} chars"
            )

            return text

        except Exception as e:
            self.logger.error(f"Anthropic API error: {e}")
            raise

    def test_connection(self, verbose: bool = False) -> bool:
        """
        Anthropic APIへの接続テスト

        Args:
            verbose: 詳細なログを出力するかどうか

        Returns:
            bool: True=接続成功, False=接続失敗
        """
        try:
            if verbose:
                print("🔌 Anthropic API接続テスト中...", end='', flush=True)

            # 簡単なテストプロンプトを送信
            test_prompt = "Hello, this is a connection test. Please respond with 'OK'."
            response = self.generate_response(
                prompt=test_prompt,
                model="claude-haiku-4",  # 最も安価で高速なモデルでテスト
                max_tokens=10
            )

            if response:
                if verbose:
                    print(" ✓ 接続成功")
                self.logger.info("Anthropic API connection test: SUCCESS")
                return True
            else:
                if verbose:
                    print(" ✗ 接続失敗")
                self.logger.error("Anthropic API connection test: FAILED (empty response)")
                return False

        except Exception as e:
            if verbose:
                print(f" ✗ 接続失敗: {e}")
            self.logger.error(f"Anthropic API connection test: FAILED - {e}")
            return False

    def get_provider_name(self) -> str:
        """
        プロバイダー名を取得

        Returns:
            str: "anthropic"
        """
        return "anthropic"
