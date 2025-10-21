# データ処理エンジン仕様書

## ドキュメント情報
- **作成日**: 2025-10-21
- **バージョン**: 1.0
- **カテゴリ**: システムアーキテクチャ - データ層

---

## 1. 概要

### 1.1 役割

市場データの取得と標準化を担当する、システムの基礎層となるコンポーネント

### 1.2 位置づけ

```
MT5 → 【データ処理エンジン】 → AI分析エンジン → ルールエンジン → MT5
```

### 1.3 設計原則

- **確定性**: 同じ入力から常に同じ出力を生成
- **再現性**: バックテストで過去データを完全に再現可能
- **標準化**: AIが解釈しやすい統一フォーマット

---

## 2. 主要機能

### 2.1 ティックデータ取得

#### 2.1.1 データソースの選択

**バックテスト/モデル作成モード（推奨）**:
- **データソース**: 月単位zipファイル（中身はcsvファイル）
- **保存場所**: `data/tick_data/USDJPY/`
- **ファイル命名規則**:
  - zip: `ticks_USDJPY-oj5k_yyyy-mm.zip`
  - csv: `ticks_USDJPY-oj5k_yyyy-mm.csv`（zip内）
  - 例: `ticks_USDJPY-oj5k_2024-09.zip` → `ticks_USDJPY-oj5k_2024-09.csv`
- **CSV形式**:
  ```csv
  timestamp,bid,ask,volume
  2024-09-01 00:00:00.123,149.650,149.653,100
  2024-09-01 00:00:00.234,149.651,149.654,150
  2024-09-01 00:00:00.345,149.649,149.652,80
  ```
- **フィールド説明**:
  - timestamp: ティックのタイムスタンプ（ミリ秒精度）
  - bid: 買値
  - ask: 売値
  - volume: ティック数
- **用途**: AI学習、バックテスト、戦略検証

**リアルタイムトレードモード**:
- **データソース**: MT5 API（MetaTrader5 Python API）
- **対象通貨ペア**: USDJPY（Phase 1-4）
- **取得頻度**:
  - リアルタイム（価格変動ごと）
  - Layer 1監視用（100ms間隔）
- **データ項目**:
  - bid（買値）
  - ask（売値）
  - last（最終約定価格）
  - volume（出来高）
  - time（タイムスタンプ）
- **用途**: 実運用時のエントリー/決済判断、Layer 1監視

#### 2.1.2 zipファイルの処理

**zip展開処理**:
```python
import zipfile
import csv
from datetime import datetime

def load_tick_data_from_zip(zip_path):
    """
    zipファイルからティックデータを読み込む

    Args:
        zip_path: zipファイルのパス
                  例: data/tick_data/USDJPY/ticks_USDJPY-oj5k_2024-09.zip

    Returns:
        list: ティックデータのリスト
    """
    tick_data = []

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        # zip内のcsvファイルを取得
        # ファイル名: ticks_USDJPY-oj5k_2024-09.csv
        csv_files = [f for f in zip_ref.namelist() if f.endswith('.csv')]

        for csv_file in csv_files:
            with zip_ref.open(csv_file) as f:
                reader = csv.DictReader(io.TextIOWrapper(f, 'utf-8'))
                for row in reader:
                    tick = {
                        'time': datetime.fromisoformat(row['timestamp']),
                        'bid': float(row['bid']),
                        'ask': float(row['ask']),
                        'volume': int(row['volume'])
                    }
                    tick_data.append(tick)

    return tick_data
```

**月単位データの管理**:
- バックテスト期間に応じて複数の月のzipファイルを自動読み込み
- メモリ効率を考慮し、必要な期間のみをロード
- キャッシュ機構により再読み込みを削減

#### 2.1.3 MT5接続管理（リアルタイムモード）

**技術**:
- MetaTrader5 Python API
- 自動再接続機能
- タイムアウト処理（10秒）

**エラーハンドリング**:
```python
# 接続エラー時の対応
1. 3回まで再接続試行（1秒間隔）
2. 失敗時はアラート送信
3. Layer 1は独立稼働（保護継続）
```

### 2.2 時間足変換

#### 2.2.1 対象時間足

| 時間足 | 取得本数 | 主な用途 |
|--------|----------|----------|
| 日足（D1） | 過去30本 | 長期トレンド判定、サポレジ算出 |
| 4時間足（H4） | 過去50本 | 中期トレンド確認、EMA配列確認 |
| 1時間足（H1） | 過去100本 | メイン分析時間軸、エントリー判定 |
| 15分足（M15） | 過去100本 | 短期シグナル、最終エントリー判断 |

#### 2.2.2 OHLC生成

**処理**:
- ティックデータから各時間足のOHLC（始値・高値・安値・終値）を生成
- タイムゾーン: MT5サーバー時刻（通常GMT+2/+3）
- 完成確認: 現在の足は未完成として扱う

**データ構造**:
```json
{
  "time": "2025-10-20 15:00:00",
  "open": 149.650,
  "high": 149.680,
  "low": 149.640,
  "close": 149.670,
  "volume": 1250,
  "spread": 0.8
}
```

### 2.3 テクニカル指標計算

#### 2.3.1 トレンド系指標

**EMA（指数移動平均線）**:
- EMA(20): 短期トレンド
- EMA(50): 中期トレンド
- 計算: 各時間足（D1, H4, H1, M15）で算出
- 用途: トレンド方向の判定、配列確認

**MACD（Moving Average Convergence Divergence）**:
- パラメータ: (12, 26, 9)
- 算出値: MACD線、シグナル線、ヒストグラム
- 用途: モメンタム確認、クロスシグナル

#### 2.3.2 オシレーター系指標

**RSI（相対力指数）**:
- パラメータ: 14期間
- 範囲: 0〜100
- 用途: 過熱感の判定（>70: 買われすぎ, <30: 売られすぎ）

**ストキャスティクス**:
- パラメータ: (5, 3, 3)
- 算出値: %K、%D
- 用途: 補助的な売買シグナル

#### 2.3.3 ボラティリティ系指標

**ATR（Average True Range）**:
- パラメータ: 14期間
- 用途: ポジションサイズ調整、ストップロス設定

**ボリンジャーバンド**:
- パラメータ: (20, 2σ)
- 算出値: 上限、中央線、下限
- 用途: レンジ判定、ブレイクアウト検知

#### 2.3.4 サポート/レジスタンス

**高値・安値分析**:
- 過去20日の高値・安値
- スイングハイ・スイングロー
- フラクタルパターン

**ピボットポイント**:
- 標準ピボット: (H + L + C) / 3
- レジスタンス: R1, R2, R3
- サポート: S1, S2, S3

**フィボナッチリトレースメント**:
- 主要レベル: 23.6%, 38.2%, 50%, 61.8%
- 直近の重要な高値・安値から算出

### 2.4 データ標準化

#### 2.4.1 標準フォーマット

AIに渡すデータは以下の構造を持つJSON:

```json
{
  "metadata": {
    "timestamp": "2025-10-20 08:00:00",
    "symbol": "USDJPY",
    "current_price": 149.650,
    "data_hash": "abc123...",
    "generation_time_ms": 1250
  },

  "market_structure": {
    "daily_trend": {
      "direction": "下降",
      "strength": "中程度",
      "ema_alignment": "弱気配列",
      "recent_pattern": "レンジ形成中",
      "confidence": 0.75
    },
    "h4_trend": {
      "direction": "横ばい",
      "strength": "弱い",
      "ema_alignment": "混在",
      "recent_pattern": "方向感なし"
    },
    "h1_trend": {
      "direction": "下降",
      "strength": "中程度",
      "ema_alignment": "弱気配列"
    },
    "m15_trend": {
      "direction": "横ばい",
      "strength": "弱い",
      "recent_pattern": "狭いレンジ"
    }
  },

  "technical_summary": {
    "ema": {
      "h1_ema20": 149.580,
      "h1_ema50": 149.720,
      "alignment": "弱気配列",
      "distance": "14pips差",
      "trend_strength": "中程度"
    },
    "rsi": {
      "h1": 45.2,
      "m15": 48.5,
      "interpretation": "中立圏",
      "divergence": "なし"
    },
    "macd": {
      "h1_value": -0.025,
      "h1_signal": -0.018,
      "histogram": -0.007,
      "trend": "弱気",
      "recent_cross": "なし"
    },
    "bollinger": {
      "h1_upper": 149.75,
      "h1_middle": 149.65,
      "h1_lower": 149.55,
      "width": "狭い",
      "position": "中央付近"
    },
    "atr": {
      "h1_value": 0.150,
      "interpretation": "ボラティリティ低め",
      "pips": 15
    }
  },

  "key_levels": {
    "support": [149.50, 149.20, 149.00],
    "resistance": [149.70, 149.90, 150.20],
    "pivot": {
      "pivot": 149.60,
      "r1": 149.70,
      "r2": 149.85,
      "s1": 149.45,
      "s2": 149.30
    },
    "fibonacci": {
      "swing_high": 149.90,
      "swing_low": 149.30,
      "levels": {
        "23.6%": 149.76,
        "38.2%": 149.67,
        "50.0%": 149.60,
        "61.8%": 149.53
      }
    }
  },

  "recent_price_action": {
    "h1_last_3": [
      {"time": "13:00", "pattern": "陰線", "size": "小", "comment": "方向感なし"},
      {"time": "14:00", "pattern": "陽線", "size": "小", "comment": "小反発"},
      {"time": "15:00", "pattern": "十字線", "size": "極小", "comment": "膠着"}
    ],
    "m15_last_5": [
      {"time": "14:00", "pattern": "陰線", "change_pips": -3},
      {"time": "14:15", "pattern": "陽線", "change_pips": 2},
      {"time": "14:30", "pattern": "陰線", "change_pips": -2},
      {"time": "14:45", "pattern": "陽線", "change_pips": 1},
      {"time": "15:00", "pattern": "十字線", "change_pips": 0}
    ],
    "summary": "狭いレンジ、方向感なし、ボラティリティ低下"
  },

  "volume_analysis": {
    "h1_average": 1200,
    "h1_current": 950,
    "trend": "減少傾向",
    "interpretation": "関心低下、様子見ムード"
  },

  "session_info": {
    "current_session": "東京後場",
    "next_session": "欧州市場",
    "session_overlap": false,
    "typical_volatility": "低い"
  }
}
```

#### 2.4.2 データハッシュ

**目的**: 再現性の確保

**計算方法**:
```python
import hashlib
import json

def generate_data_hash(market_data):
    # メタデータを除外
    data_copy = market_data.copy()
    del data_copy['metadata']

    # 正規化してハッシュ化
    json_str = json.dumps(data_copy, sort_keys=True)
    return hashlib.sha256(json_str.encode()).hexdigest()[:16]
```

**用途**:
- バックテストでの同一性確認
- データ整合性チェック
- 再計算の必要性判定

### 2.5 データ品質管理

#### 2.5.1 異常値検出

**チェック項目**:
1. スプレッド異常（>20pips）
2. 価格の急激な変動（0.1秒で30pips以上）
3. データ欠損（取得失敗）
4. タイムスタンプの不整合

**対応**:
- 異常値を記録
- Layer 1に警告
- AI分析に異常フラグを付与

#### 2.5.2 データ完全性

**検証**:
- 全時間足のデータが揃っているか
- 全指標が計算できているか
- 欠損値がないか

**不完全時の対応**:
- エントリー判断を一時停止
- Layer 1は継続稼働
- 復旧後に再開

---

## 3. データフロー

### 3.1 リアルタイム処理（実運用モード）

```
【100msごと】
MT5 → ティック取得 → Layer 1緊急停止監視

【1分ごと】
MT5 → 時間足更新チェック
    → 更新あり → テクニカル指標再計算
                → 標準化データ更新
                → ルールエンジンへ通知

【スケジュール時刻】
標準化データ生成 → AI分析エンジンへ渡す
```

### 3.2 バックテスト処理（モデル作成モード）

```
【指定日時ごと】
zipファイルからティックデータ読み込み
  ↓
月単位データを期間に応じて結合
  ↓
時間足変換（D1, H4, H1, M15）
  ↓
テクニカル指標計算
  ↓
標準化データ生成
  ↓
データハッシュ計算
  ↓
保存（再利用可能）
  ↓
AI分析/バックテスト実行
```

**zipファイル読み込みフロー**:
```
指定期間: 2024-09-01 〜 2024-10-31

1. 該当する月のzipファイルを特定
   - ticks_USDJPY-oj5k_2024-09.zip
   - ticks_USDJPY-oj5k_2024-10.zip

2. 各zipファイルを順次読み込み
   - 展開してcsvデータを取得
     - ticks_USDJPY-oj5k_2024-09.csv
     - ticks_USDJPY-oj5k_2024-10.csv
   - メモリ効率を考慮し、チャンク読み込みも可能

3. 時系列順にソート・結合

4. 時間足変換処理へ
```

---

## 4. パフォーマンス要件

### 4.1 処理速度

- **ティック取得**: 100ms以内
- **時間足変換**: 500ms以内
- **テクニカル指標計算**: 1秒以内
- **標準化データ生成**: 1.5秒以内
- **合計**: 3秒以内（目標）

### 4.2 信頼性

- **データ取得成功率**: 99.5%以上
- **接続復旧時間**: 3秒以内
- **稼働率**: 99%以上

---

## 5. エラーハンドリング

### 5.1 接続エラー

**発生時**:
1. 自動再接続（3回まで、1秒間隔）
2. 失敗時はアラート
3. Layer 1は独立稼働継続

### 5.2 データ取得エラー

**発生時**:
1. 直近の正常データを使用
2. 異常フラグを付与
3. エントリー判断を一時停止

### 5.3 計算エラー

**発生時**:
1. エラー内容を記録
2. 該当指標を除外
3. 可能な範囲で処理継続

---

## 6. データ保持戦略

### 6.1 データ保持の設計方針

リアルタイム運用時、**メモリ効率**と**応答速度**を両立するため、以下の3層でデータを管理：

1. **メモリ（常時保持）**: 頻繁にアクセスするデータ
2. **メモリ（一時保持）**: 処理中のみ必要なデータ
3. **DB（永続化）**: 履歴・分析用データ

---

### 6.2 メモリ常時保持データ

**目的**: Layer 1監視、エントリー/決済判断に必要な最新データ

| データ種別 | 保持内容 | 更新頻度 | メモリサイズ目安 |
|-----------|---------|---------|---------------|
| **現在ティック** | 最新の bid/ask/time | 100ms | 数十バイト |
| **時間足データ** | D1(30本), H4(50本), H1(100本), M15(100本) | 1分 | 約50KB |
| **テクニカル指標** | EMA, RSI, MACD等の最新値 | 1分 | 約10KB |
| **標準化データJSON** | 最新の市場状況サマリー | 1分 | 約20KB |
| **現在のルールJSON** | AI生成の最新トレードルール | 定時更新時 | 約10KB |
| **ポジション情報** | エントリー価格、時刻、ロット等 | ポジション変動時 | 数KB |

**合計メモリ使用量**: 約100KB（非常に軽量）

**実装イメージ**:
```python
class MarketDataCache:
    def __init__(self):
        # 常時保持データ
        self.current_tick = None  # 最新ティック
        self.timeframes = {
            'D1': [],   # 30本
            'H4': [],   # 50本
            'H1': [],   # 100本
            'M15': []   # 100本
        }
        self.indicators = {}  # テクニカル指標
        self.standardized_data = None  # 標準化JSON
        self.current_rules = None  # AI生成ルール
        self.positions = []  # 保有ポジション

    def update_tick(self, tick):
        """100msごとに呼ばれる（古いティックは破棄）"""
        self.current_tick = tick

    def update_timeframes(self):
        """1分ごとに呼ばれる"""
        self.timeframes['M15'] = fetch_from_mt5('M15', 100)
        self.timeframes['H1'] = fetch_from_mt5('H1', 100)
        # ... 以下同様
        self._recalculate_indicators()
        self._regenerate_standardized_data()
```

---

### 6.3 一時保持データ（処理中のみ）

**目的**: データ処理・計算中の中間データ（処理完了後は破棄）

| データ種別 | 使用タイミング | 保持期間 | 目的 |
|-----------|--------------|---------|------|
| **バックテスト用ティック** | zipファイル読み込み時 | 処理中のみ | 時間足変換・検証用 |
| **計算中の配列** | テクニカル指標計算時 | 数秒 | EMA/RSI等の計算 |
| **一時JSON** | AI分析直前 | 数秒 | Gemini送信前の最終整形 |

**実装イメージ**:
```python
def process_backtest_month(zip_path):
    """バックテスト実行時"""
    # 一時的にティックデータをロード
    tick_data = load_tick_data_from_zip(zip_path)  # メモリに展開

    # 処理
    timeframes = convert_to_timeframes(tick_data)
    indicators = calculate_indicators(timeframes)

    # 結果をDBに保存
    save_to_db(timeframes, indicators)

    # ティックデータは破棄（関数終了でメモリ解放）
    del tick_data
```

---

### 6.4 DB永続化データ

**目的**: 履歴分析、バックテスト検証、トレード記録

| データ種別 | 保存タイミング | 保存期間 | 用途 |
|-----------|--------------|---------|------|
| **トレード記録** | エントリー/決済時 | 永久 | 実績分析、税務 |
| **AI判断履歴** | AI実行時（1日5-10回） | 永久 | 判断精度の検証 |
| **ルールJSON履歴** | ルール更新時 | 永久 | 戦略の変遷追跡 |
| **市場データスナップショット** | AI実行時 | 永久 | 再現性確保 |
| **バックテスト結果** | バックテスト完了時 | 永久 | 戦略評価 |
| **異常検知ログ** | 異常発生時 | 永久 | トラブルシューティング |

**データベーススキーマ例**:
```sql
-- トレード記録
CREATE TABLE trades (
    id INTEGER PRIMARY KEY,
    entry_time TIMESTAMP,
    exit_time TIMESTAMP,
    symbol VARCHAR(10),
    direction VARCHAR(4),  -- BUY/SELL
    entry_price DECIMAL(10,5),
    exit_price DECIMAL(10,5),
    lots DECIMAL(5,2),
    profit_loss DECIMAL(10,2),
    rule_json TEXT,  -- 使用したルールJSON
    market_data_hash VARCHAR(32)  -- 市場データの同一性確認用
);

-- AI判断履歴
CREATE TABLE ai_analysis_history (
    id INTEGER PRIMARY KEY,
    timestamp TIMESTAMP,
    analysis_type VARCHAR(50),  -- 'morning_analysis', 'position_review'等
    model_used VARCHAR(50),  -- 'gemini-2.5-pro'等
    input_data TEXT,  -- 標準化データJSON
    output_rules TEXT,  -- ルールJSON
    data_hash VARCHAR(32)
);
```

---

### 6.5 データ更新・破棄タイミング

#### 6.5.1 100msごと（Layer 1監視）

```python
while True:
    # 最新ティック取得
    tick = mt5.symbol_info_tick("USDJPY")

    # メモリの現在ティックを更新（上書き）
    cache.update_tick(tick)

    # Layer 1チェック
    if check_emergency_conditions(tick):
        execute_emergency_close()

    sleep(0.1)  # 100ms待機
```

**保持**: 最新ティック1件のみ（古いティックは破棄）

---

#### 6.5.2 1分ごと（時間足・指標更新）

```python
if every_minute():
    # MT5から最新時間足を取得
    cache.timeframes['M15'] = mt5.copy_rates_from_pos("USDJPY", M15, 0, 100)
    cache.timeframes['H1'] = mt5.copy_rates_from_pos("USDJPY", H1, 0, 100)
    cache.timeframes['H4'] = mt5.copy_rates_from_pos("USDJPY", H4, 0, 50)
    cache.timeframes['D1'] = mt5.copy_rates_from_pos("USDJPY", D1, 0, 30)

    # テクニカル指標を再計算
    cache.indicators = calculate_all_indicators(cache.timeframes)

    # 標準化データJSONを再生成
    cache.standardized_data = generate_standardized_json(
        cache.timeframes,
        cache.indicators
    )
```

**保持**: 指定本数のみ（M15は100本、古いものは自動的に削除）

---

#### 6.5.3 定時AI分析時（08:00, 12:00等）

```python
if current_time in ANALYSIS_SCHEDULE:
    # メモリの最新標準化データを使用
    standardized_data = cache.standardized_data

    # AI分析実行
    rules = gemini_api.analyze(standardized_data)

    # ルールJSONをメモリに保持（上書き）
    cache.current_rules = rules

    # DBに履歴として保存
    db.save_ai_analysis(
        timestamp=now(),
        input_data=standardized_data,
        output_rules=rules
    )
```

**保持**:
- メモリ: 最新ルールJSON 1件
- DB: 全履歴を永続化

---

#### 6.5.4 ポジション保有時（15分ごと評価）

```python
if has_position() and every_15_minutes():
    # 簡易データ生成（軽量化）
    position_summary = {
        'entry_price': cache.positions[0].entry_price,
        'current_price': cache.current_tick.bid,
        'pnl': calculate_pnl(),
        'holding_minutes': get_holding_time(),
        'recent_m15': cache.timeframes['M15'][-5:],  # 直近5本のみ
        'key_indicators': {
            'rsi': cache.indicators['rsi']['h1'],
            'ema_trend': cache.indicators['ema']['h1_alignment']
        }
    }

    # Flash-Lite で評価
    evaluation = gemini_flash_lite.evaluate(position_summary)

    # DB保存（トラブル時の追跡用）
    db.save_position_evaluation(evaluation)
```

**保持**:
- メモリ: ポジション情報のみ
- DB: 評価履歴を永続化

---

### 6.6 バックテストモード時のデータ管理

```python
def run_backtest(start_date, end_date):
    """バックテスト実行"""

    # 必要な月のzipファイルを特定
    zip_files = get_zip_files_for_period(start_date, end_date)

    for zip_file in zip_files:
        # 一時的にティックデータをロード
        tick_data = load_tick_data_from_zip(zip_file)

        # 1日ごとに処理
        for day in get_trading_days(tick_data):
            day_ticks = filter_by_day(tick_data, day)

            # 時間足変換
            timeframes = convert_to_timeframes(day_ticks)

            # テクニカル指標計算
            indicators = calculate_indicators(timeframes)

            # 標準化データ生成
            standardized_data = generate_standardized_json(
                timeframes, indicators
            )

            # AI分析（バックテスト用）
            rules = gemini_api.analyze(standardized_data)

            # 仮想トレード実行
            result = simulate_trade(rules, day_ticks)

            # 結果をDBに保存
            db.save_backtest_result(result)

        # 月単位のティックデータを破棄
        del tick_data
```

**メモリ使用**:
- 1ヶ月のティックデータ（数百MB）を一時的にロード
- 処理完了後は破棄
- 結果のみDBに永続化

---

### 6.7 メモリ管理のベストプラクティス

#### 6.7.1 リアルタイムモード

```python
# ✅ 良い例：必要最小限のデータのみ保持
cache.current_tick = latest_tick  # 最新1件のみ
cache.timeframes['M15'] = mt5.copy_rates(100)  # 必要な100本のみ

# ❌ 悪い例：全ティックを保持
all_ticks = []  # これはやらない
while True:
    tick = get_tick()
    all_ticks.append(tick)  # メモリリークの原因
```

#### 6.7.2 バックテストモード

```python
# ✅ 良い例：チャンク処理
zip_files = [
    'ticks_USDJPY-oj5k_2024-09.zip',
    'ticks_USDJPY-oj5k_2024-10.zip'
]
for zip_file in zip_files:
    tick_data = load_zip(zip_file)  # 1ヶ月分
    process(tick_data)
    del tick_data  # 明示的に解放
    gc.collect()  # ガベージコレクション

# ❌ 悪い例：全期間を一度にロード
all_tick_data = []
for zip_file in zip_files:
    all_tick_data.extend(load_zip(zip_file))  # メモリ不足の原因
```

---

### 6.8 データ保持まとめ

| 保持場所 | データ種別 | サイズ | 更新頻度 | 保持期間 |
|---------|-----------|--------|---------|---------|
| **メモリ** | 現在ティック | 数十B | 100ms | 常時（最新1件のみ） |
| **メモリ** | 時間足データ | 50KB | 1分 | 常時（指定本数のみ） |
| **メモリ** | テクニカル指標 | 10KB | 1分 | 常時 |
| **メモリ** | 標準化JSON | 20KB | 1分 | 常時 |
| **メモリ** | ルールJSON | 10KB | 定時 | 常時（最新1件のみ） |
| **メモリ** | ポジション情報 | 数KB | 変動時 | 常時 |
| **メモリ一時** | バックテスト用ティック | 数百MB | - | 処理中のみ |
| **DB** | トレード記録 | 累積 | エントリー/決済時 | 永久 |
| **DB** | AI判断履歴 | 累積 | 1日5-10回 | 永久 |
| **DB** | 市場スナップショット | 累積 | AI実行時 | 永久 |

**設計思想**:
- **メモリは最小限**: リアルタイム処理に必要な最新データのみ
- **DBは詳細に**: 分析・検証・トラブルシューティング用に全履歴保存
- **一時データは即破棄**: バックテスト用の大量データは処理後即解放

---

## 7. 実装ロードマップ

### Phase 1（Week 1）

**優先度: 最高**

- データ取得機能
  - zipファイルからのティックデータ読み込み機能（優先）
  - MT5接続機能（リアルタイム用）
- 時間足変換（D1, H4, H1, M15）
- 基本的なOHLC生成

### Phase 1（Week 2）

**優先度: 最高**

- テクニカル指標計算（EMA, RSI, MACD, ATR, BB）
- サポレジ算出
- データ標準化機能
- データハッシュ生成

### Phase 2（Week 3）

**優先度: 高**

- エラーハンドリング強化
- 異常値検出
- データ品質管理
- パフォーマンス最適化

---

## 7. テスト要件

### 7.1 単体テスト

- 各テクニカル指標の計算精度
- 時間足変換の正確性
- データ標準化の完全性

### 7.2 統合テスト

- MT5との接続安定性
- エラー復旧の動作確認
- 異常値検出の精度

### 7.3 負荷テスト

- 複数時間足の同時処理
- 長時間稼働の安定性

---

## 8. 監視とログ

### 8.1 記録項目

- データ取得成功/失敗
- 処理時間
- 異常値の発生
- エラー内容

### 8.2 パフォーマンス監視

- 処理時間の推移
- エラー率
- 接続安定性

---

**以上、データ処理エンジン仕様書**
