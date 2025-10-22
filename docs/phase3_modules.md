# フェーズ3: AI分析エンジン モジュール説明書

**作成日**: 2025-10-22
**バージョン**: 1.0
**対象フェーズ**: フェーズ3 - AI分析エンジン

---

## 目次

1. [概要](#概要)
2. [モジュール一覧](#モジュール一覧)
3. [gemini_client.py - Gemini APIクライアント](#gemini_clientpy---gemini-apiクライアント)
4. [ai_analyzer.py - AI分析オーケストレーター](#ai_analyzerpy---ai分析オーケストレーター)
5. [使用例](#使用例)
6. [テスト](#テスト)
7. [トラブルシューティング](#トラブルシューティング)
8. [パフォーマンス考慮事項](#パフォーマンス考慮事項)

---

## 概要

フェーズ3では、Google Gemini APIを活用したAI分析エンジンを実装しました。
このモジュール群は、マーケットデータを分析し、BUY/SELL/HOLDのトレード判断を行います。

### 主な機能

1. **Gemini API連携**: 3つのモデル（Pro/Flash/Flash-8B）をサポート
2. **マーケット分析**: 複数時間足とテクニカル指標を統合分析
3. **トレード判断**: BUY/SELL/HOLDの判断と信頼度算出
4. **判断理由生成**: AIによる詳細な判断理由の説明
5. **データベース保存**: 判断結果の永続化

### アーキテクチャ

```
[ティックデータ]
    ↓
[時間足変換]
    ↓
[テクニカル指標計算]
    ↓
[データ標準化]
    ↓
[Gemini API] → [AI判断結果]
    ↓
[データベース保存]
```

---

## モジュール一覧

| モジュール名 | ファイルパス | 主な機能 |
|------------|------------|---------|
| **GeminiClient** | `src/ai_analysis/gemini_client.py` | Gemini API連携、プロンプト構築、レスポンスパース |
| **AIAnalyzer** | `src/ai_analysis/ai_analyzer.py` | 分析フロー統合、DB保存、履歴管理 |

---

## gemini_client.py - Gemini APIクライアント

### 概要

Google Gemini APIと連携し、マーケットデータを分析するクライアントモジュールです。
3つのモデルをサポートし、精度と速度のバランスを調整できます。

### クラス: GeminiClient

#### 初期化

```python
from src.ai_analysis import GeminiClient

client = GeminiClient()
```

**必要な環境変数**:
- `GEMINI_API_KEY`: Gemini APIキー（必須）

**初期化時の動作**:
1. APIキーの検証
2. 3つのモデルの初期化
   - `gemini-1.5-pro-latest`: 高精度モデル
   - `gemini-1.5-flash-latest`: バランス型モデル（推奨）
   - `gemini-1.5-flash-8b-latest`: 高速軽量モデル

#### 主要メソッド

##### 1. analyze_market()

マーケットデータを分析してトレード判断を行います。

```python
result = client.analyze_market(
    market_data=standardized_data,
    model='flash'  # 'pro' / 'flash' / 'flash-lite'
)
```

**引数**:
- `market_data` (Dict): 標準化されたマーケットデータ
- `model` (str): 使用するモデル名

**戻り値** (Dict):
```python
{
    'action': 'BUY' | 'SELL' | 'HOLD',
    'confidence': 0-100,
    'reasoning': '判断理由の詳細説明',
    'entry_price': エントリー価格 (optional),
    'stop_loss': ストップロス価格 (optional),
    'take_profit': テイクプロフィット価格 (optional)
}
```

##### 2. test_connection()

Gemini APIへの接続をテストします。

```python
is_connected = client.test_connection()
if is_connected:
    print("API接続成功")
```

**戻り値**:
- `True`: 接続成功
- `False`: 接続失敗

#### モデル比較

| モデル | 精度 | 速度 | コスト | 推奨用途 |
|-------|-----|------|-------|---------|
| **Pro** | ★★★★★ | ★☆☆☆☆ | 高 | 重要な判断、詳細分析 |
| **Flash** | ★★★★☆ | ★★★★☆ | 中 | 通常運用（推奨） |
| **Flash-8B** | ★★★☆☆ | ★★★★★ | 低 | バックテスト、高頻度分析 |

#### プロンプト構築

GeminiClientは以下の情報を含む詳細なプロンプトを構築します:

1. **各時間足の分析指示** (D1/H4/H1/M15)
2. **テクニカル指標の解釈** (EMA/RSI/MACD/BB/ATR)
3. **サポート・レジスタンスの考慮**
4. **総合判断の基準**

#### レスポンスパース

AIの応答からJSON形式の判断結果を抽出します。

- JSON形式が見つからない場合: HOLD判断を返す
- 無効なactionの場合: HOLD判断を返す
- 必須フィールドが欠けている場合: デフォルト値を設定

#### エラーハンドリング

```python
try:
    result = client.analyze_market(market_data)
except Exception as e:
    # エラー時はHOLD判断を返す
    # reasoning フィールドにエラーメッセージが含まれる
    print(f"Analysis error: {result['reasoning']}")
```

---

## ai_analyzer.py - AI分析オーケストレーター

### 概要

AI分析の全フローを統合管理するオーケストレーターモジュールです。
データ読み込みから判断結果の保存まで、一連の処理を実行します。

### クラス: AIAnalyzer

#### 初期化

```python
from src.ai_analysis import AIAnalyzer

analyzer = AIAnalyzer(
    symbol='USDJPY',
    data_dir='data/tick_data',
    model='flash'
)
```

**引数**:
- `symbol` (str): 通貨ペア（デフォルト: 'USDJPY'）
- `data_dir` (str): ティックデータディレクトリ
- `model` (str): 使用するGeminiモデル

**必要な環境変数**:
```
GEMINI_API_KEY=your_gemini_api_key
DB_HOST=localhost
DB_PORT=5432
DB_NAME=fx_autotrade
DB_USER=postgres
DB_PASSWORD=your_password
```

#### 主要メソッド

##### 1. analyze_market()

マーケット分析の全フローを実行します。

```python
result = analyzer.analyze_market(
    year=2024,
    month=9,
    lookback_days=60
)
```

**引数**:
- `year` (Optional[int]): データ年（Noneの場合は現在）
- `month` (Optional[int]): データ月（Noneの場合は現在）
- `lookback_days` (int): 分析に使用する過去日数

**戻り値** (Dict):
```python
{
    'action': 'BUY' | 'SELL' | 'HOLD',
    'confidence': 0-100,
    'reasoning': '判断理由',
    'timestamp': '分析実行時刻',
    'symbol': '通貨ペア',
    'model': '使用モデル',
    'entry_price': エントリー価格 (optional),
    'stop_loss': SL価格 (optional),
    'take_profit': TP価格 (optional)
}
```

**処理フロー**:

1. **ティックデータ読み込み** (`_load_tick_data`)
   - zipファイルから指定年月のティックデータを読み込み
   - データ検証を実行

2. **時間足変換** (`_convert_timeframes`)
   - D1/H4/H1/M15の4つの時間足に変換
   - OHLCV形式のデータを生成

3. **テクニカル指標計算** (`_calculate_indicators`)
   - H1足をベースに各種指標を計算
   - EMA（短期20, 長期50）
   - RSI（期間14）
   - MACD（12, 26, 9）
   - ATR（期間14）
   - Bollinger Bands（期間20, 2σ）
   - Support & Resistance（ウィンドウ20）

4. **データ標準化**
   - AI用のJSON形式に変換
   - DataStandardizerを使用

5. **AI分析実行**
   - GeminiClientを呼び出し
   - BUY/SELL/HOLD判断を取得

6. **データベース保存** (`_save_to_database`)
   - ai_judgmentsテーブルに保存
   - market_dataはJSONB形式で保存

##### 2. get_recent_judgments()

最近のAI判断履歴を取得します。

```python
judgments = analyzer.get_recent_judgments(limit=10)

for judgment in judgments:
    print(f"{judgment['timestamp']}: {judgment['action']} ({judgment['confidence']}%)")
```

**引数**:
- `limit` (int): 取得件数（デフォルト: 10）

**戻り値** (List[Dict]):
```python
[
    {
        'id': 判断ID,
        'timestamp': 分析時刻,
        'symbol': 通貨ペア,
        'action': 判断,
        'confidence': 信頼度,
        'reasoning': 理由,
        'created_at': 作成時刻
    },
    ...
]
```

#### データベーススキーマ

AIAnalyzerは`ai_judgments`テーブルにデータを保存します:

```sql
CREATE TABLE ai_judgments (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    action VARCHAR(10) NOT NULL,
    confidence DECIMAL(5, 2),
    reasoning TEXT,
    market_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### エラーハンドリング

各ステップでエラーが発生した場合、`_create_error_result()`メソッドが
エラー情報を含むHOLD判断を返します。

```python
{
    'action': 'HOLD',
    'confidence': 0,
    'reasoning': 'Analysis failed: [エラーメッセージ]',
    'error': '[詳細エラーメッセージ]',
    ...
}
```

---

## 使用例

### 基本的な使用方法

```python
from src.ai_analysis import AIAnalyzer
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# アナライザーの初期化
analyzer = AIAnalyzer(
    symbol='USDJPY',
    model='flash'
)

# マーケット分析の実行
result = analyzer.analyze_market(year=2024, month=9)

# 結果の表示
print(f"判断: {result['action']}")
print(f"信頼度: {result['confidence']}%")
print(f"理由: {result['reasoning']}")

if result['action'] in ['BUY', 'SELL']:
    print(f"エントリー: {result.get('entry_price')}")
    print(f"SL: {result.get('stop_loss')}")
    print(f"TP: {result.get('take_profit')}")
```

### 複数モデルでの比較分析

```python
from src.ai_analysis import AIAnalyzer

# 3つのモデルで分析
models = ['pro', 'flash', 'flash-lite']
results = {}

for model in models:
    analyzer = AIAnalyzer(symbol='USDJPY', model=model)
    result = analyzer.analyze_market(year=2024, month=9)
    results[model] = result

# 結果の比較
for model, result in results.items():
    print(f"{model}: {result['action']} ({result['confidence']}%)")
```

### 判断履歴の分析

```python
from src.ai_analysis import AIAnalyzer

analyzer = AIAnalyzer(symbol='USDJPY')

# 最近の判断を取得
judgments = analyzer.get_recent_judgments(limit=20)

# 統計情報の計算
buy_count = sum(1 for j in judgments if j['action'] == 'BUY')
sell_count = sum(1 for j in judgments if j['action'] == 'SELL')
hold_count = sum(1 for j in judgments if j['action'] == 'HOLD')

avg_confidence = sum(j['confidence'] for j in judgments) / len(judgments)

print(f"BUY: {buy_count}, SELL: {sell_count}, HOLD: {hold_count}")
print(f"平均信頼度: {avg_confidence:.1f}%")
```

---

## テスト

### テストファイル

**ファイル名**: `tests/test_ai_analyzer.py`

### テスト実行

```bash
# 全テスト実行
pytest tests/test_ai_analyzer.py -v

# 特定のテストクラスのみ実行
pytest tests/test_ai_analyzer.py::TestGeminiClient -v

# カバレッジ付き実行
pytest tests/test_ai_analyzer.py --cov=src.ai_analysis --cov-report=html
```

### テストケース一覧

#### GeminiClient

1. `test_client_initialization`: 初期化テスト
2. `test_client_initialization_no_api_key`: APIキー未設定時のテスト
3. `test_build_analysis_prompt`: プロンプト構築テスト
4. `test_parse_response_valid_json`: 正常なJSONパーステスト
5. `test_parse_response_invalid_action`: 無効なaction処理テスト
6. `test_parse_response_no_json`: JSON形式なしレスポンステスト
7. `test_select_model`: モデル選択テスト
8. `test_analyze_market_success`: マーケット分析成功テスト
9. `test_analyze_market_api_error`: API呼び出しエラーテスト

#### AIAnalyzer

1. `test_analyzer_initialization`: 初期化テスト
2. `test_create_error_result`: エラー結果作成テスト
3. `test_save_to_database`: DB保存テスト

### モックの使用

テストではモックを使用して、実際のAPI呼び出しやDB接続を行わずにテストできます。

```python
from unittest.mock import Mock, patch

@patch('google.generativeai.GenerativeModel')
def test_example(mock_model):
    # モックの設定
    mock_response = Mock()
    mock_response.text = '{"action": "BUY", "confidence": 80}'
    mock_model.return_value.generate_content.return_value = mock_response

    # テスト実行
    # ...
```

---

## トラブルシューティング

### 問題1: GEMINI_API_KEYが設定されていない

**エラーメッセージ**:
```
ValueError: GEMINI_API_KEY environment variable is not set
```

**解決方法**:
1. `.env`ファイルに`GEMINI_API_KEY`を追加
2. 環境変数を直接設定
```bash
export GEMINI_API_KEY='your_api_key'
```

### 問題2: API呼び出しエラー

**エラーメッセージ**:
```
AI analysis error: [API Error Details]
```

**考えられる原因**:
1. APIキーが無効または期限切れ
2. API利用制限（レートリミット）
3. ネットワーク接続の問題

**解決方法**:
1. APIキーの有効性を確認
2. API利用状況を確認（Google Cloud Console）
3. リトライロジックの実装を検討

### 問題3: データベース接続エラー

**エラーメッセージ**:
```
Failed to save to database: [Connection Error]
```

**解決方法**:
1. PostgreSQLが起動しているか確認
```bash
sudo systemctl status postgresql
```

2. データベース接続情報を確認
```bash
psql -h localhost -U postgres -d fx_autotrade
```

3. `.env`ファイルの接続情報を確認

### 問題4: ティックデータが見つからない

**エラーメッセージ**:
```
FileNotFoundError: [Tick data file not found]
```

**解決方法**:
1. データファイルのパスを確認
```
data/tick_data/USDJPY/ticks_USDJPY-oj5k_2024-09.zip
```

2. ファイル名のフォーマットを確認
```
ticks_{SYMBOL}-oj5k_{YEAR:04d}-{MONTH:02d}.zip
```

### 問題5: AI判断が常にHOLDになる

**考えられる原因**:
1. APIレスポンスのパースに失敗
2. データ品質の問題
3. プロンプトの問題

**デバッグ方法**:
1. ログレベルをDEBUGに設定
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

2. APIレスポンスを確認
```python
client = GeminiClient()
response = client.analyze_market(market_data)
print(response)  # レスポンスの詳細を確認
```

### 問題6: メモリ不足

**症状**:
- 大量のティックデータ処理時にメモリエラー

**解決方法**:
1. データを分割して処理
2. 不要なデータフレームを削除
```python
del tick_data
import gc
gc.collect()
```

3. lookback_daysを減らす

---

## パフォーマンス考慮事項

### API呼び出しコスト

| モデル | 入力コスト | 出力コスト | 推奨利用 |
|-------|----------|----------|---------|
| Pro | $0.00125/1K tokens | $0.005/1K tokens | 重要判断 |
| Flash | $0.000075/1K tokens | $0.0003/1K tokens | 通常運用 |
| Flash-8B | $0.0000375/1K tokens | $0.00015/1K tokens | 高頻度 |

**1回の分析あたりの推定トークン数**:
- 入力: 約3,000-5,000トークン
- 出力: 約500-1,000トークン

### 処理時間

| フェーズ | 処理時間 | 備考 |
|---------|---------|------|
| ティックデータ読み込み | 5-10秒 | データ量により変動 |
| 時間足変換 | 10-20秒 | 約1,400万tick処理時 |
| テクニカル指標計算 | 1-2秒 | pandas演算 |
| データ標準化 | <1秒 | JSON変換 |
| Gemini API呼び出し | 2-10秒 | モデルにより変動 |
| DB保存 | <1秒 | ネットワーク状況による |
| **合計** | **約20-45秒** | 初回実行時 |

### 最適化のヒント

1. **データキャッシュの活用**
```python
# 頻繁に使用するデータはキャッシュ
import functools

@functools.lru_cache(maxsize=128)
def load_and_process_data(symbol, year, month):
    # データ処理
    pass
```

2. **バッチ処理**
```python
# 複数の分析をバッチで実行
results = []
for period in periods:
    result = analyzer.analyze_market(year=period[0], month=period[1])
    results.append(result)
```

3. **非同期処理**
```python
import asyncio

async def analyze_async(analyzer, year, month):
    return analyzer.analyze_market(year=year, month=month)

# 複数の分析を並列実行
results = await asyncio.gather(
    analyze_async(analyzer, 2024, 9),
    analyze_async(analyzer, 2024, 10)
)
```

4. **モデル選択の最適化**
- バックテスト: Flash-8B
- 通常運用: Flash
- 重要判断: Pro

---

## まとめ

フェーズ3のAI分析エンジンは、以下の機能を提供します:

✅ **実装済み機能**
- Gemini API連携（3モデル対応）
- マーケットデータ分析
- BUY/SELL/HOLD判断
- 信頼度計算（0-100%）
- 判断理由の生成
- データベース保存
- 判断履歴の管理

📋 **次のステップ（フェーズ4）**
- トレードルールエンジン
- MT5トレード実行
- ポジション管理

---

**ドキュメント更新日**: 2025-10-22
**作成者**: Claude Code
**バージョン**: 1.0
