# 環境変数による設定管理

## 概要

FX自動トレードシステムでは、`.env`ファイルを使用してすべての設定パラメータを管理できます。
これにより、コードを変更することなく、システムの動作を柔軟にカスタマイズできます。

## セットアップ

### 1. .envファイルの作成

```bash
# .env.templateをコピーして.envファイルを作成
cp .env.template .env
```

### 2. .envファイルの編集

`.env`ファイルをテキストエディタで開き、必要な設定値を入力します。

```bash
# 例: Visual Studio Code
code .env

# 例: Nano
nano .env
```

## 設定項目

### 🔷 Gemini APIモデル設定

**重要**: この設定により、各Phase（処理段階）で使用するGeminiモデルを指定できます。

```bash
# Phase 1 (デイリーレビュー) & Phase 2 (朝の詳細分析) 用
GEMINI_MODEL_PRO=gemini-2.5-flash

# Phase 3 (定期更新 12:00/16:00/21:30) 用
GEMINI_MODEL_FLASH=gemini-2.5-flash

# Phase 4 (Layer 3a監視 15分ごと) 用
GEMINI_MODEL_FLASH_8B=gemini-2.5-flash
```

#### モデル名の例

最新のモデル一覧: https://ai.google.dev/gemini-api/docs/models

| モデル名 | 特徴 | 推奨用途 |
|---------|------|---------|
| `gemini-2.5-flash` | 高速・高性能 | 全Phase（推奨） |
| `gemini-2.5-pro` | 最高精度 | Phase 1, 2, 5（高精度が必要な場合） |
| `gemini-2.0-flash-exp` | 実験版・高速 | テスト用 |

**動作確認方法**:
バックテスト実行時に以下のようなログが出力されます：

```
✓ Gemini API initialized:
  Phase 1&2 (Pro):  gemini-2.5-flash
  Phase 3 (Flash):  gemini-2.5-flash
  Phase 4 (8B):     gemini-2.5-flash
```

### 🔷 AI分析パラメータ

各モデルの温度設定（決定論性）と最大トークン数を調整できます。

```bash
# 温度設定（0.0-1.0、低いほど決定論的）
AI_TEMPERATURE_PRO=0.3          # Phase 1 & 2
AI_TEMPERATURE_FLASH=0.3        # Phase 3
AI_TEMPERATURE_FLASH_8B=0.2     # Phase 4

# 最大トークン数
AI_MAX_TOKENS_PRO=3000          # Phase 1 & 2
AI_MAX_TOKENS_FLASH=2000        # Phase 3
AI_MAX_TOKENS_FLASH_8B=500      # Phase 4
```

**温度（temperature）の設定ガイド**:
- `0.0-0.3`: 非常に決定論的、再現性が高い（推奨）
- `0.4-0.7`: バランス型、適度なランダム性
- `0.8-1.0`: 創造的、ランダム性が高い（非推奨）

### 🔷 バックテスト設定

```bash
# バックテスト期間
BACKTEST_START_DATE=2024-09-01
BACKTEST_END_DATE=2024-09-30

# バックテスト対象シンボル
BACKTEST_SYMBOL=USDJPY

# バックテスト初期残高（円）
BACKTEST_INITIAL_BALANCE=1000000

# ティックデータパス（オプション）
BACKTEST_CSV_PATH=data/tick_data/USDJPY/ticks_USDJPY-oj5k_2024-01.zip
```

**使用方法**:
```python
# パラメータを指定せずにバックテストを開始
# .envの設定が自動的に使用されます
engine = BacktestEngine()
results = engine.run()
```

### 🔷 リスク管理設定

```bash
# デフォルトポジションサイズ（ロット数）
POSITION_SIZE_DEFAULT=0.1

# 最大同時ポジション数
MAX_POSITIONS=3

# 口座リスク率（1トレードあたりの最大損失 %）
RISK_PER_TRADE=2.0

# ストップロス（pips）
DEFAULT_STOP_LOSS_PIPS=50

# テイクプロフィット（pips）
DEFAULT_TAKE_PROFIT_PIPS=100
```

### 🔷 テクニカル指標パラメータ

```bash
# EMA（指数移動平均）
EMA_SHORT_PERIOD=20
EMA_LONG_PERIOD=50

# RSI（相対力指数）
RSI_PERIOD=14
RSI_OVERBOUGHT=70
RSI_OVERSOLD=30

# MACD
MACD_FAST=12
MACD_SLOW=26
MACD_SIGNAL=9

# ATR（平均真実範囲）
ATR_PERIOD=14

# ボリンジャーバンド
BOLLINGER_PERIOD=20
BOLLINGER_STD_DEV=2.0

# サポート&レジスタンス
SUPPORT_RESISTANCE_WINDOW=20
```

### 🔷 Layer 3監視設定

```bash
# Layer 3a監視間隔（分）
LAYER3A_MONITOR_INTERVAL=15

# 異常検知の閾値
# 価格変動閾値（%）
ANOMALY_PRICE_CHANGE_THRESHOLD=0.5

# スプレッド拡大閾値（通常の何倍）
ANOMALY_SPREAD_MULTIPLIER=3.0

# ボラティリティ閾値（ATRの何倍）
ANOMALY_VOLATILITY_MULTIPLIER=2.0

# 含み損閾値（%）
ANOMALY_DRAWDOWN_THRESHOLD=3.0
```

## コードでの使用方法

### 設定の読み込み

```python
from src.utils.config import get_config

# 設定を取得
config = get_config()

# 設定値を使用
print(f"Gemini Pro Model: {config.gemini_model_pro}")
print(f"Initial Balance: {config.backtest_initial_balance}")
print(f"RSI Period: {config.rsi_period}")
```

### バックテストエンジン

```python
from src.backtest.backtest_engine import BacktestEngine

# .envから自動的に設定を読み込む
engine = BacktestEngine()

# または、特定の値を上書き
engine = BacktestEngine(
    symbol='EURJPY',  # USDJPYの代わりにEURJPY
    initial_balance=2000000  # 初期残高を200万円に変更
)
```

### AIAnalyzer

```python
from src.ai_analysis.ai_analyzer import AIAnalyzer

# .envから自動的に設定を読み込む
analyzer = AIAnalyzer(symbol='USDJPY', model='pro')

# モデル名は内部的に.envのGEMINI_MODEL_PROを使用
```

### GeminiClient

```python
from src.ai_analysis.gemini_client import GeminiClient

# .envから自動的に設定を読み込む
client = GeminiClient()

# AI分析（温度とトークン数は.envから自動取得）
response = client.generate_response(
    prompt="市場分析してください",
    model='pro'  # GEMINI_MODEL_PROを使用
)
```

## 設定の優先順位

設定値は以下の優先順位で適用されます：

1. **コードで明示的に指定した値** （最優先）
2. **.envファイルの値**
3. **デフォルト値** （最後の手段）

例：
```python
# ケース1: .envの値を使用
engine = BacktestEngine()  # .envのBACKTEST_INITIAL_BALANCEを使用

# ケース2: 明示的に指定
engine = BacktestEngine(initial_balance=5000000)  # 500万円を使用

# ケース3: .envに値がなければデフォルト
# .envにBACKTEST_INITIAL_BALANCEがない場合、1,000,000円を使用
```

## トラブルシューティング

### 問題: モデル名が反映されない

**原因**: `.env`ファイルが存在しないか、正しく読み込まれていない

**解決策**:
1. `.env`ファイルがプロジェクトルートに存在するか確認
2. `.env.template`をコピーして`.env`を作成
3. システムを再起動

### 問題: 設定値が空白またはコメントを含む

**原因**: `.env`ファイルでコメントが混在している

**間違った例**:
```bash
GEMINI_MODEL_PRO=gemini-2.5-flash  # これはコメント
```

**正しい例**:
```bash
# これはコメント
GEMINI_MODEL_PRO=gemini-2.5-flash
```

### 問題: 日本語が文字化けする

**解決策**: `.env`ファイルをUTF-8エンコーディングで保存

```bash
# Visual Studio Codeの場合
# 右下のエンコーディング表示をクリック → UTF-8を選択
```

## セキュリティ

`.env`ファイルには機密情報（APIキー、パスワード等）が含まれるため、以下の点に注意してください：

1. **Gitにコミットしない**
   - `.gitignore`に`.env`が含まれているか確認
   - 既にコミットしてしまった場合は`git rm --cached .env`で削除

2. **適切なファイルパーミッション**
   ```bash
   chmod 600 .env
   ```

3. **バックアップ**
   - `.env`ファイルは安全な場所にバックアップ
   - パスワードマネージャーで管理することを推奨

## まとめ

`.env`ファイルを使用することで：

✅ **コードを変更せずに設定を調整**できる
✅ **複数の環境（開発/本番）で異なる設定**を使用できる
✅ **機密情報をコードから分離**できる
✅ **チーム全体で統一された設定管理**ができる

設定を変更したら、システムを再起動して反映させてください。
