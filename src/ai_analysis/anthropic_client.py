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

from typing import Optional, Dict
import logging
import time
import json
import re
from anthropic import Anthropic, InternalServerError, RateLimitError
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

    def _select_model(self, model: str) -> str:
        """
        使用するモデルを選択する

        Args:
            model: モデル名（完全なモデル名 例: claude-sonnet-4-5）
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

        # モデル名のバリデーション - AnthropicClient はClaudeモデルのみ対応
        if not model_name.startswith('claude-'):
            # Claude以外のモデルが指定された場合
            provider_hint = "Unknown"
            if model_name.startswith('gemini-'):
                provider_hint = "Google Gemini"
            elif model_name.startswith(('gpt-', 'o1-', 'chatgpt-')):
                provider_hint = "OpenAI"

            raise ValueError(
                f"AnthropicClient cannot use non-Claude model: '{model_name}' ({provider_hint})\n"
                f"Please configure a Claude model (claude-*) in your .env file.\n"
                f"Example Claude models:\n"
                f"  - claude-sonnet-4-5-20250929\n"
                f"  - claude-3-5-haiku-20241022\n"
                f"  - claude-opus-4\n"
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
        Anthropic APIからレスポンスを生成

        Args:
            prompt: プロンプトテキスト
            model: モデル名（例: claude-sonnet-4-5, claude-haiku-4）
                  またはPhase名（例: daily_analysis, periodic_update）
            temperature: 温度パラメータ（0.0-1.0、デフォルト: 1.0）
            max_tokens: 最大トークン数（Noneの場合: 4096）
            **kwargs: その他のパラメータ（top_p, top_k, etc.）

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
                # Anthropic APIはmax_tokensが必須
                # Noneの場合は4096（Claude-4の推奨最大値）を使用
                "max_tokens": max_tokens if max_tokens is not None else 4096,
            }

            if temperature is not None:
                params["temperature"] = temperature

            # その他のパラメータをマージ（phase除外）
            phase = kwargs.pop('phase', 'Unknown')
            params.update(kwargs)

            self.logger.debug(
                f"Anthropic API request: model={actual_model}, "
                f"temperature={temperature}, max_tokens={max_tokens}"
            )

            # API呼び出し（リトライ処理付き）
            max_retries = 3
            retry_delay = 2  # 初回待機時間（秒）

            for attempt in range(max_retries):
                try:
                    response = self.client.messages.create(**params)
                    break  # 成功したらループを抜ける

                except (InternalServerError, RateLimitError) as e:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)  # 指数バックオフ: 2秒、4秒、8秒
                        self.logger.warning(
                            f"Anthropic API error (attempt {attempt + 1}/{max_retries}): {e}. "
                            f"Retrying in {wait_time} seconds..."
                        )
                        time.sleep(wait_time)
                    else:
                        # 最後のリトライも失敗
                        self.logger.error(f"Anthropic API failed after {max_retries} attempts: {e}")
                        raise

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

            # トークン使用量を記録
            if hasattr(response, 'usage'):
                from src.ai_analysis.token_usage_tracker import get_token_tracker
                tracker = get_token_tracker()
                tracker.record_usage(
                    phase=phase,
                    provider='anthropic',
                    model=actual_model,
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens
                )

            return text

        except Exception as e:
            self.logger.error(f"Anthropic API error: {e}")
            raise

    def test_connection(self, verbose: bool = False, model: Optional[str] = None) -> bool:
        """
        Anthropic APIへの接続テスト

        Args:
            verbose: 詳細なログを出力するかどうか
            model: テストに使用するモデル名（Noneの場合はデフォルトモデル）

        Returns:
            bool: True=接続成功, False=接続失敗
        """
        try:
            if verbose:
                print("🔌 Anthropic API接続テスト中...", end='', flush=True)

            # モデルが指定されていない場合はデフォルト（最も安価で高速）を使用
            test_model = model if model else "claude-3-5-haiku-20241022"

            # 簡単なテストプロンプトを送信
            test_prompt = "Hello, this is a connection test. Please respond with 'OK'."
            response = self.generate_response(
                prompt=test_prompt,
                model=test_model,
                max_tokens=10,
                phase="Connection Test"  # レポートで識別できるようにphaseを設定
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

    def analyze_market(self,
                      market_data: Dict,
                      model: str = 'claude-sonnet-4-5') -> Dict:
        """
        マーケットデータを分析してトレード判断を行う

        Args:
            market_data: 標準化されたマーケットデータ（DataStandardizerの出力）
            model: 使用するモデル (例: 'claude-sonnet-4-5', 'daily_analysis')

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

        prompt = f"""あなたはプロのFXトレーダーです。以下のマーケットデータを分析し、トレード判断を行ってください。

## マーケットデータ
{market_data_json}

## 分析指示
1. **各時間足のトレンド分析**
   - D1（日足）: 長期トレンドを確認
   - H4（4時間足）: 中期トレンドを確認
   - H1（1時間足）: 短期トレンドを確認
   - M15（15分足）: エントリータイミングを確認

2. **テクニカル指標分析**
   - EMA: トレンド方向の確認（短期EMAと長期EMAの関係）
   - RSI: 買われすぎ/売られすぎの判断
   - MACD: モメンタムとトレンド転換の確認
   - Bollinger Bands: ボラティリティと価格位置の確認
   - ATR: 現在のボラティリティレベル

3. **サポート・レジスタンス**
   - 重要な価格レベルを考慮
   - ブレイクアウトの可能性を評価

4. **総合判断**
   - 上記の分析を総合し、BUY/SELL/HOLDのいずれかを選択
   - 信頼度（0-100）を数値で示す
   - 判断理由を明確に説明

## 判断基準
- **BUY**: 上昇トレンドが明確で、エントリーに適した状況
- **SELL**: 下降トレンドが明確で、エントリーに適した状況
- **HOLD**: トレンドが不明確、またはエントリーに不適切な状況

## 重要事項
- 複数の時間足が同じ方向を示している場合、信頼度を高くする
- テクニカル指標が矛盾している場合は、慎重にHOLDを選択
- ボラティリティが高すぎる/低すぎる場合は考慮に入れる

## 出力フォーマット
以下のJSON形式で回答してください（他のテキストは含めないでください）:

```json
{{
  "action": "BUY" or "SELL" or "HOLD",
  "confidence": 0-100の数値,
  "reasoning": "判断理由の詳細な説明",
  "entry_price": 推奨エントリー価格（optional）,
  "stop_loss": 推奨SL価格（optional）,
  "take_profit": 推奨TP価格（optional）
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
