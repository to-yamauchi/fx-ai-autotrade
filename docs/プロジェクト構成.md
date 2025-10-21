# FX自動トレードシステム - プロジェクト構造設計書

## ドキュメント情報
- **作成日**: 2025-10-21
- **バージョン**: 1.0
- **種別**: 実装設計書
- **対象読者**: 開発者

---

## 目次
1. [設計方針](#1-設計方針)
2. [ディレクトリ構造](#2-ディレクトリ構造)
3. [各モジュールの概要](#3-各モジュールの概要)
4. [モジュール間の依存関係](#4-モジュール間の依存関係)
5. [実行方法](#5-実行方法)
6. [開発ワークフロー](#6-開発ワークフロー)

---

## 1. 設計方針

### 1.1 基本コンセプト

**バッチ処理型モジュラーアーキテクチャ**

各アーキテクチャコンポーネントを独立したモジュールとして実装し、以下の特性を持たせる：

1. **独立実行可能性**: 各モジュールは単独でバッチ処理として実行できる
2. **疎結合**: モジュール間の依存を最小限に抑え、データベースやファイルを介して連携
3. **テスト容易性**: 各モジュールを独立してユニットテスト可能
4. **保守性**: モジュールごとにフォルダを分け、責務を明確化
5. **再利用性**: 共通機能はライブラリとして切り出し

### 1.2 モジュール分離の原則

#### 各モジュールの責務

| 原則 | 説明 | 実装方法 |
|------|------|---------|
| **単一責任** | 1モジュール = 1つの明確な責務 | アーキテクチャドキュメントの分類に従う |
| **明示的な入出力** | 入力と出力を明確に定義 | データベーステーブル、JSONファイル等 |
| **独立したエントリポイント** | 各モジュールに main() を持つ | `python -m <module>` で実行可能 |
| **共通基盤の活用** | 共通機能は lib/ に集約 | DB接続、ログ、設定管理等 |

#### モジュール間連携の方法

1. **データベース**: トランザクションデータ、AI判断履歴、設定等
2. **ファイル**: 標準化データJSON、ルールJSON等
3. **イベント**: 必要に応じてメッセージキュー（将来拡張）

### 1.3 Flaskとの違い

| 項目 | Flask型（モノリス） | 本設計（モジュラー） |
|------|-------------------|-------------------|
| **構造** | 1つのアプリケーション | 独立したモジュール群 |
| **実行方法** | アプリ起動で全機能稼働 | 必要なモジュールのみ実行 |
| **スケーリング** | 全体をスケール | モジュール単位でスケール |
| **開発** | 全機能を同時に扱う | モジュール単位で開発 |
| **テスト** | 統合テスト中心 | ユニットテスト容易 |
| **デプロイ** | 一括デプロイ | モジュール単位でデプロイ可 |

---

## 2. ディレクトリ構造

### 2.1 全体構成

```
fx-ai-autotrade/
│
├── docs/                           # ドキュメント
│   ├── ARCHITECTURE_OVERVIEW.md
│   ├── PROJECT_STRUCTURE.md        # 本ドキュメント
│   ├── DEVELOPMENT_TASKS.md        # 開発タスク詳細
│   ├── architecture/               # 詳細設計書
│   └── basic_design/               # 基本設計書
│
├── src/                            # ソースコード
│   │
│   ├── lib/                        # 共通ライブラリ
│   │   ├── __init__.py
│   │   ├── database/               # データベース関連
│   │   │   ├── __init__.py
│   │   │   ├── connection.py      # DB接続管理
│   │   │   ├── models.py           # データモデル (SQLAlchemy)
│   │   │   └── repositories/       # リポジトリパターン
│   │   │       ├── __init__.py
│   │   │       ├── trade.py
│   │   │       ├── ai_decision.py
│   │   │       └── market_data.py
│   │   │
│   │   ├── mt5/                    # MT5共通機能
│   │   │   ├── __init__.py
│   │   │   ├── connector.py        # MT5接続管理
│   │   │   └── data_fetcher.py     # データ取得共通処理
│   │   │
│   │   ├── config/                 # 設定管理
│   │   │   ├── __init__.py
│   │   │   ├── settings.py         # 設定読み込み
│   │   │   └── constants.py        # 定数定義
│   │   │
│   │   ├── utils/                  # ユーティリティ
│   │   │   ├── __init__.py
│   │   │   ├── logger.py           # ロギング
│   │   │   ├── date_utils.py       # 日時処理
│   │   │   └── validation.py       # バリデーション
│   │   │
│   │   └── exceptions/             # カスタム例外
│   │       ├── __init__.py
│   │       └── custom_exceptions.py
│   │
│   ├── modules/                    # モジュール群
│   │   │
│   │   ├── data_processing/        # データ処理エンジン
│   │   │   ├── __init__.py
│   │   │   ├── __main__.py         # エントリポイント
│   │   │   ├── processor.py        # メイン処理
│   │   │   ├── timeframe_converter.py
│   │   │   ├── indicator_calculator.py
│   │   │   ├── data_normalizer.py
│   │   │   └── tests/
│   │   │       ├── __init__.py
│   │   │       ├── test_processor.py
│   │   │       └── test_indicator.py
│   │   │
│   │   ├── ai_analysis/            # AI分析エンジン
│   │   │   ├── __init__.py
│   │   │   ├── __main__.py
│   │   │   ├── analyzer.py
│   │   │   ├── prompt_builder.py
│   │   │   ├── gemini_client.py
│   │   │   ├── rule_generator.py
│   │   │   └── tests/
│   │   │
│   │   ├── rule_engine/            # ルールエンジン
│   │   │   ├── __init__.py
│   │   │   ├── __main__.py
│   │   │   ├── engine.py
│   │   │   ├── layer1_emergency.py
│   │   │   ├── layer2_anomaly.py
│   │   │   ├── layer3_ai_eval.py
│   │   │   ├── entry_monitor.py
│   │   │   ├── exit_monitor.py
│   │   │   └── tests/
│   │   │
│   │   ├── trade_execution/        # トレード実行
│   │   │   ├── __init__.py
│   │   │   ├── __main__.py
│   │   │   ├── executor.py
│   │   │   ├── position_sizer.py
│   │   │   ├── order_manager.py
│   │   │   └── tests/
│   │   │
│   │   ├── risk_management/        # リスク管理
│   │   │   ├── __init__.py
│   │   │   ├── __main__.py
│   │   │   ├── risk_monitor.py
│   │   │   ├── drawdown_manager.py
│   │   │   └── tests/
│   │   │
│   │   ├── backtest/               # バックテスト
│   │   │   ├── __init__.py
│   │   │   ├── __main__.py
│   │   │   ├── backtester.py
│   │   │   ├── historical_data.py
│   │   │   ├── report_generator.py
│   │   │   └── tests/
│   │   │
│   │   └── scheduler/              # スケジューラ
│   │       ├── __init__.py
│   │       ├── __main__.py
│   │       ├── scheduler.py
│   │       ├── job_manager.py
│   │       └── tests/
│   │
│   └── orchestrator/               # 統合オーケストレーター（オプション）
│       ├── __init__.py
│       ├── __main__.py
│       └── main.py                 # 全モジュール統合実行
│
├── data/                           # データディレクトリ
│   ├── market/                     # 市場データ
│   ├── rules/                      # AI生成ルールJSON
│   ├── backtest/                   # バックテスト結果
│   └── logs/                       # ログファイル
│
├── config/                         # 設定ファイル
│   ├── settings.yaml               # 環境設定
│   ├── database.yaml               # DB設定
│   ├── mt5.yaml                    # MT5設定
│   └── secrets.yaml.example        # シークレット（テンプレート）
│
├── scripts/                        # 運用スクリプト
│   ├── setup/                      # セットアップ
│   │   ├── init_database.py
│   │   └── install_dependencies.sh
│   ├── batch/                      # バッチ実行スクリプト
│   │   ├── run_data_processing.sh
│   │   ├── run_ai_analysis.sh
│   │   └── run_backtest.sh
│   └── utils/                      # ユーティリティ
│       ├── backup_database.sh
│       └── clean_logs.sh
│
├── tests/                          # 統合テスト
│   ├── integration/
│   │   ├── test_data_to_ai.py
│   │   └── test_full_workflow.py
│   └── fixtures/                   # テストデータ
│
├── requirements.txt                # Python依存パッケージ
├── requirements-dev.txt            # 開発用依存パッケージ
├── setup.py                        # パッケージ設定
├── pytest.ini                      # pytest設定
├── .env.example                    # 環境変数テンプレート
├── .gitignore
└── README.md
```

### 2.2 主要ディレクトリの役割

| ディレクトリ | 役割 | 備考 |
|------------|------|------|
| **src/lib/** | 共通ライブラリ | 全モジュールから利用される基盤機能 |
| **src/modules/** | 独立モジュール群 | 各アーキテクチャの実装 |
| **data/** | データ保存 | 市場データ、ルール、ログ等 |
| **config/** | 設定ファイル | YAML形式の設定 |
| **scripts/** | 運用スクリプト | セットアップ、バッチ実行等 |
| **tests/** | 統合テスト | モジュール間の連携テスト |

---

## 3. 各モジュールの概要

### 3.1 データ処理エンジン (data_processing)

#### 責務
- MT5からの市場データ取得
- 時間足変換
- テクニカル指標計算
- 標準化データJSON生成

#### 入力
- MT5 API経由の市場データ
- 設定ファイル (config/mt5.yaml)

#### 出力
- 標準化データJSON (data/market/)
- データベース (market_data テーブル)

#### 実行方法
```bash
# 単独実行
python -m src.modules.data_processing

# オプション指定
python -m src.modules.data_processing --symbol USDJPY --save-db
```

#### テスト
```bash
pytest src/modules/data_processing/tests/
```

---

### 3.2 AI分析エンジン (ai_analysis)

#### 責務
- 前日振り返り分析
- 朝の詳細市場分析
- 定期更新分析
- ポジション評価
- ルールJSON生成

#### 入力
- 標準化データJSON (data/market/)
- 前日のトレード記録 (データベース)
- 既存ルールJSON (data/rules/)

#### 出力
- ルールJSON (data/rules/)
- AI判断履歴 (データベース)

#### 実行方法
```bash
# 朝の分析
python -m src.modules.ai_analysis --mode morning

# 定期更新
python -m src.modules.ai_analysis --mode update

# 振り返り
python -m src.modules.ai_analysis --mode review
```

#### テスト
```bash
pytest src/modules/ai_analysis/tests/
```

---

### 3.3 ルールエンジン (rule_engine)

#### 責務
- 3層監視システムの運用
- エントリー条件の監視
- 決済条件の監視
- 緊急停止判断

#### 入力
- ルールJSON (data/rules/)
- リアルタイム市場データ (MT5 API)
- ポジション情報 (データベース)

#### 出力
- トレード実行指示 (データベース)
- 監視ログ (data/logs/)

#### 実行方法
```bash
# デーモンとして実行
python -m src.modules.rule_engine --daemon

# 単発チェック
python -m src.modules.rule_engine --check-once
```

#### テスト
```bash
pytest src/modules/rule_engine/tests/
```

---

### 3.4 トレード実行 (trade_execution)

#### 責務
- MT5への注文実行
- ポジションサイズ計算
- ストップロス設定
- トレード記録

#### 入力
- トレード実行指示 (データベース)
- ルールJSON (data/rules/)

#### 出力
- MT5注文
- トレード記録 (データベース)

#### 実行方法
```bash
# 実行待機
python -m src.modules.trade_execution --monitor

# 手動実行（テスト用）
python -m src.modules.trade_execution --manual --direction BUY
```

#### テスト
```bash
pytest src/modules/trade_execution/tests/
```

---

### 3.5 リスク管理 (risk_management)

#### 責務
- ドローダウン監視
- ポジションサイズ調整
- 週次・月次レビュー
- 緊急停止判断

#### 入力
- トレード記録 (データベース)
- 口座情報 (MT5 API)

#### 出力
- リスクアラート (データベース)
- レビューレポート (data/reports/)

#### 実行方法
```bash
# リスク監視
python -m src.modules.risk_management --monitor

# 週次レビュー
python -m src.modules.risk_management --weekly-review
```

#### テスト
```bash
pytest src/modules/risk_management/tests/
```

---

### 3.6 バックテスト (backtest)

#### 責務
- 過去データでのAI判断再現
- 再現性検証
- パフォーマンス評価
- レポート生成

#### 入力
- 過去の市場データ (データベース)
- 設定 (config/backtest.yaml)

#### 出力
- バックテスト結果 (data/backtest/)
- 評価レポート (data/reports/)

#### 実行方法
```bash
# 期間指定実行
python -m src.modules.backtest --start 2024-09-01 --end 2024-09-30

# レポート生成
python -m src.modules.backtest --generate-report
```

#### テスト
```bash
pytest src/modules/backtest/tests/
```

---

### 3.7 スケジューラ (scheduler)

#### 責務
- 定時実行制御
- 週末停止・再開
- モジュール起動管理

#### 入力
- スケジュール設定 (config/schedule.yaml)

#### 出力
- モジュール実行ログ (data/logs/)

#### 実行方法
```bash
# スケジューラ起動
python -m src.modules.scheduler --start

# スケジュール確認
python -m src.modules.scheduler --list-jobs
```

#### テスト
```bash
pytest src/modules/scheduler/tests/
```

---

## 4. モジュール間の依存関係

### 4.1 依存グラフ

```
MT5 API
   ↓
[data_processing] → 標準化データJSON → [ai_analysis]
                         ↓                      ↓
                    データベース           ルールJSON
                         ↓                      ↓
                  [rule_engine] ← ─ ─ ─ ─ ─ ─ ┘
                         ↓
                  実行指示
                         ↓
                [trade_execution] → MT5注文
                         ↓
                  トレード記録
                         ↓
              [risk_management] → アラート・レポート

[scheduler] → 全モジュールの起動制御

[backtest] ← 過去データ (独立実行)
```

### 4.2 依存関係の種類

| 依存の種類 | 説明 | 実装方法 |
|-----------|------|---------|
| **データ依存** | あるモジュールの出力が別モジュールの入力 | ファイル、データベース |
| **ライブラリ依存** | 共通機能の利用 | src/lib/ のインポート |
| **実行依存** | あるモジュールの実行が前提 | スケジューラで制御 |

### 4.3 疎結合の実現

#### データベーステーブルを介した連携

各モジュールは以下のテーブルを共有：

| テーブル | 書き込み | 読み込み |
|---------|---------|---------|
| **market_data** | data_processing | ai_analysis, backtest |
| **ai_decisions** | ai_analysis | rule_engine, backtest |
| **trades** | trade_execution | risk_management, backtest |
| **positions** | trade_execution | rule_engine, risk_management |
| **risk_alerts** | risk_management | scheduler |

#### ファイルを介した連携

| ファイル | 生成 | 利用 |
|---------|------|------|
| **標準化データJSON** | data_processing | ai_analysis |
| **ルールJSON** | ai_analysis | rule_engine |
| **バックテストレポート** | backtest | - |

---

## 5. 実行方法

### 5.1 開発環境での実行

#### 1. 環境セットアップ

```bash
# 仮想環境作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存パッケージインストール
pip install -r requirements.txt
pip install -r requirements-dev.txt

# データベース初期化
python scripts/setup/init_database.py

# 設定ファイルコピー
cp config/secrets.yaml.example config/secrets.yaml
# secrets.yaml を編集してAPI キー等を設定
```

#### 2. 個別モジュール実行

```bash
# データ処理
python -m src.modules.data_processing

# AI分析（朝）
python -m src.modules.ai_analysis --mode morning

# ルールエンジン（単発チェック）
python -m src.modules.rule_engine --check-once
```

#### 3. 統合実行（オプション）

```bash
# オーケストレーターで全モジュール起動
python -m src.orchestrator
```

### 5.2 本番環境での実行

#### systemdサービスとして登録（Linux）

```bash
# スケジューラをサービス化
sudo cp scripts/systemd/fx-scheduler.service /etc/systemd/system/
sudo systemctl enable fx-scheduler
sudo systemctl start fx-scheduler
```

#### cronで定期実行

```bash
# crontab編集
crontab -e

# 朝の分析（8:00）
0 8 * * * /path/to/venv/bin/python -m src.modules.ai_analysis --mode morning

# 定期更新（12:00, 16:00, 21:30）
0 12,16 * * * /path/to/venv/bin/python -m src.modules.ai_analysis --mode update
30 21 * * * /path/to/venv/bin/python -m src.modules.ai_analysis --mode update
```

---

## 6. 開発ワークフロー

### 6.1 新規モジュール開発手順

1. **モジュールディレクトリ作成**
   ```bash
   mkdir -p src/modules/new_module/tests
   ```

2. **基本ファイル作成**
   - `__init__.py`: モジュール初期化
   - `__main__.py`: エントリポイント
   - `processor.py`: メイン処理
   - `tests/test_processor.py`: テスト

3. **共通ライブラリ活用**
   ```python
   from src.lib.database import get_db_connection
   from src.lib.utils.logger import get_logger
   ```

4. **テスト作成**
   ```bash
   pytest src/modules/new_module/tests/
   ```

5. **ドキュメント更新**
   - README.md に使用方法追加
   - 本ドキュメントに概要追加

### 6.2 テスト戦略

#### ユニットテスト
- 各モジュール内で完結するテスト
- モックを活用して外部依存を排除

#### 統合テスト
- 複数モジュールの連携をテスト
- テストデータベースを使用

#### エンドツーエンドテスト
- 全体フローをテスト
- デモ口座で実行

### 6.3 継続的インテグレーション

```yaml
# .github/workflows/ci.yml (例)
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.10
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      - name: Run tests
        run: pytest tests/
```

---

## 7. まとめ

### 7.1 設計の利点

1. **独立開発**: 各モジュールを並行して開発可能
2. **テスト容易**: モジュール単位でテスト実行
3. **段階的デプロイ**: 完成したモジュールから順次デプロイ
4. **保守性**: 責務が明確で変更の影響範囲が限定的
5. **スケーラビリティ**: 負荷の高いモジュールのみスケール可能

### 7.2 次のステップ

1. 共通ライブラリ (src/lib/) の実装
2. データベーススキーマの設計と実装
3. 各モジュールの順次実装（Phase 1から）
4. 統合テストの実施

---

**本設計に基づき、モジュール単位で段階的に開発を進めます。**
