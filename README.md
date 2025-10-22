# FX AI自動トレードシステム

Gemini APIを活用したFX（ドル円）の自動トレードシステム

---

## 概要

このシステムは、Google の Gemini API を活用して、FX市場（USDJPY）のティックデータを分析し、
自動的にトレード判断を行うシステムです。

### 主な特徴

- **AI駆動のトレード判断**: Gemini APIによる高度なマーケット分析
- **多時間軸分析**: D1/H4/H1/M15の4つの時間軸を統合分析
- **テクニカル指標**: EMA、RSI、MACD、ATR、ボリンジャーバンドなど
- **3層モニタリング**: リスク管理のための多層モニタリングシステム
- **バックテスト機能**: AI判断精度の検証と最適化

---

## プロジェクト構成

```
fx-ai-autotrade/
├── src/                          # ソースコード
│   ├── data_processing/          # データ処理（ティック読み込み、時間足変換）
│   ├── ai_analysis/              # AI分析（Gemini API連携）
│   ├── rule_engine/              # トレードルール管理
│   ├── trade_execution/          # MT5トレード実行
│   ├── monitoring/               # ポジションモニタリング
│   └── utils/                    # ユーティリティ
├── tests/                        # テストコード
├── data/                         # データ保存先
│   └── tick_data/               # ティックデータ（zip形式）
├── config/                       # 設定ファイル
│   └── database_schema.sql      # データベーススキーマ
├── logs/                         # ログファイル
├── docs/                         # ドキュメント
│   ├── architecture/            # アーキテクチャ設計
│   ├── basic_design/            # 基本設計
│   └── phase1_modules.md        # フェーズ1モジュール説明書
├── requirements.txt              # Python依存パッケージ
├── .env.template                # 環境変数テンプレート
├── FX自動トレード仕様書.md        # システム仕様書
└── 開発ステップ.md                # 開発手順書
```

---

## セットアップ

### 前提条件

- Python 3.11以上
- PostgreSQL 14以上
- MetaTrader5（デモ口座またはライブ口座）
- Gemini APIキー

### インストール手順

1. **リポジトリのクローン**
   ```bash
   git clone <repository-url>
   cd fx-ai-autotrade
   ```

2. **仮想環境の作成と有効化**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # または
   venv\Scripts\activate     # Windows
   ```

3. **依存パッケージのインストール**
   ```bash
   pip install -r requirements.txt
   ```

4. **環境変数の設定**
   ```bash
   cp .env.template .env
   # .envファイルを編集して、以下を設定:
   # - GEMINI_API_KEY: Gemini APIキー
   # - MT5_LOGIN, MT5_PASSWORD, MT5_SERVER: MT5接続情報
   # - DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD: データベース接続情報
   ```

5. **データベースのセットアップ**
   ```bash
   # PostgreSQLに接続してデータベースを作成
   createdb fx_autotrade

   # スキーマを適用
   psql -d fx_autotrade -f config/database_schema.sql
   ```

---

## 使用方法

### フェーズ1: データ基盤

#### ティックデータの読み込み

```python
from src.data_processing.tick_loader import TickDataLoader

# ローダーのインスタンス化
loader = TickDataLoader(data_dir="data/tick_data")

# 2024年9月のUSDJPYティックデータを読み込み
tick_data = loader.load_from_zip("USDJPY", 2024, 9)

# データ検証
if loader.validate_data(tick_data):
    print(f"読み込み成功: {len(tick_data)} 件のティックデータ")
```

### フェーズ2: データ変換とテクニカル指標

#### 時間足変換とテクニカル指標の計算

```python
from src.data_processing import TimeframeConverter, TechnicalIndicators

# 時間足変換
converter = TimeframeConverter()
h1_data = converter.convert_to_timeframe(tick_data, 'H1')

# テクニカル指標計算
indicators = TechnicalIndicators()
rsi = indicators.calculate_rsi(h1_data['close'])
macd = indicators.calculate_macd(h1_data['close'])
```

### フェーズ3: AI分析エンジン（現在の実装状態）

#### AI判断の実行

```python
from src.ai_analysis import AIAnalyzer

# AIアナライザーの初期化
analyzer = AIAnalyzer(
    symbol='USDJPY',
    model='flash'  # 'pro' / 'flash' / 'flash-lite'
)

# マーケット分析実行
result = analyzer.analyze_market(year=2024, month=9)

# 結果の表示
print(f"判断: {result['action']}")
print(f"信頼度: {result['confidence']}%")
print(f"理由: {result['reasoning']}")
```

#### サンプルスクリプトの実行

```bash
# Phase 3のデモスクリプト実行
python phase3_sample.py

# Phase 4のデモスクリプト実行
python phase4_sample.py
```

### フェーズ4: ルールエンジンとトレード実行（現在の実装状態）

#### トレード実行

```python
from src.ai_analysis import AIAnalyzer
from src.trade_execution import PositionManager

# AI分析
analyzer = AIAnalyzer(symbol='USDJPY')
ai_judgment = analyzer.analyze_market(year=2024, month=9)

# トレード実行（デモモード）
manager = PositionManager(symbol='USDJPY', use_mt5=False)
result = manager.process_ai_judgment(ai_judgment)

print(f"実行結果: {result['success']}")
print(f"メッセージ: {result['message']}")
```

#### テストの実行

```bash
# 全テスト実行
pytest tests/ -v

# 特定のモジュールのテスト
pytest tests/test_tick_loader.py -v
pytest tests/test_ai_analyzer.py -v
pytest tests/test_phase4.py -v

# カバレッジ付きテスト実行
pytest tests/ --cov=src --cov-report=html
```

---

## 開発フェーズ

### フェーズ1: 環境構築とデータ基盤 ✅ 完了
- [x] プロジェクト構造の構築
- [x] 依存パッケージの設定
- [x] データベーススキーマの作成
- [x] ティックデータローダーの実装
- [x] ユニットテストの作成

### フェーズ2: データ変換とテクニカル指標計算 ✅ 完了
- [x] 時間足変換（D1/H4/H1/M15）
- [x] テクニカル指標計算（EMA/RSI/MACD/ATR/BB）
- [x] AI用データ標準化とJSON変換

### フェーズ3: AI分析エンジン ✅ 完了
- [x] Gemini API連携（3モデル対応: Pro/Flash/Flash-8B）
- [x] AI判断ロジック実装（BUY/SELL/HOLD）
- [x] 判断結果のDB保存
- [x] 統合分析フロー実装

### フェーズ4: ルールエンジンとトレード実行 ✅ 完了
- [x] トレードルールエンジン（信頼度/スプレッド/ポジション数チェック）
- [x] MT5トレード実行（成行注文、決済）
- [x] ポジション管理（統合フロー）

### フェーズ5: モニタリングと決済
- [ ] 3層モニタリングシステム
- [ ] 自動決済機能
- [ ] アラート通知

### フェーズ6: バックテスト
- [ ] バックテストエンジン
- [ ] 結果分析とレポート生成

---

## ドキュメント

- **[FX自動トレード仕様書.md](./FX自動トレード仕様書.md)**: システム全体の仕様
- **[開発ステップ.md](./開発ステップ.md)**: 段階的な開発手順
- **[docs/phase1_modules.md](./docs/phase1_modules.md)**: フェーズ1のモジュール詳細説明
- **[docs/phase3_modules.md](./docs/phase3_modules.md)**: フェーズ3のモジュール詳細説明
- **[docs/architecture/](./docs/architecture/)**: アーキテクチャ設計書
- **[docs/basic_design/](./docs/basic_design/)**: 基本設計書

---

## データフォーマット

### ティックデータ（zipファイル）

**ファイル名**: `ticks_{symbol}-oj5k_{year:04d}-{month:02d}.zip`
- 例: `ticks_USDJPY-oj5k_2024-09.zip`

**内部CSV**: `ticks_{symbol}-oj5k_{year:04d}-{month:02d}.csv`

**CSVフォーマット（TSV形式、タブ区切り）**:
```
<DATE>	<TIME>	<BID>	<ASK>	<LAST>	<VOLUME>
2024.09.01	00:00:00.000	145.123	145.125
2024.09.01	00:00:01.123	145.124	145.126		100
2024.09.01	00:00:02.456	145.125	145.127		150
...
```

**注意事項**:
- カラムは実際にはタブ文字で区切られています（TSV形式）
- `<LAST>` と `<VOLUME>` は空の場合があります
- 日付フォーマット: YYYY.MM.DD
- 時刻フォーマット: HH:MM:SS.fff（ミリ秒含む）

---

## テクノロジースタック

### バックエンド
- **Python 3.11+**: メイン開発言語
- **pandas / numpy**: データ処理
- **psycopg2**: PostgreSQL接続
- **MetaTrader5**: トレード実行

### AI/機械学習
- **Google Gemini API**: マーケット分析と判断

### データベース
- **PostgreSQL 14+**: データ永続化

### テスト
- **pytest**: ユニットテスト
- **pytest-cov**: カバレッジ測定

---

## コーディング規約

- **PEP 8準拠**: Python標準コーディング規約
- **型ヒント**: 全ての関数に型アノテーションを使用
- **Docstring**: 全てのモジュール、クラス、関数にドキュメント文字列を記述
- **ロギング**: 適切なログレベルでログを出力
- **テストカバレッジ**: 80%以上を目標

---

## ライセンス

（ライセンスを記載してください）

---

## 貢献

プルリクエストを歓迎します。大きな変更の場合は、まずissueを開いて変更内容を議論してください。

---

## サポート

問題が発生した場合は、以下を確認してください:

1. フェーズ別モジュールドキュメントのトラブルシューティングセクション
   - **[docs/phase1_modules.md](./docs/phase1_modules.md)**: データ基盤
   - **[docs/phase3_modules.md](./docs/phase3_modules.md)**: AI分析エンジン
2. GitHubのIssuesセクション
3. 開発ドキュメント

---

**プロジェクト作成日**: 2025-10-21
**現在のフェーズ**: フェーズ4完了
**バージョン**: 0.4.0
