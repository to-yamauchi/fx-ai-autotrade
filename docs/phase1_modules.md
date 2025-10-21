# フェーズ1 モジュール説明書

## 概要
このドキュメントでは、フェーズ1「環境構築とデータ基盤」で実装された全モジュールの詳細な説明を提供します。

作成日: 2025-10-21
フェーズ: フェーズ1 - 環境構築とデータ基盤

---

## 目次
1. [ディレクトリ構造](#ディレクトリ構造)
2. [設定ファイル](#設定ファイル)
3. [データ処理モジュール](#データ処理モジュール)
4. [データベース設計](#データベース設計)
5. [テストモジュール](#テストモジュール)

---

## ディレクトリ構造

```
fx-ai-autotrade/
├── src/                          # ソースコードディレクトリ
│   ├── __init__.py              # メインパッケージ初期化
│   ├── data_processing/          # データ処理モジュール群
│   │   ├── __init__.py          # データ処理パッケージ初期化
│   │   └── tick_loader.py       # ティックデータローダー
│   ├── ai_analysis/              # AI分析モジュール群（今後実装）
│   │   └── __init__.py
│   ├── rule_engine/              # ルールエンジンモジュール群（今後実装）
│   │   └── __init__.py
│   ├── trade_execution/          # トレード実行モジュール群（今後実装）
│   │   └── __init__.py
│   ├── monitoring/               # モニタリングモジュール群（今後実装）
│   │   └── __init__.py
│   └── utils/                    # ユーティリティモジュール群（今後実装）
│       └── __init__.py
├── tests/                        # テストコードディレクトリ
│   ├── __init__.py              # テストパッケージ初期化
│   └── test_tick_loader.py      # ティックデータローダーのテスト
├── data/                         # データ保存ディレクトリ
│   └── tick_data/               # ティックデータ保存先
│       └── USDJPY/              # 通貨ペア別ディレクトリ
├── config/                       # 設定ファイルディレクトリ
│   └── database_schema.sql      # データベーススキーマ定義
├── logs/                         # ログファイル保存先
├── docs/                         # ドキュメント
│   └── phase1_modules.md        # このドキュメント
├── requirements.txt              # Python依存パッケージ一覧
├── .env.template                # 環境変数テンプレート
└── .gitignore                   # Git除外設定
```

---

## 設定ファイル

### 1. requirements.txt
**ファイルパス**: `/requirements.txt`

**目的**: Python依存パッケージの管理

**内容**:
| パッケージ | バージョン | 用途 |
|-----------|----------|------|
| pandas | >=2.0.0 | データ処理 |
| numpy | >=1.24.0 | 数値計算 |
| MetaTrader5 | >=5.0.45 | MT5連携 |
| psycopg2-binary | >=2.9.0 | PostgreSQL接続 |
| google-generativeai | >=0.3.0 | Gemini API連携 |
| python-dotenv | >=1.0.0 | 環境変数管理 |
| pytest | >=7.4.0 | テスト実行 |
| pytest-cov | >=4.1.0 | テストカバレッジ |
| colorlog | >=6.7.0 | ログ出力 |
| mypy | >=1.5.0 | 型チェック |

**使用方法**:
```bash
# パッケージのインストール
pip install -r requirements.txt
```

---

### 2. .env.template
**ファイルパス**: `/.env.template`

**目的**: 環境変数設定のテンプレート提供

**含まれる設定項目**:
- **Gemini API設定**: GEMINI_API_KEY
- **MetaTrader5設定**: MT5_LOGIN, MT5_PASSWORD, MT5_SERVER
- **PostgreSQL設定**: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
- **ロギング設定**: LOG_LEVEL, LOG_FILE
- **トレード設定**: TRADE_MODE (demo/live)

**使用方法**:
```bash
# .env.templateをコピーして.envを作成
cp .env.template .env

# .envを編集して実際の値を設定
nano .env
```

**注意事項**:
- `.env`ファイルは`.gitignore`に含まれており、Gitにコミットされません
- 機密情報は絶対にコードに直接書かないでください

---

### 3. .gitignore
**ファイルパス**: `/.gitignore`

**目的**: Git管理から除外するファイル・ディレクトリの指定

**除外対象**:
- Python関連: `__pycache__/`, `*.pyc`, `venv/`
- 機密情報: `.env`
- ログファイル: `logs/`, `*.log`
- データファイル: `data/tick_data/**/*.zip`, `data/tick_data/**/*.csv`
- IDE設定: `.vscode/`, `.idea/`
- テストカバレッジ: `.coverage`, `htmlcov/`

---

## データ処理モジュール

### 1. tick_loader.py
**ファイルパス**: `src/data_processing/tick_loader.py`

**目的**: 月次zipファイルからティックデータを読み込む

#### クラス: TickDataLoader

**責務**:
- zipファイルの展開と読み込み
- CSV形式データのパース
- タイムスタンプのDatetime変換
- データバリデーション

**主要メソッド**:

##### `__init__(data_dir: str = "data/tick_data")`
TickDataLoaderの初期化

- **引数**:
  - `data_dir` (str): ティックデータが格納されているディレクトリパス
- **処理内容**:
  - ロガーの初期化
  - データディレクトリパスの設定

##### `load_from_zip(symbol: str, year: int, month: int) -> List[Dict]`
zipファイルからティックデータを読み込む

- **引数**:
  - `symbol` (str): 通貨ペア（例: "USDJPY"）
  - `year` (int): 年（例: 2024）
  - `month` (int): 月（1-12）
- **戻り値**: ティックデータのリスト（各要素は辞書形式）
- **例外**:
  - `FileNotFoundError`: ファイルが存在しない場合
  - `Exception`: zipファイル破損やCSV形式エラー

**データ構造（戻り値）**:
```python
[
    {
        'timestamp': datetime(2024, 9, 1, 0, 0, 0),  # ティック発生時刻
        'bid': 145.123,                               # Bid価格
        'ask': 145.125,                               # Ask価格
        'volume': 100                                 # 出来高
    },
    ...
]
```

##### `validate_data(tick_data: List[Dict]) -> bool`
読み込んだティックデータの妥当性を検証

- **引数**:
  - `tick_data` (List[Dict]): 検証対象のティックデータ
- **戻り値**: 検証成功時True、失敗時False
- **検証項目**:
  1. データが空でないか
  2. 必須フィールド（timestamp, bid, ask, volume）が存在するか
  3. 価格が正の値か
  4. Bid <= Ask の関係が保たれているか

**使用例**:
```python
from src.data_processing.tick_loader import TickDataLoader

# ローダーのインスタンス化
loader = TickDataLoader(data_dir="data/tick_data")

# データ読み込み
tick_data = loader.load_from_zip("USDJPY", 2024, 9)

# データ検証
if loader.validate_data(tick_data):
    print(f"読み込み成功: {len(tick_data)} 件")
else:
    print("データ検証失敗")
```

**ファイルフォーマット**:
- **入力zipファイル名**: `ticks_{symbol}-oj5k_{year:04d}-{month:02d}.zip`
  - 例: `ticks_USDJPY-oj5k_2024-09.zip`
- **内部CSVファイル名**: `ticks_{symbol}-oj5k_{year:04d}-{month:02d}.csv`
  - 例: `ticks_USDJPY-oj5k_2024-09.csv`

**CSVフォーマット**:
```csv
timestamp,bid,ask,volume
2024-09-01T00:00:00,145.123,145.125,100
2024-09-01T00:00:01,145.124,145.126,150
...
```

**エラーハンドリング**:
- ファイルが見つからない → `FileNotFoundError`を発生させログ出力
- zipファイルが破損 → `Exception`を発生させログ出力
- CSV行のパース失敗 → 該当行をスキップして警告ログ出力、処理継続

---

## データベース設計

### database_schema.sql
**ファイルパス**: `config/database_schema.sql`

**目的**: PostgreSQLデータベースのテーブル定義

#### テーブル一覧

##### 1. tick_data（ティックデータテーブル）

**用途**: MT5から取得した生のティックデータを保存

| カラム名 | 型 | 説明 | 制約 |
|---------|---|------|------|
| id | BIGSERIAL | 主キー | PRIMARY KEY |
| symbol | VARCHAR(10) | 通貨ペア（例: USDJPY） | NOT NULL |
| timestamp | TIMESTAMP | ティック発生時刻 | NOT NULL |
| bid | DECIMAL(10, 5) | Bid価格（売値） | NOT NULL |
| ask | DECIMAL(10, 5) | Ask価格（買値） | NOT NULL |
| volume | INTEGER | 出来高 | - |

**制約・インデックス**:
- UNIQUE制約: (symbol, timestamp) - 重複データ防止
- インデックス: timestamp, (symbol, timestamp) - 検索高速化

---

##### 2. timeframe_data（時間足データテーブル）

**用途**: ティックデータから生成したOHLCVデータを保存

| カラム名 | 型 | 説明 | 制約 |
|---------|---|------|------|
| id | BIGSERIAL | 主キー | PRIMARY KEY |
| symbol | VARCHAR(10) | 通貨ペア | NOT NULL |
| timeframe | VARCHAR(5) | 時間足（D1/H4/H1/M15） | NOT NULL |
| timestamp | TIMESTAMP | 足の開始時刻 | NOT NULL |
| open | DECIMAL(10, 5) | 始値 | NOT NULL |
| high | DECIMAL(10, 5) | 高値 | NOT NULL |
| low | DECIMAL(10, 5) | 安値 | NOT NULL |
| close | DECIMAL(10, 5) | 終値 | NOT NULL |
| volume | INTEGER | 出来高 | - |

**制約・インデックス**:
- UNIQUE制約: (symbol, timeframe, timestamp)
- インデックス: (symbol, timeframe, timestamp)

---

##### 3. ai_judgments（AIトレード判断テーブル）

**用途**: Gemini APIによるトレード判断結果を保存

| カラム名 | 型 | 説明 | 制約 |
|---------|---|------|------|
| id | BIGSERIAL | 主キー | PRIMARY KEY |
| timestamp | TIMESTAMP | 判断時刻 | NOT NULL |
| symbol | VARCHAR(10) | 通貨ペア | NOT NULL |
| action | VARCHAR(10) | アクション（BUY/SELL/HOLD） | NOT NULL |
| confidence | DECIMAL(5, 2) | 信頼度（0-100%） | - |
| reasoning | TEXT | 判断理由 | - |
| market_data | JSONB | 判断時のマーケットデータ | - |
| created_at | TIMESTAMP | 作成日時 | DEFAULT CURRENT_TIMESTAMP |

**インデックス**:
- timestamp, symbol - 検索高速化

---

##### 4. positions（ポジションテーブル）

**用途**: オープン中および決済済みのポジション情報を管理

| カラム名 | 型 | 説明 | 制約 |
|---------|---|------|------|
| id | BIGSERIAL | 主キー | PRIMARY KEY |
| ticket | BIGINT | MT5チケット番号 | UNIQUE |
| symbol | VARCHAR(10) | 通貨ペア | NOT NULL |
| type | VARCHAR(10) | ポジションタイプ（BUY/SELL） | NOT NULL |
| volume | DECIMAL(10, 2) | ロット数 | NOT NULL |
| open_price | DECIMAL(10, 5) | エントリー価格 | NOT NULL |
| sl | DECIMAL(10, 5) | ストップロス | - |
| tp | DECIMAL(10, 5) | テイクプロフィット | - |
| open_time | TIMESTAMP | オープン時刻 | NOT NULL |
| close_time | TIMESTAMP | クローズ時刻 | - |
| close_price | DECIMAL(10, 5) | 決済価格 | - |
| profit | DECIMAL(10, 2) | 損益 | - |
| status | VARCHAR(20) | ステータス（OPEN/CLOSED） | NOT NULL |

**インデックス**:
- status, symbol, open_time - 検索高速化

---

##### 5. backtest_results（バックテスト結果テーブル）

**用途**: バックテスト実行結果を保存・分析

| カラム名 | 型 | 説明 | 制約 |
|---------|---|------|------|
| id | BIGSERIAL | 主キー | PRIMARY KEY |
| test_name | VARCHAR(100) | テスト名 | NOT NULL |
| start_date | DATE | テスト開始日 | NOT NULL |
| end_date | DATE | テスト終了日 | NOT NULL |
| total_trades | INTEGER | 総トレード数 | - |
| win_rate | DECIMAL(5, 2) | 勝率 | - |
| direction_accuracy | DECIMAL(5, 2) | 方向性精度（目標60%以上） | - |
| judgment_consistency | DECIMAL(5, 2) | 判断の一貫性（目標85%以上） | - |
| profit_factor | DECIMAL(10, 2) | プロフィットファクター | - |
| max_drawdown | DECIMAL(10, 2) | 最大ドローダウン | - |
| created_at | TIMESTAMP | 作成日時 | DEFAULT CURRENT_TIMESTAMP |

**インデックス**:
- created_at - 検索高速化

---

**データベースセットアップ方法**:
```bash
# PostgreSQLに接続
psql -U postgres

# データベース作成
CREATE DATABASE fx_autotrade;

# スキーマ適用
psql -U postgres -d fx_autotrade -f config/database_schema.sql

# テーブル確認
psql -U postgres -d fx_autotrade -c "\dt"
```

---

## テストモジュール

### test_tick_loader.py
**ファイルパス**: `tests/test_tick_loader.py`

**目的**: TickDataLoaderクラスの機能をテスト

#### テストケース一覧

##### 1. 初期化テスト
- **テスト関数**: `test_loader_initialization()`
- **確認内容**: インスタンスが正しく生成されるか

##### 2. 正常な読み込みテスト
- **テスト関数**: `test_load_from_zip_success()`
- **確認内容**:
  - データが正しく読み込まれるか
  - データ件数が正しいか
  - データ構造が正しいか（timestamp, bid, ask, volume）
  - 型変換が正しく行われているか（datetime, float, float, int）

##### 3. ファイル未検出テスト
- **テスト関数**: `test_load_from_zip_file_not_found()`
- **確認内容**: 存在しないファイルで`FileNotFoundError`が発生するか

##### 4. データバリデーション成功テスト
- **テスト関数**: `test_validate_data_success()`
- **確認内容**: 正常なデータがバリデーションを通過するか

##### 5. 空データバリデーションテスト
- **テスト関数**: `test_validate_data_empty()`
- **確認内容**: 空のデータリストがバリデーションで失敗するか

##### 6. 無効な価格バリデーションテスト
- **テスト関数**: `test_validate_data_invalid_price()`
- **確認内容**: 負の価格がバリデーションで失敗するか

##### 7. タイムスタンプパーステスト
- **テスト関数**: `test_timestamp_parsing()`
- **確認内容**: タイムスタンプが正しくdatetimeに変換されるか

##### 8. データ順序性テスト
- **テスト関数**: `test_data_order()`
- **確認内容**: データが時系列順に読み込まれるか

##### 9. Bid/Ask関係性テスト
- **テスト関数**: `test_bid_ask_relationship()`
- **確認内容**: Bid <= Ask の関係が保たれているか

**テスト実行方法**:
```bash
# 全テスト実行
pytest tests/test_tick_loader.py -v

# カバレッジ付き実行
pytest tests/test_tick_loader.py --cov=src.data_processing.tick_loader -v

# 特定のテストのみ実行
pytest tests/test_tick_loader.py::TestTickDataLoader::test_load_from_zip_success -v
```

**テストカバレッジ目標**: 80%以上

---

## フェーズ1完了基準

### チェックリスト

- [x] 全依存パッケージがインストール済み
- [x] ディレクトリ構造が正しく作成されている
- [x] データベーススキーマファイルが作成済み
- [x] zipファイルからティックデータを読み込めるモジュールが実装済み
- [x] ユニットテストが作成済み
- [x] 各モジュールに詳細なドキュメントが記載されている

### 次のステップ

フェーズ1が完了したら、以下の手順で次のフェーズに進んでください:

1. **データベースのセットアップ**:
   ```bash
   psql -U postgres -d fx_autotrade -f config/database_schema.sql
   ```

2. **依存パッケージのインストール**:
   ```bash
   pip install -r requirements.txt
   ```

3. **環境変数の設定**:
   ```bash
   cp .env.template .env
   # .envを編集して実際の値を設定
   ```

4. **テストの実行**:
   ```bash
   pytest tests/test_tick_loader.py -v
   ```

5. **フェーズ2の開始**:
   - 時間足変換の実装（timeframe_converter.py）
   - テクニカル指標の計算（technical_indicators.py）
   - データ標準化とJSON変換（data_standardizer.py）

---

## トラブルシューティング

### よくある問題と解決方法

#### 1. ティックデータが読み込めない
**問題**: `FileNotFoundError`が発生する
**解決方法**:
- ファイルパスが正しいか確認
- zipファイルが`data/tick_data/{symbol}/`に配置されているか確認
- ファイル名が正しいフォーマットか確認（`ticks_{symbol}-oj5k_{year:04d}-{month:02d}.zip`）

#### 2. データベース接続エラー
**問題**: PostgreSQLに接続できない
**解決方法**:
- PostgreSQLが起動しているか確認: `sudo systemctl status postgresql`
- `.env`ファイルの設定が正しいか確認
- データベース`fx_autotrade`が作成されているか確認

#### 3. テストが失敗する
**問題**: pytestでテストが失敗する
**解決方法**:
- 依存パッケージが全てインストールされているか確認
- Pythonバージョンが3.11以上か確認
- テストデータ（zipファイル）が正しいフォーマットか確認

---

## サポート情報

### ドキュメント参照先
- [FX自動トレード仕様書.md](/FX自動トレード仕様書.md)
- [開発ステップ.md](/開発ステップ.md)
- [docs/architecture/](/docs/architecture/) - アーキテクチャ仕様書
- [docs/basic_design/](/docs/basic_design/) - 基本設計書

### 連絡先
問題が発生した場合は、開発チームまでご連絡ください。

---

**ドキュメント作成日**: 2025-10-21
**最終更新日**: 2025-10-21
**バージョン**: 1.0.0
