# FX自動トレードシステム - テスト戦略

## ドキュメント情報
- **作成日**: 2025-10-21
- **バージョン**: 1.0
- **種別**: テスト設計書
- **対象読者**: 開発者、QA担当者

---

## 目次
1. [テスト戦略概要](#1-テスト戦略概要)
2. [ユニットテスト](#2-ユニットテスト)
3. [統合テスト](#3-統合テスト)
4. [エンドツーエンドテスト](#4-エンドツーエンドテスト)
5. [パフォーマンステスト](#5-パフォーマンステスト)
6. [テストデータ管理](#6-テストデータ管理)
7. [CI/CD統合](#7-cicd統合)

---

## 1. テスト戦略概要

### 1.1 テストピラミッド

```
         /\
        /  \  E2E (少数)
       /----\
      /      \ 統合テスト (中程度)
     /--------\
    /          \ ユニットテスト (多数)
   /------------\
```

**比率の目安**:
- ユニットテスト: 70%
- 統合テスト: 20%
- E2Eテスト: 10%

### 1.2 テストの種類と目的

| テスト種類 | 目的 | 実行頻度 | 実行環境 |
|-----------|------|---------|---------|
| **ユニットテスト** | 個別モジュールの動作確認 | コミット毎 | ローカル/CI |
| **統合テスト** | モジュール間連携確認 | プッシュ毎 | CI |
| **E2Eテスト** | 全体フロー確認 | リリース前 | デモ環境 |
| **パフォーマンステスト** | 速度・負荷確認 | 週次 | 専用環境 |

### 1.3 テストツール

| 用途 | ツール | 備考 |
|------|--------|------|
| **テストフレームワーク** | pytest | Pythonの標準的なテストツール |
| **モック** | pytest-mock | 外部依存のモック化 |
| **カバレッジ** | pytest-cov | コードカバレッジ測定 |
| **パフォーマンス** | pytest-benchmark | 速度計測 |
| **CI/CD** | GitHub Actions | 自動テスト実行 |

---

## 2. ユニットテスト

### 2.1 基本方針

**目的**: 各モジュールの機能を独立してテスト

**原則**:
- 外部依存はモック化
- 1テストケース = 1つの機能
- AAA (Arrange, Act, Assert) パターン
- テストの独立性を保つ

### 2.2 モジュール別テスト戦略

#### 2.2.1 データ処理エンジン

**テストファイル**: `src/modules/data_processing/tests/`

**テストケース例**:

```python
# src/modules/data_processing/tests/test_indicator_calculator.py
import pytest
import pandas as pd
from src.modules.data_processing.indicator_calculator import IndicatorCalculator

class TestIndicatorCalculator:

    @pytest.fixture
    def sample_ohlc_data(self):
        """サンプルOHLCデータ"""
        return pd.DataFrame({
            'open': [100, 101, 102, 103, 104],
            'high': [101, 102, 103, 104, 105],
            'low': [99, 100, 101, 102, 103],
            'close': [100.5, 101.5, 102.5, 103.5, 104.5],
            'volume': [1000, 1100, 1200, 1300, 1400]
        })

    def test_calculate_ema_20(self, sample_ohlc_data):
        """EMA20の計算テスト"""
        # Arrange
        calculator = IndicatorCalculator()

        # Act
        ema = calculator.calculate_ema(sample_ohlc_data, period=20)

        # Assert
        assert ema is not None
        assert len(ema) == len(sample_ohlc_data)
        assert not ema.isna().all()  # すべてがNaNでないこと

    def test_calculate_rsi(self, sample_ohlc_data):
        """RSIの計算テスト"""
        calculator = IndicatorCalculator()
        rsi = calculator.calculate_rsi(sample_ohlc_data)

        assert rsi is not None
        # RSIは0-100の範囲
        assert (rsi.dropna() >= 0).all()
        assert (rsi.dropna() <= 100).all()

    def test_calculate_macd(self, sample_ohlc_data):
        """MACDの計算テスト"""
        calculator = IndicatorCalculator()
        result = calculator.calculate_macd(sample_ohlc_data)

        assert 'macd' in result
        assert 'signal' in result
        assert 'histogram' in result
        assert len(result['macd']) == len(sample_ohlc_data)
```

**MT5データ取得のモック化**:

```python
# src/modules/data_processing/tests/test_data_fetcher.py
import pytest
from unittest.mock import Mock, patch
from src.lib.mt5.data_fetcher import DataFetcher
import pandas as pd

class TestDataFetcher:

    @pytest.fixture
    def mock_mt5_rates(self):
        """MT5 ratesのモックデータ"""
        import numpy as np
        return np.array([
            (1634000000, 100.0, 101.0, 99.0, 100.5, 1000, 0, 0),
            (1634003600, 100.5, 101.5, 100.0, 101.0, 1100, 0, 0),
        ], dtype=[
            ('time', '<i8'), ('open', '<f8'), ('high', '<f8'),
            ('low', '<f8'), ('close', '<f8'), ('tick_volume', '<i8'),
            ('spread', '<i4'), ('real_volume', '<i8')
        ])

    @patch('MetaTrader5.copy_rates_from_pos')
    @patch.object(DataFetcher, 'connector')
    def test_get_rates_success(self, mock_connector, mock_copy_rates, mock_mt5_rates):
        """データ取得成功のテスト"""
        # Arrange
        mock_connector.is_connected.return_value = True
        mock_copy_rates.return_value = mock_mt5_rates
        fetcher = DataFetcher()

        # Act
        df = fetcher.get_rates("USDJPY", 60, 100)

        # Assert
        assert df is not None
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert 'open' in df.columns
        assert 'close' in df.columns

    @patch.object(DataFetcher, 'connector')
    def test_get_rates_not_connected(self, mock_connector):
        """未接続時のテスト"""
        # Arrange
        mock_connector.is_connected.return_value = False
        mock_connector.reconnect.return_value = False
        fetcher = DataFetcher()

        # Act
        df = fetcher.get_rates("USDJPY", 60, 100)

        # Assert
        assert df is None
        mock_connector.reconnect.assert_called_once()
```

**カバレッジ目標**: 80%以上

---

#### 2.2.2 AI分析エンジン

**テストファイル**: `src/modules/ai_analysis/tests/`

**Gemini APIのモック化**:

```python
# src/modules/ai_analysis/tests/test_gemini_client.py
import pytest
from unittest.mock import Mock, patch
from src.modules.ai_analysis.gemini_client import GeminiClient

class TestGeminiClient:

    @pytest.fixture
    def mock_gemini_response(self):
        """Gemini APIレスポンスのモック"""
        mock_response = Mock()
        mock_response.text = '{"daily_bias": "BUY", "confidence": 0.75}'
        mock_response.usage_metadata.prompt_token_count = 1000
        mock_response.usage_metadata.candidates_token_count = 500
        return mock_response

    @patch('google.generativeai.GenerativeModel')
    def test_generate_success(self, mock_model_class, mock_gemini_response):
        """AI生成成功のテスト"""
        # Arrange
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_gemini_response
        mock_model_class.return_value = mock_model

        client = GeminiClient()

        # Act
        result = client.generate("test prompt", model="gemini-2.5-pro")

        # Assert
        assert result is not None
        assert 'text' in result
        assert 'token_count' in result
        assert 'cost' in result
        assert result['token_count']['input'] == 1000
        assert result['token_count']['output'] == 500
```

**プロンプトビルダーのテスト**:

```python
# src/modules/ai_analysis/tests/test_prompt_builder.py
import pytest
from src.modules.ai_analysis.prompt_builder import PromptBuilder

class TestPromptBuilder:

    @pytest.fixture
    def sample_market_data(self):
        """サンプル市場データ"""
        return {
            "metadata": {
                "timestamp": "2025-10-21 08:00:00",
                "symbol": "USDJPY",
                "current_price": 149.650
            },
            "market_structure": {
                "daily_trend": {
                    "direction": "下降",
                    "strength": "中程度"
                }
            },
            "technical_summary": {
                "ema": {
                    "h1_ema20": 149.580,
                    "h1_ema50": 149.720
                }
            }
        }

    def test_build_morning_analysis_prompt(self, sample_market_data):
        """朝の分析プロンプト生成テスト"""
        # Arrange
        builder = PromptBuilder()

        # Act
        prompt = builder.build_morning_analysis_prompt(sample_market_data)

        # Assert
        assert prompt is not None
        assert "USDJPY" in prompt
        assert "149.650" in prompt
        assert "下降" in prompt
```

**カバレッジ目標**: 75%以上

---

#### 2.2.3 ルールエンジン

**テストファイル**: `src/modules/rule_engine/tests/`

**Layer 1緊急停止のテスト**:

```python
# src/modules/rule_engine/tests/test_layer1_emergency.py
import pytest
from unittest.mock import Mock
from src.modules.rule_engine.layer1_emergency import Layer1Emergency

class TestLayer1Emergency:

    @pytest.fixture
    def sample_position(self):
        """サンプルポジション"""
        return {
            'ticket': 123456,
            'symbol': 'USDJPY',
            'direction': 'BUY',
            'entry_price': 149.50,
            'lot_size': 0.1,
            'unrealized_pnl': -200.0
        }

    @pytest.fixture
    def account_balance(self):
        """口座残高"""
        return 10000.0  # $10,000

    def test_check_2_percent_loss_trigger(self, sample_position, account_balance):
        """2%損失検知テスト"""
        # Arrange
        layer1 = Layer1Emergency()
        threshold = account_balance * 0.02  # $200

        # Act
        should_close = layer1.check_2_percent_loss(
            sample_position,
            account_balance
        )

        # Assert
        assert should_close is True  # 損失$200で発動

    def test_check_2_percent_loss_no_trigger(self, account_balance):
        """2%損失未満のテスト"""
        layer1 = Layer1Emergency()
        position = {
            'unrealized_pnl': -100.0  # $100損失（2%未満）
        }

        should_close = layer1.check_2_percent_loss(position, account_balance)
        assert should_close is False

    def test_check_hard_stop_50pips(self):
        """ハードストップ50pipsテスト"""
        layer1 = Layer1Emergency()
        position = {
            'direction': 'BUY',
            'entry_price': 149.50,
        }
        current_price = 149.00  # 50pips逆行

        should_close = layer1.check_hard_stop(position, current_price)
        assert should_close is True
```

**エントリー監視のテスト**:

```python
# src/modules/rule_engine/tests/test_entry_monitor.py
import pytest
from src.modules.rule_engine.entry_monitor import EntryMonitor

class TestEntryMonitor:

    @pytest.fixture
    def sample_rules(self):
        """サンプルルールJSON"""
        return {
            "daily_bias": "BUY",
            "should_trade": True,
            "entry_conditions": {
                "direction": "BUY",
                "price_zone": {"min": 149.50, "max": 149.70},
                "required_signals": [
                    "EMA20 > EMA50",
                    "RSI > 50"
                ],
                "avoid_if": [
                    "スプレッド > 10pips"
                ]
            }
        }

    def test_check_entry_conditions_all_met(self, sample_rules):
        """エントリー条件全達成テスト"""
        monitor = EntryMonitor()

        market_state = {
            'current_price': 149.60,
            'ema20': 149.70,
            'ema50': 149.50,
            'rsi': 60,
            'spread': 5
        }

        should_entry = monitor.check_entry_conditions(sample_rules, market_state)
        assert should_entry is True

    def test_check_entry_conditions_price_out_of_zone(self, sample_rules):
        """価格ゾーン外のテスト"""
        monitor = EntryMonitor()

        market_state = {
            'current_price': 149.80,  # ゾーン外
            'ema20': 149.70,
            'ema50': 149.50,
            'rsi': 60,
            'spread': 5
        }

        should_entry = monitor.check_entry_conditions(sample_rules, market_state)
        assert should_entry is False
```

**カバレッジ目標**: 85%以上（安全装置のため高カバレッジ）

---

### 2.3 ユニットテスト実行

#### 基本実行

```bash
# 全テスト実行
pytest

# 特定モジュールのみ
pytest src/modules/data_processing/tests/

# 特定ファイルのみ
pytest src/modules/data_processing/tests/test_indicator.py

# 特定テストケースのみ
pytest src/modules/data_processing/tests/test_indicator.py::TestIndicatorCalculator::test_calculate_ema_20
```

#### カバレッジ付き実行

```bash
# カバレッジ測定
pytest --cov=src --cov-report=html

# カバレッジレポート確認
open htmlcov/index.html
```

#### 詳細出力

```bash
# 詳細ログ表示
pytest -v

# 標準出力表示
pytest -s

# 失敗時に即停止
pytest -x
```

---

## 3. 統合テスト

### 3.1 基本方針

**目的**: 複数モジュール間の連携をテスト

**対象**:
- データ処理 → AI分析の連携
- AI分析 → ルールエンジンの連携
- ルールエンジン → トレード実行の連携

### 3.2 統合テストケース

#### 3.2.1 データ処理 → AI分析

**テストファイル**: `tests/integration/test_data_to_ai.py`

```python
# tests/integration/test_data_to_ai.py
import pytest
from src.modules.data_processing.processor import DataProcessor
from src.modules.ai_analysis.analyzer import AIAnalyzer

class TestDataToAI:

    @pytest.fixture(scope="class")
    def test_database(self):
        """テスト用データベース"""
        # テストDB作成
        from src.lib.database.connection import db
        # ... テストDB初期化
        yield
        # ... テストDB削除

    def test_data_processing_to_ai_analysis(self, test_database):
        """データ処理からAI分析までのフロー"""
        # Arrange
        processor = DataProcessor()
        analyzer = AIAnalyzer()

        # Act
        # 1. データ処理実行
        market_data = processor.process("USDJPY")
        assert market_data is not None

        # 2. データをファイルに保存
        data_file = processor.save_to_file(market_data)
        assert data_file.exists()

        # 3. AI分析実行
        rules = analyzer.analyze_morning(data_file)
        assert rules is not None
        assert 'daily_bias' in rules
        assert 'entry_conditions' in rules
```

#### 3.2.2 AI分析 → ルールエンジン

**テストファイル**: `tests/integration/test_ai_to_rule_engine.py`

```python
# tests/integration/test_ai_to_rule_engine.py
import pytest
from src.modules.ai_analysis.analyzer import AIAnalyzer
from src.modules.rule_engine.engine import RuleEngine

class TestAIToRuleEngine:

    def test_ai_rules_to_entry_check(self):
        """AI生成ルールからエントリーチェックまで"""
        # Arrange
        analyzer = AIAnalyzer()
        rule_engine = RuleEngine()

        # Act
        # 1. AI分析でルール生成
        rules = analyzer.analyze_morning("sample_market_data.json")

        # 2. ルールエンジンに読み込み
        rule_engine.load_rules(rules)

        # 3. エントリー条件チェック
        should_entry = rule_engine.check_entry_conditions({
            'current_price': 149.60,
            'ema20': 149.70,
            'ema50': 149.50,
            'rsi': 60
        })

        # Assert
        assert isinstance(should_entry, bool)
```

### 3.3 統合テスト実行

```bash
# 統合テストのみ実行
pytest tests/integration/

# マーカー指定
pytest -m integration
```

---

## 4. エンドツーエンドテスト

### 4.1 基本方針

**目的**: システム全体のフローをテスト

**環境**: デモ口座

**実行頻度**: リリース前、週次

### 4.2 E2Eテストシナリオ

#### シナリオ1: 朝の分析からエントリーまで

```python
# tests/e2e/test_morning_to_entry.py
import pytest
import time
from src.modules.data_processing.processor import DataProcessor
from src.modules.ai_analysis.analyzer import AIAnalyzer
from src.modules.rule_engine.engine import RuleEngine

@pytest.mark.e2e
class TestMorningToEntry:

    def test_full_workflow_morning_analysis_to_entry(self):
        """朝の分析からエントリーまでのフルフロー"""

        # 1. データ処理
        print("Step 1: Data Processing")
        processor = DataProcessor()
        market_data = processor.process("USDJPY")
        assert market_data is not None

        # 2. AI分析
        print("Step 2: AI Analysis")
        analyzer = AIAnalyzer()
        rules = analyzer.analyze_morning(market_data)
        assert rules['should_trade'] is not None

        # 3. ルールエンジン起動
        print("Step 3: Rule Engine")
        engine = RuleEngine()
        engine.load_rules(rules)

        # 4. エントリー監視（最大5分間）
        print("Step 4: Entry Monitoring")
        max_wait = 300  # 5分
        start_time = time.time()

        entry_executed = False
        while time.time() - start_time < max_wait:
            if engine.check_and_execute_entry():
                entry_executed = True
                break
            time.sleep(10)  # 10秒ごとにチェック

        # 検証
        if rules['should_trade']:
            print(f"Entry executed: {entry_executed}")
        else:
            print("No trade expected (NEUTRAL bias)")
```

#### シナリオ2: エントリーから決済まで

```python
# tests/e2e/test_entry_to_exit.py
@pytest.mark.e2e
class TestEntryToExit:

    def test_full_trade_lifecycle(self):
        """エントリーから決済までのライフサイクル"""

        # 前提: ポジション保有中
        # (前のテストでエントリー済み、またはテストデータ準備)

        # 1. Layer 1監視起動
        from src.modules.rule_engine.layer1_emergency import Layer1Emergency
        layer1 = Layer1Emergency()

        # 2. 決済監視起動
        from src.modules.rule_engine.exit_monitor import ExitMonitor
        exit_monitor = ExitMonitor()

        # 3. 決済まで監視（最大10分）
        max_wait = 600
        start_time = time.time()

        while time.time() - start_time < max_wait:
            # Layer 1チェック
            if layer1.check_emergency():
                print("Emergency stop triggered")
                break

            # 決済条件チェック
            if exit_monitor.check_exit_conditions():
                print("Exit conditions met")
                break

            time.sleep(1)

        # トレード記録確認
        from src.lib.database.connection import get_db_session
        from src.lib.database.models import Trade

        with get_db_session() as session:
            latest_trade = session.query(Trade).order_by(
                Trade.entry_time.desc()
            ).first()

            assert latest_trade is not None
            assert latest_trade.exit_time is not None
            assert latest_trade.profit is not None
```

### 4.3 E2Eテスト実行

```bash
# E2Eテストのみ実行
pytest -m e2e

# 詳細ログ付き
pytest -m e2e -v -s

# タイムアウト設定
pytest -m e2e --timeout=600
```

---

## 5. パフォーマンステスト

### 5.1 速度計測

**テスト対象**:
- データ処理速度（目標: 3秒以内）
- Layer 1応答速度（目標: 100ms以内）
- AI分析速度（目標: 5-8秒以内）

```python
# tests/performance/test_performance.py
import pytest
from src.modules.data_processing.processor import DataProcessor

@pytest.mark.benchmark
def test_data_processing_speed(benchmark):
    """データ処理速度テスト"""
    processor = DataProcessor()

    result = benchmark(processor.process, "USDJPY")

    # 3秒以内を確認
    assert benchmark.stats['mean'] < 3.0
```

```bash
# ベンチマーク実行
pytest --benchmark-only

# 結果をHTMLで出力
pytest --benchmark-only --benchmark-autosave --benchmark-histogram
```

---

## 6. テストデータ管理

### 6.1 フィクスチャ管理

**共通フィクスチャ**: `tests/fixtures/conftest.py`

```python
# tests/fixtures/conftest.py
import pytest
import pandas as pd

@pytest.fixture(scope="session")
def sample_ohlc_100():
    """サンプルOHLC 100本"""
    import numpy as np
    dates = pd.date_range('2024-01-01', periods=100, freq='1H')
    return pd.DataFrame({
        'time': dates,
        'open': np.random.uniform(149, 150, 100),
        'high': np.random.uniform(149.5, 150.5, 100),
        'low': np.random.uniform(148.5, 149.5, 100),
        'close': np.random.uniform(149, 150, 100),
        'volume': np.random.randint(1000, 2000, 100)
    })

@pytest.fixture(scope="session")
def sample_rules_json():
    """サンプルルールJSON"""
    return {
        "daily_bias": "BUY",
        "confidence": 0.75,
        "should_trade": True,
        "entry_conditions": {
            "direction": "BUY",
            "price_zone": {"min": 149.50, "max": 149.70},
            "required_signals": ["EMA20 > EMA50"]
        }
    }
```

### 6.2 テストデータベース

```python
# tests/fixtures/test_database.py
import pytest
from sqlalchemy import create_engine
from src.lib.database.models import Base

@pytest.fixture(scope="session")
def test_db_engine():
    """テスト用DB"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
```

---

## 7. CI/CD統合

### 7.1 GitHub Actions設定

```yaml
# .github/workflows/test.yml
name: Test

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt

    - name: Run unit tests
      run: |
        pytest --cov=src --cov-report=xml tests/

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml

    - name: Run integration tests
      run: |
        pytest tests/integration/
```

### 7.2 プルリクエスト時のテスト

- ユニットテスト必須
- カバレッジ80%以上
- 統合テスト通過

---

## 8. テスト実行チェックリスト

### 8.1 開発時（コミット前）

- [ ] 変更箇所のユニットテスト作成
- [ ] 既存テストが通過
- [ ] カバレッジ低下なし

### 8.2 プルリクエスト時

- [ ] 全ユニットテスト通過
- [ ] 統合テスト通過
- [ ] カバレッジ80%以上
- [ ] Lintエラーなし

### 8.3 リリース前

- [ ] E2Eテスト通過
- [ ] パフォーマンステスト通過
- [ ] デモ口座での動作確認

---

## 9. まとめ

### 9.1 テスト戦略の要点

1. **ユニットテスト**: 外部依存をモック化し、各モジュールを独立してテスト
2. **統合テスト**: モジュール間の連携を実データベースでテスト
3. **E2Eテスト**: デモ口座で実環境に近い形でテスト
4. **継続的テスト**: CI/CDでコミット毎に自動テスト

### 9.2 品質目標

| 指標 | 目標値 |
|------|--------|
| **ユニットテストカバレッジ** | 80%以上 |
| **統合テスト通過率** | 100% |
| **E2Eテスト通過率** | 100% |
| **データ処理速度** | 3秒以内 |
| **Layer 1応答速度** | 100ms以内 |

---

**本テスト戦略に従い、高品質なシステムを構築します。**
