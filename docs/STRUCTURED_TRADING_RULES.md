# 構造化トレードルール仕様

## 概要

自然言語パラメータを排除し、プログラムが直接解釈できる構造化データに変更。

## 完全な構造化トレードルールJSON

```json
{
  "version": "2.0",
  "generated_at": "2025-01-15T08:00:00Z",
  "valid_until": "2025-01-15T09:00:00Z",

  "daily_bias": "BUY",
  "confidence": 0.75,
  "reasoning": "判断理由（人間用のメモ）",

  "entry_conditions": {
    "should_trade": true,
    "direction": "BUY",
    "price_zone": {
      "min": 149.50,
      "max": 149.65
    },
    "indicators": {
      "rsi": {
        "timeframe": "M15",
        "min": 50,
        "max": 70
      },
      "ema": {
        "timeframe": "M15",
        "condition": "price_above",
        "period": 20
      },
      "macd": {
        "timeframe": "M15",
        "condition": "histogram_positive"
      }
    },
    "spread": {
      "max_pips": 10
    },
    "time_filter": {
      "avoid_times": [
        {"start": "09:50", "end": "10:00", "reason": "Tokyo fixing"},
        {"start": "16:50", "end": "17:00", "reason": "London fixing"}
      ]
    }
  },

  "exit_strategy": {
    "take_profit": [
      {"pips": 10, "close_percent": 30},
      {"pips": 20, "close_percent": 40},
      {"pips": 30, "close_percent": 100}
    ],
    "stop_loss": {
      "initial_pips": 15,
      "price_level": 149.40,
      "trailing": {
        "activate_at_pips": 15,
        "trail_distance_pips": 10
      }
    },
    "indicator_exits": [
      {
        "type": "macd_cross",
        "timeframe": "M15",
        "direction": "bearish",
        "action": "close_50"
      },
      {
        "type": "ema_break",
        "timeframe": "M15",
        "period": 20,
        "direction": "below",
        "consecutive_candles": 2,
        "action": "close_all"
      },
      {
        "type": "rsi_threshold",
        "timeframe": "M15",
        "threshold": 70,
        "direction": "above",
        "action": "close_50"
      }
    ],
    "time_exits": {
      "max_hold_minutes": 240,
      "force_close_time": "23:00"
    }
  },

  "risk_management": {
    "position_size_multiplier": 0.8,
    "max_positions": 1,
    "max_risk_per_trade_percent": 2.0,
    "max_total_exposure_percent": 4.0
  },

  "key_levels": {
    "entry_target": 149.55,
    "invalidation_level": 149.40,
    "support_levels": [149.50, 149.30, 149.00],
    "resistance_levels": [149.70, 149.90, 150.00]
  },

  "hourly_predictions": {
    "09:00": {
      "predicted_range": {"min": 149.40, "max": 149.60},
      "bias": "NEUTRAL",
      "volatility_expected": "low"
    },
    "12:00": {
      "predicted_range": {"min": 149.45, "max": 149.70},
      "bias": "BUY",
      "volatility_expected": "medium"
    },
    "15:00": {
      "predicted_range": {"min": 149.55, "max": 149.80},
      "bias": "BUY",
      "volatility_expected": "high"
    },
    "18:00": {
      "predicted_range": {"min": 149.60, "max": 149.90},
      "bias": "BUY",
      "volatility_expected": "high"
    },
    "21:00": {
      "predicted_range": {"min": 149.50, "max": 149.85},
      "bias": "NEUTRAL",
      "volatility_expected": "very_high"
    }
  }
}
```

## データ型定義

### entry_conditions.indicators.rsi
```typescript
{
  "timeframe": "M15" | "H1" | "H4" | "D1",
  "min": number,  // 最小値
  "max": number   // 最大値
}
```

### entry_conditions.indicators.ema
```typescript
{
  "timeframe": "M15" | "H1" | "H4" | "D1",
  "condition": "price_above" | "price_below" | "cross_above" | "cross_below",
  "period": number  // EMA期間
}
```

### entry_conditions.indicators.macd
```typescript
{
  "timeframe": "M15" | "H1" | "H4" | "D1",
  "condition": "histogram_positive" | "histogram_negative" | "signal_cross_above" | "signal_cross_below"
}
```

### exit_strategy.indicator_exits[]
```typescript
{
  "type": "macd_cross" | "ema_break" | "rsi_threshold",
  "timeframe": "M15" | "H1" | "H4" | "D1",
  "action": "close_50" | "close_all" | "close_75",
  // type別の追加パラメータ
  ...
}
```

## ルールエンジンの解釈方法

### エントリーチェック
```python
def check_entry_conditions(market_data, rule):
    # 1. should_tradeチェック
    if not rule['entry_conditions']['should_trade']:
        return False

    # 2. 価格ゾーンチェック
    current_price = market_data['current_price']
    price_zone = rule['entry_conditions']['price_zone']
    if not (price_zone['min'] <= current_price <= price_zone['max']):
        return False

    # 3. インジケーターチェック
    indicators = rule['entry_conditions']['indicators']

    # RSI
    rsi_rule = indicators['rsi']
    current_rsi = market_data['M15']['rsi']
    if not (rsi_rule['min'] <= current_rsi <= rsi_rule['max']):
        return False

    # EMA
    ema_rule = indicators['ema']
    if ema_rule['condition'] == 'price_above':
        ema_value = market_data['M15'][f'ema_{ema_rule["period"]}']
        if not (current_price > ema_value):
            return False

    # MACD
    macd_rule = indicators['macd']
    if macd_rule['condition'] == 'histogram_positive':
        macd_hist = market_data['M15']['macd_histogram']
        if not (macd_hist > 0):
            return False

    # 4. スプレッドチェック
    spread = market_data['spread']
    if spread > indicators['spread']['max_pips']:
        return False

    # 5. 時間フィルター
    current_time = market_data['current_time']
    for avoid in indicators['time_filter']['avoid_times']:
        if is_time_in_range(current_time, avoid['start'], avoid['end']):
            return False

    return True
```

## 1時間毎のルール更新フロー

```
[毎時00分]
  ↓
AI分析実行（最新60分のティックデータ使用）
  ↓
構造化ルール生成
  ↓
DBに保存（trade_rules テーブル）
  ↓
有効期限: 次の1時間（valid_until設定）
```

```
[15分毎 or ティック毎]
  ↓
最新ルールをDBから取得
  ↓
市場データ取得
  ↓
エントリー条件チェック
  ↓ (全て満たす)
MT5でトレード実行
```
