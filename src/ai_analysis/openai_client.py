"""
========================================
OpenAI APIクライアント
========================================

ファイル名: openai_client.py
パス: src/ai_analysis/openai_client.py

【概要】
OpenAI ChatGPT APIを使用してLLMレスポンスを生成するクライアントです。
BaseLLMClientを継承し、統一インターフェースを実装します。

【対応モデル】
- gpt-4o
- gpt-4o-mini
- gpt-4-turbo
- gpt-3.5-turbo
- o1-preview
- o1-mini

最新のモデル一覧: https://platform.openai.com/docs/models

【使用例】
```python
from src.ai_analysis.openai_client import OpenAIClient

client = OpenAIClient(api_key="your_api_key")
response = client.generate_response(
    prompt="Analyze this market data...",
    model="gpt-4o",
    temperature=0.3,
    max_tokens=2000
)
```

【作成日】2025-10-23
"""

from typing import Optional
import logging
from openai import OpenAI
from src.ai_analysis.base_llm_client import BaseLLMClient


class OpenAIClient(BaseLLMClient):
    """
    OpenAI ChatGPT APIクライアント

    OpenAI APIを使用してLLMレスポンスを生成します。
    """

    def __init__(self, api_key: str):
        """
        OpenAIClientの初期化

        Args:
            api_key: OpenAI APIキー
        """
        super().__init__(api_key)
        self.client = OpenAI(api_key=api_key)
        self.logger.info("OpenAI client initialized")

    def _select_model(self, model: str) -> str:
        """
        使用するモデルを選択する

        Args:
            model: モデル名（完全なモデル名 例: gpt-4o）
                または短縮名（Phase名）:
                - 'daily_analysis': MODEL_DAILY_ANALYSISの値を使用
                - 'periodic_update': MODEL_PERIODIC_UPDATEの値を使用
                - 'position_monitor': MODEL_POSITION_MONITORの値を使用
                - 'emergency_evaluation': MODEL_EMERGENCY_EVALUATIONの値を使用

        Returns:
            str: 実際のモデル名

        Raises:
            ValueError: モデル設定が不正な場合
        """
        from src.utils.config import get_config
        config = get_config()

        # Phase名から.env設定へのマッピング
        phase_to_config_mapping = {
            'daily_analysis': config.model_daily_analysis,
            'periodic_update': config.model_periodic_update,
            'position_monitor': config.model_position_monitor,
            'emergency_evaluation': config.model_emergency_evaluation,
        }

        # Phase名の場合は.envから設定を取得
        if model in phase_to_config_mapping:
            model_name = phase_to_config_mapping[model]
            if not model_name:
                raise ValueError(
                    f"Model for phase '{model}' is not configured in .env file. "
                    f"Please set the appropriate MODEL_* environment variable."
                )
            self.logger.debug(f"Phase '{model}' mapped to model '{model_name}'")
        else:
            # すでに完全なモデル名
            model_name = model

        # モデル名のバリデーション - OpenAIClient はOpenAIモデルのみ対応
        if not model_name.startswith(('gpt-', 'o1-', 'chatgpt-')):
            # OpenAI以外のモデルが指定された場合
            provider_hint = "Unknown"
            if model_name.startswith('gemini-'):
                provider_hint = "Google Gemini"
            elif model_name.startswith('claude-'):
                provider_hint = "Anthropic Claude"

            raise ValueError(
                f"OpenAIClient cannot use non-OpenAI model: '{model_name}' ({provider_hint})\n"
                f"Please configure an OpenAI model (gpt-*, o1-*, chatgpt-*) in your .env file.\n"
                f"Example OpenAI models:\n"
                f"  - gpt-4o\n"
                f"  - gpt-4o-mini\n"
                f"  - gpt-5-nano\n"
                f"  - o1-preview\n"
                f"\n"
                f"If you want to use {provider_hint} models, configure them in MODEL_* variables\n"
                f"and the system will automatically select the appropriate client."
            )

        return model_name

    def generate_response(
        self,
        prompt: str,
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        OpenAI APIからレスポンスを生成

        Args:
            prompt: プロンプトテキスト
            model: モデル名（例: gpt-4o, gpt-4o-mini）
                  またはPhase名（例: daily_analysis, periodic_update）
            temperature: 温度パラメータ（0.0-2.0、デフォルト: 1.0）
            max_tokens: 最大トークン数
            **kwargs: その他のパラメータ（top_p, frequency_penalty, etc.）

        Returns:
            str: 生成されたテキスト

        Raises:
            Exception: API呼び出しが失敗した場合
        """
        try:
            # Phase名を実際のモデル名に変換
            actual_model = self._select_model(model)

            # パラメータ設定
            params = {
                "model": actual_model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
            }

            if temperature is not None:
                params["temperature"] = temperature
            if max_tokens is not None:
                params["max_tokens"] = max_tokens

            # その他のパラメータをマージ（phase除外）
            phase = kwargs.pop('phase', 'Unknown')
            params.update(kwargs)

            self.logger.debug(
                f"OpenAI API request: model={actual_model}, "
                f"temperature={temperature}, max_tokens={max_tokens}"
            )

            # API呼び出し
            response = self.client.chat.completions.create(**params)

            # レスポンスからテキストを取得
            if not response.choices:
                raise ValueError("OpenAI API returned no choices")

            text = response.choices[0].message.content

            # finish_reasonをチェック
            finish_reason = response.choices[0].finish_reason
            if finish_reason == "length":
                self.logger.warning(
                    f"Response was truncated due to max_tokens limit. "
                    f"Current max_tokens: {max_tokens}. "
                    f"Consider increasing max_tokens in .env"
                )
            elif finish_reason == "content_filter":
                raise ValueError(
                    "Response was filtered by OpenAI content policy. "
                    "Please modify your prompt."
                )

            self.logger.debug(
                f"OpenAI API response received: "
                f"finish_reason={finish_reason}, "
                f"length={len(text)} chars"
            )

            # トークン使用量を記録
            if hasattr(response, 'usage'):
                from src.ai_analysis.token_usage_tracker import get_token_tracker
                tracker = get_token_tracker()
                tracker.record_usage(
                    phase=phase,
                    provider='openai',
                    model=actual_model,
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens
                )

            return text

        except Exception as e:
            self.logger.error(f"OpenAI API error: {e}")
            raise

    def test_connection(self, verbose: bool = False) -> bool:
        """
        OpenAI APIへの接続テスト

        Args:
            verbose: 詳細なログを出力するかどうか

        Returns:
            bool: True=接続成功, False=接続失敗
        """
        try:
            if verbose:
                print("🔌 OpenAI API接続テスト中...", end='', flush=True)

            # 簡単なテストプロンプトを送信
            test_prompt = "Hello, this is a connection test. Please respond with 'OK'."
            response = self.generate_response(
                prompt=test_prompt,
                model="gpt-3.5-turbo",  # 最も安価なモデルでテスト
                max_tokens=10,
                phase="Connection Test"  # レポートで識別できるようにphaseを設定
            )

            if response:
                if verbose:
                    print(" ✓ 接続成功")
                self.logger.info("OpenAI API connection test: SUCCESS")
                return True
            else:
                if verbose:
                    print(" ✗ 接続失敗")
                self.logger.error("OpenAI API connection test: FAILED (empty response)")
                return False

        except Exception as e:
            if verbose:
                print(f" ✗ 接続失敗: {e}")
            self.logger.error(f"OpenAI API connection test: FAILED - {e}")
            return False

    def get_provider_name(self) -> str:
        """
        プロバイダー名を取得

        Returns:
            str: "openai"
        """
        return "openai"
