"""
========================================
Gemini APIクライアントモジュール
========================================

ファイル名: gemini_client.py
パス: src/ai_analysis/gemini_client.py

【概要】
Google Gemini APIと連携し、マーケットデータを分析してトレード判断を行う
モジュールです。3つのモデル(Pro/Flash/Flash-8B)をサポートし、
柔軟にモデルを切り替えることができます。

【主な機能】
1. Gemini API連携
2. マーケットデータ分析プロンプト構築
3. AI判断結果のパース
4. エラーハンドリング

【使用モデル】
モデル名は.envファイルで設定可能:
- GEMINI_MODEL_DAILY_ANALYSIS: デイリー分析用（Phase 1, 2, 5）（デフォルト: gemini-2.5-flash）
- GEMINI_MODEL_PERIODIC_UPDATE: 定期更新用（Phase 3）（デフォルト: gemini-2.5-flash）
- GEMINI_MODEL_POSITION_MONITOR: ポジション監視用（Phase 4）（デフォルト: gemini-2.5-flash）

最新のモデル一覧: https://ai.google.dev/gemini-api/docs/models

【出力形式】
{
    "action": "BUY/SELL/HOLD",
    "confidence": 0-100,
    "reasoning": "判断理由",
    "entry_price": エントリー価格,
    "stop_loss": SL価格,
    "take_profit": TP価格
}

【作成日】2025-10-22
"""

import google.generativeai as genai
from typing import Dict, Optional
import os
import logging
import json
import re
from src.ai_analysis.base_llm_client import BaseLLMClient


class GeminiClient(BaseLLMClient):
    """
    Gemini APIクライアントクラス

    マーケットデータを分析し、トレード判断を行うためのクライアント。
    複数のモデルをサポートし、モデル選択により精度と速度のバランスを調整可能。
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        GeminiClientの初期化

        Args:
            api_key: Gemini APIキー（省略時は環境変数から取得）

        Raises:
            ValueError: GEMINI_API_KEYが設定されていない場合
        """
        from src.utils.config import get_config

        # .envから設定を強制的に読み込み
        self.config = get_config()

        # APIキーの取得（引数優先、次に環境変数）
        if api_key is None:
            api_key = self.config.gemini_api_key

        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")

        # 基底クラスの初期化
        super().__init__(api_key)

        # Gemini APIの設定
        genai.configure(api_key=api_key)

        self.logger.info("✓ Gemini API initialized")

    def analyze_market(self,
                      market_data: Dict,
                      model: str = 'flash') -> Dict:
        """
        マーケットデータを分析してトレード判断を行う

        Args:
            market_data: 標準化されたマーケットデータ（DataStandardizerの出力）
            model: 使用するモデル ('pro' / 'flash' / 'flash-lite')

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
        # 分析プロンプトの構築
        prompt = self._build_analysis_prompt(market_data)

        # モデルの選択と実際のモデル名を取得
        selected_model, actual_model_name = self._select_model(model)

        try:
            # AI分析の実行（ログは最小限に）
            response = selected_model.generate_content(prompt)

            # レスポンスのパース
            result = self._parse_response(response.text)

            return result

        except Exception as e:
            # エラー時はHOLDを返す
            self.logger.error(f"❌ AI analysis error: {e}")
            return {
                'action': 'HOLD',
                'confidence': 0,
                'reasoning': f'Error occurred during AI analysis: {str(e)}'
            }

    def generate_response(
        self,
        prompt: str,
        model: str = 'flash',
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        汎用的なプロンプトに対してAI応答を生成する

        Args:
            prompt: AIに送信するプロンプト
            model: 使用するモデル ('pro' / 'flash' / 'flash-8b')
            temperature: 応答のランダム性（0.0-1.0）、Noneの場合は.envの設定を使用
            max_tokens: 最大トークン数、Noneの場合は.envの設定を使用

        Returns:
            AIの応答テキスト

        Raises:
            Exception: API呼び出しエラー時
        """
        # モデルの選択と実際のモデル名を取得
        selected_model, actual_model_name = self._select_model(model)

        # パラメータのデフォルト値を設定から取得
        if temperature is None:
            if model == 'pro' or model == 'daily_analysis':
                temperature = self.config.ai_temperature_daily_analysis
            elif model == 'flash-8b' or model == 'flash-lite' or model == 'position_monitor':
                temperature = self.config.ai_temperature_position_monitor
            else:  # flash or periodic_update
                temperature = self.config.ai_temperature_periodic_update

        if max_tokens is None:
            if model == 'pro' or model == 'daily_analysis':
                max_tokens = self.config.ai_max_tokens_daily_analysis
            elif model == 'flash-8b' or model == 'flash-lite' or model == 'position_monitor':
                max_tokens = self.config.ai_max_tokens_position_monitor
            else:  # flash or periodic_update
                max_tokens = self.config.ai_max_tokens_periodic_update

        try:
            # 生成設定
            generation_config = {
                'temperature': temperature,
            }
            # max_tokensが指定されている場合のみ追加（Noneの場合はモデルのデフォルトを使用）
            if max_tokens is not None:
                generation_config['max_output_tokens'] = max_tokens

            # AI応答の生成
            response = selected_model.generate_content(
                prompt,
                generation_config=generation_config
            )

            # finish_reasonをチェック
            if not response.parts:
                # responseにpartsがない場合はfinish_reasonを確認
                finish_reason = response.candidates[0].finish_reason if response.candidates else None

                if finish_reason == 2:  # MAX_TOKENS
                    error_msg = (
                        "AI応答が最大トークン数に達しました。"
                        f"現在の設定: {max_tokens} tokens。"
                        ".envのmax_tokens設定を増やすか、プロンプトを短くしてください。"
                    )
                    self.logger.error(f"❌ {error_msg}")
                    raise ValueError(error_msg)
                elif finish_reason == 3:  # SAFETY
                    error_msg = (
                        "AI応答が安全性フィルタによりブロックされました。"
                        "プロンプトの内容を確認してください。"
                    )
                    self.logger.error(f"❌ {error_msg}")
                    raise ValueError(error_msg)
                else:
                    error_msg = f"AI応答が生成されませんでした。finish_reason: {finish_reason}"
                    self.logger.error(f"❌ {error_msg}")
                    raise ValueError(error_msg)

            # トークン使用量を記録
            if hasattr(response, 'usage_metadata'):
                from src.ai_analysis.token_usage_tracker import get_token_tracker
                tracker = get_token_tracker()
                input_tokens = response.usage_metadata.prompt_token_count
                output_tokens = response.usage_metadata.candidates_token_count
                tracker.record_usage(
                    phase=kwargs.get('phase', 'Unknown'),
                    provider='gemini',
                    model=actual_model_name,  # 実際に使用されたモデル名を記録
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )

            return response.text

        except Exception as e:
            self.logger.error(f"❌ Generate response error: {e}")
            raise

    def _build_analysis_prompt(self, market_data: Dict) -> str:
        """
        分析プロンプトを構築する

        マーケットデータをJSON形式で整形し、AIに分析を依頼する
        プロンプトを生成します。

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
  "action": "BUY/SELL/HOLD",
  "confidence": 0-100の数値,
  "reasoning": "判断理由を詳しく説明（各時間足の状況、テクニカル指標の状態、総合判断の根拠）",
  "entry_price": エントリー推奨価格（actionがHOLD以外の場合）,
  "stop_loss": ストップロス推奨価格（actionがHOLD以外の場合）,
  "take_profit": テイクプロフィット推奨価格（actionがHOLD以外の場合）
}}
```

注意: 必ずJSON形式のみで回答してください。説明文は"reasoning"フィールドに含めてください。
"""
        return prompt

    def _select_model(self, model: str):
        """
        使用するモデルを選択する

        Args:
            model: モデル名（完全なモデル名 例: gemini-2.5-flash）
                または短縮名（後方互換性のため）:
                - 'pro' or 'daily_analysis': gemini-2.5-pro相当
                - 'flash' or 'periodic_update': gemini-2.5-flash相当
                - 'flash-lite', 'flash-8b' or 'position_monitor': gemini-2.5-flash相当

        Returns:
            Tuple[GenerativeModel, str]: (選択されたGenerativeModelオブジェクト, 実際のモデル名)
        """
        # 短縮名から完全なモデル名へのマッピング（後方互換性）
        model_name_mapping = {
            'pro': 'gemini-2.5-pro',
            'daily_analysis': 'gemini-2.5-pro',
            'flash': 'gemini-2.5-flash',
            'periodic_update': 'gemini-2.5-flash',
            'flash-lite': 'gemini-2.5-flash',
            'flash-8b': 'gemini-2.5-flash',
            'position_monitor': 'gemini-2.5-flash',
        }

        # 短縮名の場合は完全なモデル名に変換
        if model in model_name_mapping:
            model_name = model_name_mapping[model]
            self.logger.debug(f"Model shorthand '{model}' mapped to '{model_name}'")
        else:
            # すでに完全なモデル名（例: gemini-2.5-flash, claude-sonnet-4-5など）
            model_name = model

        # GenerativeModelオブジェクトを生成して、モデル名も返す
        return genai.GenerativeModel(model_name), model_name

    def _parse_response(self, response_text: str) -> Dict:
        """
        AIレスポンスをパースする

        AIの応答からJSON部分を抽出し、辞書に変換します。
        パースに失敗した場合はデフォルト値（HOLD）を返します。

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

    def test_connection(self, verbose: bool = False) -> bool:
        """
        Gemini APIへの接続テスト

        簡単なプロンプトを送信してAPIが正常に動作するか確認します。
        軽量なテストモデル（gemini-2.0-flash-lite）を使用してテストします。

        Args:
            verbose: 詳細なログを出力するかどうか

        Returns:
            True: 接続成功, False: 接続失敗
        """
        try:
            if verbose:
                print("🔌 Gemini API接続テスト中...", end='', flush=True)

            test_prompt = "Hello, this is a connection test. Please respond with 'OK'."
            # generate_responseを使用してトークン使用量を記録
            response = self.generate_response(
                prompt=test_prompt,
                model='gemini-2.0-flash-lite',
                max_tokens=10,
                phase="Connection Test"  # レポートで識別できるようにphaseを設定
            )

            if response:
                if verbose:
                    print(" ✓ 接続成功")
                return True
            else:
                if verbose:
                    print(" ❌ 失敗（空のレスポンス）")
                self.logger.error("Gemini API connection test failed: empty response")
                return False

        except Exception as e:
            if verbose:
                print(f" ❌ 失敗")
                print(f"   エラー: {e}")
            self.logger.error(f"Gemini API connection test failed: {e}")
            return False

    def get_provider_name(self) -> str:
        """
        プロバイダー名を取得

        Returns:
            str: "gemini"
        """
        return "gemini"


# モジュールのエクスポート
__all__ = ['GeminiClient']
