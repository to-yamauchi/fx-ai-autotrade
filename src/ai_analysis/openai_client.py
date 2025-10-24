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
- GPT-5シリーズ: gpt-5-nano, gpt-5-mini (Responses API)
- GPT-4シリーズ: gpt-4o, gpt-4o-mini, gpt-4-turbo (Chat Completions API)
- GPT-3.5シリーズ: gpt-3.5-turbo (Chat Completions API)
- o1シリーズ: o1-preview, o1-mini (Chat Completions API)

最新のモデル一覧: https://platform.openai.com/docs/models

【API種別】
- GPT-5: Responses API (client.responses.create)
- GPT-4/3.5/o1: Chat Completions API (client.chat.completions.create)

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

from typing import Optional, Dict
import logging
import time
import json
import re
from openai import OpenAI, InternalServerError, RateLimitError
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
        if not model_name.startswith(('gpt-', 'o1-', 'o3-', 'chatgpt-')):
            # OpenAI以外のモデルが指定された場合
            provider_hint = "Unknown"
            if model_name.startswith('gemini-'):
                provider_hint = "Google Gemini"
            elif model_name.startswith('claude-'):
                provider_hint = "Anthropic Claude"

            raise ValueError(
                f"OpenAIClient cannot use non-OpenAI model: '{model_name}' ({provider_hint})\n"
                f"Please configure an OpenAI model (gpt-*, o1-*, o3-*, chatgpt-*) in your .env file.\n"
                f"Example OpenAI models:\n"
                f"  - gpt-5-nano, gpt-5-mini (Responses API)\n"
                f"  - gpt-4o, gpt-4o-mini (Chat Completions API)\n"
                f"  - o1-preview, o1-mini (Chat Completions API)\n"
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

            # phaseパラメータを取得（トークン使用量記録用）
            phase = kwargs.pop('phase', 'Unknown')

            # GPT-5は Responses API、それ以外は Chat Completions API
            is_gpt5 = actual_model.startswith('gpt-5')

            # ログ出力
            api_type = "Responses API" if is_gpt5 else "Chat Completions API"
            self.logger.debug(
                f"OpenAI {api_type} request: model={actual_model}, "
                f"temperature={temperature if not is_gpt5 else 'N/A'}, "
                f"max_tokens={max_tokens}"
            )

            # API呼び出し（リトライ処理付き）
            max_retries = 3
            retry_delay = 2  # 初回待機時間（秒）

            for attempt in range(max_retries):
                try:
                    if is_gpt5:
                        # GPT-5: Responses API
                        response = self._call_responses_api(
                            model=actual_model,
                            prompt=prompt,
                            max_tokens=max_tokens,
                            **kwargs
                        )
                    else:
                        # GPT-4/3.5/o1: Chat Completions API
                        response = self._call_chat_completions_api(
                            model=actual_model,
                            prompt=prompt,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            **kwargs
                        )
                    break  # 成功したらループを抜ける

                except (InternalServerError, RateLimitError) as e:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)  # 指数バックオフ: 2秒、4秒、8秒
                        self.logger.warning(
                            f"OpenAI API error (attempt {attempt + 1}/{max_retries}): {e}. "
                            f"Retrying in {wait_time} seconds..."
                        )
                        time.sleep(wait_time)
                    else:
                        # 最後のリトライも失敗
                        self.logger.error(f"OpenAI API failed after {max_retries} attempts: {e}")
                        raise

            # レスポンスからテキストを取得
            if is_gpt5:
                text = self._extract_text_from_responses_api(response)
            else:
                text = self._extract_text_from_chat_completions_api(response, max_tokens)

            # トークン使用量を記録
            if hasattr(response, 'usage'):
                from src.ai_analysis.token_usage_tracker import get_token_tracker
                tracker = get_token_tracker()
                tracker.record_usage(
                    phase=phase,
                    provider='openai',
                    model=actual_model,
                    input_tokens=response.usage.prompt_tokens if hasattr(response.usage, 'prompt_tokens') else 0,
                    output_tokens=response.usage.completion_tokens if hasattr(response.usage, 'completion_tokens') else 0
                )

            return text

        except Exception as e:
            self.logger.error(f"OpenAI API error: {e}")
            raise

    def _call_chat_completions_api(
        self,
        model: str,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        """
        Chat Completions APIを呼び出す（GPT-4/3.5/o1用）

        Args:
            model: モデル名
            prompt: プロンプトテキスト
            temperature: 温度パラメータ
            max_tokens: 最大トークン数
            **kwargs: その他のパラメータ

        Returns:
            ChatCompletion: APIレスポンス
        """
        params = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
        }

        # o1シリーズかどうかを判定
        is_o1_model = model.startswith(('o1-', 'o3-'))

        # temperatureの設定（o1シリーズは非対応）
        if temperature is not None and not is_o1_model:
            params["temperature"] = temperature

        # max_tokensの設定（モデルによって使い分け）
        if max_tokens is not None:
            if is_o1_model:
                # o1シリーズは max_completion_tokens を使用
                params["max_completion_tokens"] = max_tokens
            else:
                # GPT-4、GPT-3.5などは max_tokens を使用
                params["max_tokens"] = max_tokens

        # その他のパラメータをマージ
        params.update(kwargs)

        return self.client.chat.completions.create(**params)

    def _call_responses_api(
        self,
        model: str,
        prompt: str,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        """
        Responses APIを呼び出す（GPT-5用）

        Args:
            model: モデル名
            prompt: プロンプトテキスト
            max_tokens: 最大トークン数
            **kwargs: その他のパラメータ

        Returns:
            Response: APIレスポンス
        """
        params = {
            "model": model,
            "input": [
                {"type": "message", "role": "user", "content": prompt}
            ],
            "text": {
                "format": {"type": "text"},
                "verbosity": "medium"
            },
            "reasoning": {
                "effort": "medium",
                "summary": "auto"
            }
        }

        # max_tokensがある場合はトップレベルパラメータとして設定
        if max_tokens is not None:
            params["max_output_tokens"] = max_tokens

        # その他のパラメータをマージ
        params.update(kwargs)

        return self.client.responses.create(**params)

    def _extract_text_from_chat_completions_api(self, response, max_tokens: Optional[int]) -> str:
        """
        Chat Completions APIのレスポンスからテキストを抽出

        Args:
            response: APIレスポンス
            max_tokens: max_tokens設定値

        Returns:
            str: 抽出されたテキスト

        Raises:
            ValueError: レスポンスが空または異常な場合
        """
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

        return text

    def _extract_text_from_responses_api(self, response) -> str:
        """
        Responses APIのレスポンスからテキストを抽出

        Args:
            response: APIレスポンス (openai.types.responses.Response)

        Returns:
            str: 抽出されたテキスト

        Raises:
            ValueError: レスポンスが空または異常な場合
        """
        # デバッグ: レスポンスの詳細情報を確認
        status = response.status if hasattr(response, 'status') else 'N/A'
        self.logger.debug(f"Response status: {status}")
        self.logger.debug(f"Response output length: {len(response.output) if hasattr(response, 'output') and response.output else 0}")

        # incompleteの場合、詳細情報を確認
        if status == 'incomplete' and hasattr(response, 'incomplete_details'):
            details = response.incomplete_details
            reason = details.reason if hasattr(details, 'reason') else 'unknown'
            self.logger.warning(f"Response is incomplete. Reason: {reason}")
            if reason == 'max_output_tokens':
                self.logger.warning("Response was truncated due to max_output_tokens limit. Consider increasing max_tokens.")

        # GPT-5は非同期で実行される可能性があるため、完了を待つ
        if status in ['in_progress', 'queued']:
            self.logger.info(f"Response status is '{status}', waiting for completion...")
            max_wait_attempts = 30  # 最大30回（30秒）待機
            wait_interval = 1  # 1秒間隔

            for attempt in range(max_wait_attempts):
                time.sleep(wait_interval)
                # レスポンスIDを使って最新の状態を取得
                response = self.client.responses.retrieve(response.id)
                status = response.status if hasattr(response, 'status') else 'N/A'
                self.logger.debug(f"Response status (attempt {attempt + 1}): {status}")

                if status == 'completed':
                    self.logger.info(f"Response completed after {attempt + 1} seconds")
                    break
                elif status in ['failed', 'cancelled', 'incomplete']:
                    self.logger.error(f"Response ended with status: {status}")
                    break

            if status != 'completed':
                raise ValueError(f"Response did not complete. Final status: {status}")

        # output配列の内容を確認
        if hasattr(response, 'output') and response.output:
            for i, output_item in enumerate(response.output):
                self.logger.debug(f"Output[{i}] type: {output_item.type if hasattr(output_item, 'type') else 'N/A'}")
                if hasattr(output_item, 'content') and output_item.content:
                    self.logger.debug(f"Output[{i}] content length: {len(output_item.content)}")
                    for j, content_item in enumerate(output_item.content):
                        content_type = content_item.type if hasattr(content_item, 'type') else 'N/A'
                        self.logger.debug(f"Output[{i}] content[{j}] type: {content_type}")
                        if content_type == 'text' and hasattr(content_item, 'text'):
                            self.logger.debug(f"Output[{i}] content[{j}] text length: {len(content_item.text)}")

        # OpenAI SDKのResponseオブジェクトにはoutput_textプロパティがある
        # これがすべてのoutput_textコンテンツを集約したもの
        # ただし、response.outputがNoneの場合、output_textアクセス時にエラーになる
        text = ""

        if not hasattr(response, 'output_text'):
            self.logger.error(f"Response has no 'output_text' property. Type: {type(response)}")
            raise ValueError("OpenAI Responses API returned unexpected response type")

        # output_textにアクセスする前に、outputがNoneでないことを確認
        if hasattr(response, 'output') and response.output is not None:
            try:
                text = response.output_text
            except (TypeError, AttributeError) as e:
                self.logger.warning(f"Failed to access output_text property: {e}")
                text = ""
        else:
            self.logger.warning(f"Response.output is None, cannot access output_text property")

        # output_textが空の場合、代替手段を試す
        if not text:
            self.logger.warning("OpenAI Responses API returned empty output_text")

            # 代替: output配列から直接テキストを取得
            if hasattr(response, 'output') and response.output:
                texts = []
                for output_item in response.output:
                    if hasattr(output_item, 'content') and output_item.content:
                        for content_item in output_item.content:
                            # 'output_text'タイプまたは'text'タイプのコンテンツを探す
                            content_type = content_item.type if hasattr(content_item, 'type') else None
                            if content_type in ['output_text', 'text']:
                                if hasattr(content_item, 'text'):
                                    texts.append(content_item.text)
                                    self.logger.debug(f"Found '{content_type}' type content: {len(content_item.text)} chars")
                            else:
                                self.logger.debug(f"Skipping content type: {content_type}")

                if texts:
                    text = "".join(texts)
                    self.logger.info(f"Extracted text from output.content: {len(text)} chars")
                else:
                    self.logger.warning("No text content found in output.content array")
            else:
                self.logger.error(f"Response output is None or empty. Response ID: {response.id if hasattr(response, 'id') else 'N/A'}")

        if not text:
            # それでも空の場合は詳細なエラー情報を出力
            model_name = response.model if hasattr(response, 'model') else 'Unknown'
            error_msg = f"No text content found in response from model '{model_name}'"

            # レスポンスの詳細情報をログに記録
            if hasattr(response, 'id'):
                error_msg += f"\nResponse ID: {response.id}"
            if hasattr(response, 'status'):
                error_msg += f"\nStatus: {response.status}"

            # outputの状態を確認
            if hasattr(response, 'output'):
                if response.output is None:
                    error_msg += "\noutput: None (no output generated)"
                elif len(response.output) == 0:
                    error_msg += "\noutput: [] (empty array)"
                else:
                    error_msg += f"\noutput: {len(response.output)} items, but no text content found"

            self.logger.error(error_msg)

            # gpt-5-nanoの場合は特別なヒントを追加
            if model_name and 'gpt-5-nano' in model_name:
                self.logger.warning(
                    "gpt-5-nano may have different behavior or requirements. "
                    "Consider using gpt-5-mini or checking model availability."
                )

            raise ValueError(f"OpenAI Responses API returned no text content for model '{model_name}'")

        self.logger.debug(
            f"OpenAI Responses API response received: "
            f"length={len(text)} chars"
        )

        return text

    def test_connection(self, verbose: bool = False, model: Optional[str] = None) -> bool:
        """
        OpenAI APIへの接続テスト

        Args:
            verbose: 詳細なログを出力するかどうか
            model: テストに使用するモデル名（Noneの場合はデフォルトモデル）

        Returns:
            bool: True=接続成功, False=接続失敗
        """
        try:
            if verbose:
                print("🔌 OpenAI API接続テスト中...", end='', flush=True)

            # モデルが指定されていない場合はデフォルト（最も安価）を使用
            test_model = model if model else "gpt-3.5-turbo"

            # 簡単なテストプロンプトを送信
            # max_tokensは指定しない（モデルのデフォルト動作に任せる）
            # これにより、GPT-5のreasoningが途中で切れる問題を回避
            test_prompt = "Say OK"
            response = self.generate_response(
                prompt=test_prompt,
                model=test_model,
                max_tokens=None,  # デフォルト動作に任せる
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

    def analyze_market(self,
                      market_data: Dict,
                      model: str = 'gpt-4o') -> Dict:
        """
        マーケットデータを分析してトレード判断を行う

        Args:
            market_data: 標準化されたマーケットデータ（DataStandardizerの出力）
            model: 使用するモデル (例: 'gpt-4o', 'periodic_update')

        Returns:
            AI判断結果の辞書
            {
                'action': 'BUY' | 'SELL' | 'HOLD',
                'confidence': 0-100の数値,
                'reasoning': '判断理由の説明',
                'entry_price': エントリー推奨価格 (optional),
                'stop_loss': SL推奨価格 (optional),
                'take_profit': TP推奨価格 (optional)
            }

        Raises:
            Exception: API呼び出しエラー時（エラーはログに記録し、HOLDを返す）
        """
        try:
            # 分析プロンプトの構築
            prompt = self._build_analysis_prompt(market_data)

            # generate_responseを使用してAI分析を実行
            response = self.generate_response(
                prompt=prompt,
                model=model,
                phase='Market Analysis'
            )

            # レスポンスのパース
            result = self._parse_response(response)

            return result

        except Exception as e:
            # エラー時はHOLDを返す
            self.logger.error(f"AI analysis error: {e}")
            return {
                'action': 'HOLD',
                'confidence': 0,
                'reasoning': f'Error occurred during AI analysis: {str(e)}'
            }

    def _build_analysis_prompt(self, market_data: Dict) -> str:
        """
        分析プロンプトを構築する

        Args:
            market_data: 標準化されたマーケットデータ

        Returns:
            分析プロンプト文字列
        """
        # マーケットデータをJSON文字列に変換
        market_data_json = json.dumps(market_data, indent=2, ensure_ascii=False)

        prompt = f"""あなたはプロのFXスキャルピングトレーダーです。10-30pipsの小さな利益を積極的に狙います。以下のマーケットデータを分析し、トレード判断を行ってください。

## マーケットデータ
{market_data_json}

## トレーディングスタイル
- **スキャルピング重視**: 10-30pipsの小さな値幅でも積極的にエントリー
- **M15（15分足）を最重視**: エントリータイミングはM15を中心に判断
- **積極的な姿勢**: レンジ相場でも反発・押し目を狙う
- **迅速な判断**: 明確なトレンドがなくても、短期的な方向性があればエントリー

## 分析指示
1. **M15（15分足）の詳細分析（最重要）**
   - 直近の価格アクション（上昇/下降の勢い）
   - EMAとの位置関係（クロスやタッチ）
   - RSIの状態（30以下で買い、70以上で売りシグナル）
   - ボリンジャーバンドの位置（バンドタッチは反転シグナル）

2. **短期トレンドの確認（H1）**
   - M15のトレードが短期トレンドに沿っているか確認
   - 逆張りの場合は確信度を下げる

3. **中長期トレンドの確認（H4、D1）**
   - 長期トレンドと同じ方向なら確信度を上げる
   - 逆方向でもM15が明確ならエントリー可（確信度は下げる）

4. **テクニカル指標の総合判断**
   - RSI: 30以下=買いチャンス、70以上=売りチャンス、40-60=トレンドフォロー
   - MACD: ヒストグラムの方向転換をエントリーシグナルとして重視
   - ボリンジャー: バンドの上限/下限タッチは反転エントリーチャンス
   - EMA: 価格がEMAを上抜け/下抜けした直後はエントリーチャンス

## 判断基準（スキャルピング重視）
- **BUY条件**:
  - M15で上昇の勢いがある
  - RSI < 70（買われすぎでなければOK）
  - 価格がEMA上にある、またはEMAを上抜けた直後
  - ボリンジャー下限付近からの反発
  - MACDヒストグラムがプラスに転じた

- **SELL条件**:
  - M15で下降の勢いがある
  - RSI > 30（売られすぎでなければOK）
  - 価格がEMA下にある、またはEMAを下抜けた直後
  - ボリンジャー上限付近からの反落
  - MACDヒストグラムがマイナスに転じた

- **HOLD条件（最小限に）**:
  - すべての指標が完全に中立（RSI 45-55、MACD 0付近、EMAフラット）
  - 重要な経済指標発表の直前

## 重要事項
- **HOLDは最後の選択肢**: 少しでもエントリーチャンスがあればBUY/SELLを選択
- **小さな利益を狙う**: 10pips程度の小さな動きでも積極的にエントリー
- **確信度は50以上を目標**: 完璧な状況を待たず、60-70%の確信度でもエントリー
- **ストップは狭く**: 10-15pips程度のタイトなストップを推奨
- **リスクリワード**: 最低1:1、理想は1:1.5以上

## 出力フォーマット
以下のJSON形式で回答してください（他のテキストは含めないでください）:

```json
{{
  "action": "BUY" or "SELL" or "HOLD",
  "confidence": 50-85の範囲を目安（完璧でなくてもエントリー）,
  "reasoning": "判断理由（M15の状況を中心に、エントリー根拠を明確に）",
  "entry_price": エントリー推奨価格（現在価格付近）,
  "stop_loss": ストップロス推奨価格（10-15pips）,
  "take_profit": テイクプロフィット推奨価格（15-30pips、リスクリワード1:1.5以上）
}}
```
"""
        return prompt

    def _parse_response(self, response_text: str) -> Dict:
        """
        AIレスポンスをパースする

        Args:
            response_text: AIからの応答テキスト

        Returns:
            パースされた判断結果の辞書
        """
        try:
            # JSONブロック（```json ... ```）を抽出
            json_match = re.search(
                r'```json\s*(\{.*?\})\s*```',
                response_text,
                re.DOTALL
            )

            if json_match:
                json_text = json_match.group(1)
            else:
                # JSONブロックがない場合、{ } で囲まれた部分を探す
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_text = json_match.group(0)
                else:
                    # JSON形式が見つからない場合
                    raise ValueError("No JSON format found in response")

            # JSONをパース
            result = json.loads(json_text)

            # 必須フィールドの検証
            if 'action' not in result:
                raise ValueError("'action' field is missing in response")

            if result['action'] not in ['BUY', 'SELL', 'HOLD']:
                raise ValueError(f"Invalid action: {result['action']}")

            # confidenceのデフォルト値
            if 'confidence' not in result:
                result['confidence'] = 50

            # reasoningのデフォルト値
            if 'reasoning' not in result:
                result['reasoning'] = 'No reasoning provided'

            return result

        except (json.JSONDecodeError, ValueError) as e:
            # パース失敗時はデフォルト値を返す
            self.logger.error(f"Failed to parse AI response: {e}")
            self.logger.debug(f"Response text: {response_text}")

            return {
                'action': 'HOLD',
                'confidence': 0,
                'reasoning': f'Failed to parse AI response: {str(e)}'
            }
