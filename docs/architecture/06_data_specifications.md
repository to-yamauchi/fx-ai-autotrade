# データ仕様書

## ドキュメント情報
- **作成日**: 2025-10-21
- **バージョン**: 1.0
- **カテゴリ**: システムアーキテクチャ - データ層仕様

---

## 1. 概要

### 1.1 目的

システム内で使用される全データの形式、取得方法、標準化ルールを定義

### 1.2 設計原則

- **一貫性**: 全コンポーネント間で統一されたフォーマット
- **可読性**: AIと人間の両方が理解しやすい形式
- **再現性**: 同じデータから同じ結果を生成可能

---

## 2. 取得データ

### 2.1 時間足データ

#### 2.1.1 対象時間足

| 時間足 | 取得本数 | 主な用途 | 更新頻度 |
|--------|----------|----------|---------|
| 日足（D1） | 過去30本 | 長期トレンド判定、サポレジ算出 | 1回/日 |
| 4時間足（H4） | 過去50本 | 中期トレンド確認、EMA配列確認 | 1回/4時間 |
| 1時間足（H1） | 過去100本 | メイン分析時間軸、エントリー判定 | 1回/時間 |
| 15分足（M15） | 過去100本 | 短期シグナル、最終エントリー判断 | 1回/15分 |

#### 2.1.2 OHLC構造

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

**フィールド説明**:
- time: タイムスタンプ（MT5サーバー時刻）
- open: 始値
- high: 高値
- low: 安値
- close: 終値
- volume: 出来高（ティック数）
- spread: スプレッド（pips）

### 2.2 テクニカル指標

#### 2.2.1 トレンド系指標

**EMA（指数移動平均線）**

| パラメータ | 期間 | 計算対象 | 用途 |
|-----------|------|---------|------|
| EMA(20) | 20 | D1, H4, H1, M15 | 短期トレンド |
| EMA(50) | 50 | D1, H4, H1, M15 | 中期トレンド |

**計算式**:
```
EMA(t) = Price(t) × k + EMA(t-1) × (1 - k)
k = 2 / (period + 1)
```

**MACD（Moving Average Convergence Divergence）**

| パラメータ | 値 | 説明 |
|-----------|-----|------|
| Fast Period | 12 | 短期EMA |
| Slow Period | 26 | 長期EMA |
| Signal Period | 9 | シグナル線 |

**計算式**:
```
MACD Line = EMA(12) - EMA(26)
Signal Line = EMA(9) of MACD Line
Histogram = MACD Line - Signal Line
```

#### 2.2.2 オシレーター系指標

**RSI（相対力指数）**

| パラメータ | 値 | 説明 |
|-----------|-----|------|
| Period | 14 | 計算期間 |
| 範囲 | 0〜100 | 値の範囲 |

**計算式**:
```
RS = 平均上昇幅 / 平均下降幅（14期間）
RSI = 100 - (100 / (1 + RS))
```

**解釈**:
- RSI > 70: 買われすぎ
- RSI < 30: 売られすぎ
- 50付近: 中立

**ストキャスティクス**

| パラメータ | 値 | 説明 |
|-----------|-----|------|
| %K Period | 5 | %K計算期間 |
| %D Period | 3 | %D計算期間 |
| Slowing | 3 | 平滑化期間 |

**計算式**:
```
%K = 100 × (Close - Low14) / (High14 - Low14)
%D = SMA(3) of %K
```

#### 2.2.3 ボラティリティ系指標

**ATR（Average True Range）**

| パラメータ | 値 | 説明 |
|-----------|-----|------|
| Period | 14 | 計算期間 |

**計算式**:
```
TR = max(High - Low, |High - Close前日|, |Low - Close前日|)
ATR = SMA(14) of TR
```

**用途**:
- ポジションサイズ調整
- ストップロス設定
- ボラティリティ評価

**ボリンジャーバンド**

| パラメータ | 値 | 説明 |
|-----------|-----|------|
| Period | 20 | 移動平均期間 |
| Deviation | 2 | 標準偏差の倍数 |

**計算式**:
```
Middle Band = SMA(20)
Upper Band = Middle Band + (2 × σ)
Lower Band = Middle Band - (2 × σ)
```

**解釈**:
- バンド幅狭い: ボラティリティ低、ブレイクアウト待ち
- バンド幅広い: ボラティリティ高、レンジ回帰の可能性
- 価格が上限/下限接触: 反転またはブレイクアウトの兆候

#### 2.2.4 サポート/レジスタンス

**高値・安値分析**

```json
{
  "past_20_days": {
    "highest": 150.50,
    "lowest": 148.80,
    "swing_highs": [150.20, 149.90, 149.65],
    "swing_lows": [149.00, 149.30, 149.45]
  }
}
```

**ピボットポイント**

```json
{
  "pivot": 149.60,
  "resistance": {
    "r1": 149.70,
    "r2": 149.85,
    "r3": 150.00
  },
  "support": {
    "s1": 149.45,
    "s2": 149.30,
    "s3": 149.15
  }
}
```

**計算式**:
```
Pivot = (High + Low + Close) / 3
R1 = (2 × Pivot) - Low
R2 = Pivot + (High - Low)
R3 = High + 2 × (Pivot - Low)
S1 = (2 × Pivot) - High
S2 = Pivot - (High - Low)
S3 = Low - 2 × (High - Pivot)
```

**フィボナッチリトレースメント**

```json
{
  "swing_high": 149.90,
  "swing_low": 149.30,
  "range_pips": 60,
  "levels": {
    "0.0%": 149.30,
    "23.6%": 149.44,
    "38.2%": 149.53,
    "50.0%": 149.60,
    "61.8%": 149.67,
    "100.0%": 149.90
  }
}
```

---

## 3. データ標準化フォーマット

### 3.1 完全なJSON構造

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
      "d1": {"ema20": 149.80, "ema50": 150.20},
      "h4": {"ema20": 149.65, "ema50": 149.85},
      "h1": {"ema20": 149.58, "ema50": 149.72},
      "m15": {"ema20": 149.63, "ema50": 149.65},
      "h1_alignment": "弱気配列",
      "h1_distance": "14pips差",
      "trend_strength": "中程度"
    },
    "rsi": {
      "d1": 42.5,
      "h4": 48.2,
      "h1": 45.2,
      "m15": 48.5,
      "h1_interpretation": "中立圏",
      "divergence": "なし"
    },
    "macd": {
      "h1_value": -0.025,
      "h1_signal": -0.018,
      "histogram": -0.007,
      "trend": "弱気",
      "recent_cross": "なし",
      "h1_direction": "下向き"
    },
    "bollinger": {
      "h1_upper": 149.75,
      "h1_middle": 149.65,
      "h1_lower": 149.55,
      "width": "狭い",
      "width_pips": 20,
      "position": "中央付近",
      "squeeze": true
    },
    "atr": {
      "d1": 0.450,
      "h4": 0.220,
      "h1": 0.150,
      "h1_interpretation": "ボラティリティ低め",
      "h1_pips": 15
    },
    "stochastic": {
      "h1_k": 52.3,
      "h1_d": 48.7,
      "interpretation": "中立"
    }
  },

  "key_levels": {
    "support": [149.50, 149.20, 149.00],
    "resistance": [149.70, 149.90, 150.20],
    "pivot": {
      "pivot": 149.60,
      "r1": 149.70,
      "r2": 149.85,
      "r3": 150.00,
      "s1": 149.45,
      "s2": 149.30,
      "s3": 149.15
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
      {
        "time": "13:00",
        "open": 149.65,
        "high": 149.68,
        "low": 149.62,
        "close": 149.64,
        "pattern": "陰線",
        "size": "小",
        "body_pips": 1,
        "comment": "方向感なし"
      },
      {
        "time": "14:00",
        "open": 149.64,
        "high": 149.69,
        "low": 149.63,
        "close": 149.67,
        "pattern": "陽線",
        "size": "小",
        "body_pips": 3,
        "comment": "小反発"
      },
      {
        "time": "15:00",
        "open": 149.67,
        "high": 149.68,
        "low": 149.65,
        "close": 149.67,
        "pattern": "十字線",
        "size": "極小",
        "body_pips": 0,
        "comment": "膠着"
      }
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
    "next_session_start": "16:00",
    "session_overlap": false,
    "typical_volatility": "低い",
    "comment": "東京時間は動き鈍い、欧州開始で活発化期待"
  },

  "market_context": {
    "day_of_week": "月曜日",
    "week_of_month": 3,
    "is_month_end": false,
    "近日の重要指標": [
      {"date": "2025-10-21", "time": "21:30", "event": "米国失業保険申請件数"}
    ]
  }
}
```

### 3.2 データハッシュ

**目的**: 再現性の確保

**計算方法**:
```python
import hashlib
import json

def generate_data_hash(market_data):
    # メタデータを除外
    data_copy = market_data.copy()
    if 'metadata' in data_copy:
        del data_copy['metadata']

    # 正規化してハッシュ化
    json_str = json.dumps(data_copy, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(json_str.encode('utf-8')).hexdigest()[:16]
```

**用途**:
- バックテストでの同一性確認
- データ整合性チェック
- 再計算の必要性判定

---

## 4. AI向け最適化

### 4.1 自然言語による解釈

**数値だけでなく、解釈も含める**:
```json
{
  "rsi": {
    "h1": 45.2,
    "interpretation": "中立圏"  // AIが理解しやすい
  }
}
```

### 4.2 階層的構造

**トップダウンでの理解**:
1. market_structure: 全体像
2. technical_summary: 詳細指標
3. key_levels: 重要価格
4. recent_price_action: 直近の動き

### 4.3 コンテキスト情報

**市場環境の背景**:
- セッション情報
- 曜日・月末情報
- 重要指標予定

---

## 5. データ品質管理

### 5.1 異常値検出

**チェック項目**:
```python
def validate_market_data(data):
    # スプレッド異常
    if data['metadata']['current_spread'] > 20:
        raise DataQualityError("Spread too wide")

    # 価格の急激な変動
    price_change = abs(data['current_price'] - data['previous_price'])
    if price_change > 0.30:  # 30pips
        logger.warning("Large price movement detected")

    # データ欠損
    required_fields = ['market_structure', 'technical_summary', 'key_levels']
    for field in required_fields:
        if field not in data:
            raise DataQualityError(f"Missing field: {field}")

    # タイムスタンプの妥当性
    timestamp = datetime.fromisoformat(data['metadata']['timestamp'])
    if abs((datetime.now() - timestamp).total_seconds()) > 300:
        logger.warning("Data timestamp is more than 5 minutes old")
```

### 5.2 データ完全性

```python
def check_data_completeness(data):
    # 全時間足のデータが揃っているか
    timeframes = ['daily_trend', 'h4_trend', 'h1_trend', 'm15_trend']
    for tf in timeframes:
        if tf not in data['market_structure']:
            return False, f"Missing timeframe: {tf}"

    # 全指標が計算できているか
    indicators = ['ema', 'rsi', 'macd', 'bollinger', 'atr']
    for ind in indicators:
        if ind not in data['technical_summary']:
            return False, f"Missing indicator: {ind}"

    # 欠損値がないか
    if has_null_values(data):
        return False, "Contains null values"

    return True, "Data complete"
```

---

## 6. パフォーマンス最適化

### 6.1 計算キャッシュ

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def calculate_ema(prices_tuple, period):
    prices = list(prices_tuple)
    # EMA計算...
    return ema_values

# 使用時
prices_tuple = tuple(prices)  # リストをタプルに変換（ハッシュ可能）
ema20 = calculate_ema(prices_tuple, 20)
```

### 6.2 並列計算

```python
from concurrent.futures import ThreadPoolExecutor

def calculate_all_indicators(ohlc_data):
    with ThreadPoolExecutor(max_workers=4) as executor:
        # 並列で計算
        future_ema = executor.submit(calculate_ema_all_timeframes, ohlc_data)
        future_rsi = executor.submit(calculate_rsi_all_timeframes, ohlc_data)
        future_macd = executor.submit(calculate_macd_all_timeframes, ohlc_data)
        future_bb = executor.submit(calculate_bollinger_all_timeframes, ohlc_data)

        # 結果取得
        ema_results = future_ema.result()
        rsi_results = future_rsi.result()
        macd_results = future_macd.result()
        bb_results = future_bb.result()

    return combine_results(ema_results, rsi_results, macd_results, bb_results)
```

---

**以上、データ仕様書**
