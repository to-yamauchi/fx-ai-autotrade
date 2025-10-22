"""
========================================
AI分析モジュール テストモジュール
========================================

ファイル名: test_ai_analyzer.py
パス: tests/test_ai_analyzer.py

【概要】
GeminiClientとAIAnalyzerクラスの機能をテストするユニットテストモジュールです。

【テスト項目】
1. GeminiClient初期化テスト
2. プロンプト構築テスト
3. レスポンスパーステスト
4. モデル選択テスト
5. エラーハンドリングテスト
6. 統合テスト（モックを使用）

【テスト実行方法】
個別実行:
    pytest tests/test_ai_analyzer.py -v

カバレッジ付き:
    pytest tests/test_ai_analyzer.py --cov=src.ai_analysis -v

【前提条件】
- GEMINI_API_KEYは環境変数またはモックで設定
- データベースはモックを使用（実DBは不要）

【作成日】2025-10-22
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import json

from src.ai_analysis.gemini_client import GeminiClient
from src.ai_analysis.ai_analyzer import AIAnalyzer


class TestGeminiClient:
    """GeminiClientクラスのテストケース"""

    @pytest.fixture
    def mock_env(self):
        """環境変数をモック"""
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test_api_key'}):
            yield

    @pytest.fixture
    def sample_market_data(self):
        """テスト用のサンプルマーケットデータ"""
        return {
            'timestamp': '2024-09-01T10:00:00',
            'symbol': 'USDJPY',
            'timeframes': {
                'H1': {
                    'current': {
                        'open': 145.120,
                        'high': 145.150,
                        'low': 145.100,
                        'close': 145.140,
                        'volume': 1000
                    },
                    'change_pct': 0.15
                }
            },
            'technical_indicators': {
                'ema': {
                    'short': 145.130,
                    'long': 145.100,
                    'trend': 'up'
                },
                'rsi': {
                    'value': 55.0,
                    'condition': 'neutral'
                }
            }
        }

    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_client_initialization(self, mock_model, mock_configure, mock_env):
        """
        GeminiClientの初期化テスト

        【確認内容】
        - インスタンスが正しく生成されるか
        - APIキーが設定されるか
        - 3つのモデルが初期化されるか
        """
        client = GeminiClient()

        assert client.api_key == 'test_api_key'
        assert client.model_pro is not None
        assert client.model_flash is not None
        assert client.model_flash_lite is not None
        mock_configure.assert_called_once_with(api_key='test_api_key')

    def test_client_initialization_no_api_key(self):
        """
        APIキーが設定されていない場合のテスト

        【確認内容】
        - ValueErrorが発生するか
        """
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                GeminiClient()

            assert 'GEMINI_API_KEY' in str(exc_info.value)

    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_build_analysis_prompt(self, mock_model, mock_configure, mock_env, sample_market_data):
        """
        分析プロンプト構築テスト

        【確認内容】
        - プロンプトが正しく構築されるか
        - マーケットデータがJSON形式で含まれるか
        """
        client = GeminiClient()
        prompt = client._build_analysis_prompt(sample_market_data)

        assert isinstance(prompt, str)
        assert 'USDJPY' in prompt
        assert 'BUY/SELL/HOLD' in prompt
        assert 'technical_indicators' in prompt.lower()

    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_parse_response_valid_json(self, mock_model, mock_configure, mock_env):
        """
        正常なJSONレスポンスのパーステスト

        【確認内容】
        - 正しいJSON形式がパースされるか
        - 必須フィールドが含まれるか
        """
        client = GeminiClient()

        valid_response = """
        ```json
        {
            "action": "BUY",
            "confidence": 75,
            "reasoning": "Strong uptrend detected"
        }
        ```
        """

        result = client._parse_response(valid_response)

        assert result['action'] == 'BUY'
        assert result['confidence'] == 75
        assert 'reasoning' in result

    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_parse_response_invalid_action(self, mock_model, mock_configure, mock_env):
        """
        無効なactionのレスポンステスト

        【確認内容】
        - 無効なactionが処理されるか
        - HOLDにフォールバックするか
        """
        client = GeminiClient()

        invalid_response = """
        ```json
        {
            "action": "INVALID_ACTION",
            "confidence": 50
        }
        ```
        """

        result = client._parse_response(invalid_response)

        assert result['action'] == 'HOLD'
        assert result['confidence'] == 0

    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_parse_response_no_json(self, mock_model, mock_configure, mock_env):
        """
        JSON形式が含まれないレスポンステスト

        【確認内容】
        - JSON形式がない場合にエラーハンドリングされるか
        - HOLDが返されるか
        """
        client = GeminiClient()

        no_json_response = "This is just a plain text response without any JSON."

        result = client._parse_response(no_json_response)

        assert result['action'] == 'HOLD'
        assert result['confidence'] == 0
        assert 'Failed to parse' in result['reasoning']

    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_select_model(self, mock_model, mock_configure, mock_env):
        """
        モデル選択テスト

        【確認内容】
        - 各モデルが正しく選択されるか
        - 不明なモデル名の場合はflashが選択されるか
        """
        client = GeminiClient()

        # 各モデルの選択確認
        assert client._select_model('pro') == client.model_pro
        assert client._select_model('flash') == client.model_flash
        assert client._select_model('flash-lite') == client.model_flash_lite

        # 不明なモデル名の場合
        assert client._select_model('unknown') == client.model_flash

    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_analyze_market_success(self, mock_model_class, mock_configure, mock_env, sample_market_data):
        """
        マーケット分析成功テスト

        【確認内容】
        - analyze_marketが正常に動作するか
        - 正しい結果が返されるか
        """
        # モックレスポンスの設定
        mock_response = Mock()
        mock_response.text = """
        ```json
        {
            "action": "BUY",
            "confidence": 80,
            "reasoning": "Strong uptrend"
        }
        ```
        """

        mock_model_instance = Mock()
        mock_model_instance.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model_instance

        client = GeminiClient()
        client.model_flash = mock_model_instance

        result = client.analyze_market(sample_market_data, model='flash')

        assert result['action'] == 'BUY'
        assert result['confidence'] == 80
        mock_model_instance.generate_content.assert_called_once()

    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_analyze_market_api_error(self, mock_model_class, mock_configure, mock_env, sample_market_data):
        """
        API呼び出しエラー時のテスト

        【確認内容】
        - API呼び出しエラー時にHOLDが返されるか
        - エラーメッセージが含まれるか
        """
        # エラーを発生させるモックの設定
        mock_model_instance = Mock()
        mock_model_instance.generate_content.side_effect = Exception("API Error")
        mock_model_class.return_value = mock_model_instance

        client = GeminiClient()
        client.model_flash = mock_model_instance

        result = client.analyze_market(sample_market_data, model='flash')

        assert result['action'] == 'HOLD'
        assert result['confidence'] == 0
        assert 'Error' in result['reasoning']


class TestAIAnalyzer:
    """AIAnalyzerクラスのテストケース"""

    @pytest.fixture
    def mock_env_full(self):
        """完全な環境変数をモック"""
        with patch.dict(os.environ, {
            'GEMINI_API_KEY': 'test_api_key',
            'DB_HOST': 'localhost',
            'DB_PORT': '5432',
            'DB_NAME': 'test_db',
            'DB_USER': 'test_user',
            'DB_PASSWORD': 'test_password'
        }):
            yield

    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    @patch('src.ai_analysis.ai_analyzer.TickDataLoader')
    @patch('src.ai_analysis.ai_analyzer.TimeframeConverter')
    @patch('src.ai_analysis.ai_analyzer.TechnicalIndicators')
    @patch('src.ai_analysis.ai_analyzer.DataStandardizer')
    def test_analyzer_initialization(
        self,
        mock_standardizer,
        mock_indicators,
        mock_converter,
        mock_loader,
        mock_model,
        mock_configure,
        mock_env_full
    ):
        """
        AIAnalyzerの初期化テスト

        【確認内容】
        - インスタンスが正しく生成されるか
        - 各コンポーネントが初期化されるか
        """
        analyzer = AIAnalyzer(symbol='USDJPY', model='flash')

        assert analyzer.symbol == 'USDJPY'
        assert analyzer.model == 'flash'
        assert analyzer.tick_loader is not None
        assert analyzer.timeframe_converter is not None
        assert analyzer.technical_indicators is not None
        assert analyzer.data_standardizer is not None
        assert analyzer.gemini_client is not None

    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    @patch('src.ai_analysis.ai_analyzer.psycopg2.connect')
    def test_create_error_result(self, mock_connect, mock_model, mock_configure, mock_env_full):
        """
        エラー結果作成テスト

        【確認内容】
        - エラー結果が正しく作成されるか
        - 必須フィールドが含まれるか
        """
        analyzer = AIAnalyzer()
        result = analyzer._create_error_result("Test error")

        assert result['action'] == 'HOLD'
        assert result['confidence'] == 0
        assert 'Test error' in result['reasoning']
        assert 'timestamp' in result
        assert 'symbol' in result

    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    @patch('src.ai_analysis.ai_analyzer.psycopg2.connect')
    def test_save_to_database(self, mock_connect, mock_model, mock_configure, mock_env_full):
        """
        データベース保存テスト

        【確認内容】
        - DB保存が正常に実行されるか
        - 正しいデータが保存されるか
        """
        # DBモックの設定
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        analyzer = AIAnalyzer()

        ai_result = {
            'action': 'BUY',
            'confidence': 75,
            'reasoning': 'Test reasoning',
            'symbol': 'USDJPY'
        }

        market_data = {'test': 'data'}

        result = analyzer._save_to_database(ai_result, market_data)

        assert result is True
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()


# テストの実行統計情報（参考）
def test_suite_info():
    """
    テストスイート情報

    このテストモジュールは以下をカバーします:
    - GeminiClient: 9ケース
    - AIAnalyzer: 3ケース
    合計: 12ケース
    """
    pass


if __name__ == "__main__":
    """
    直接実行時のテストランナー

    実行方法:
        python -m pytest tests/test_ai_analyzer.py -v
    """
    pytest.main([__file__, "-v"])
