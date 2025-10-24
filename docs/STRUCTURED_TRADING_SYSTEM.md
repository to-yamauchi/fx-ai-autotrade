# 構造化トレードシステム

## 概要

自然言語パラメータを排除し、完全に構造化されたデータでトレード判断を行う新しいアーキテクチャです。

### アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│  1時間毎のルール生成（AIが実行）                              │
└─────────────────────────────────────────────────────────────┘
    ↓
┌──────────────┐
│ 市場データ取得 │ ← リアルタイムティックデータ
└──────────────┘
    ↓
┌──────────────┐
│ AI分析       │ ← morning_analysis_v2.txt プロンプト
└──────────────┘
    ↓
┌──────────────────┐
│ 構造化ルール生成  │ ← 自然言語なし、完全に構造化されたJSON
└──────────────────┘
    ↓
┌──────────────┐
│ DBに保存     │ ← trade_rules テーブル
└──────────────┘
    ↓ (有効期限: 1時間)


┌─────────────────────────────────────────────────────────────┐
│  15分毎のトレード判断（機械的に実行）                         │
└─────────────────────────────────────────────────────────────┘
    ↓
┌──────────────┐
│ 最新ルール取得 │ ← DBから最新の有効なルールを取得
└──────────────┘
    ↓
┌──────────────┐
│ 市場データ取得 │ ← 現在の価格、インジケーター
└──────────────┘
    ↓
┌────────────────────┐
│ 構造化ルールエンジン │ ← StructuredRuleEngine
└────────────────────┘
    ↓
┌──────────────────┐
│ エントリー条件チェック│ ← price_zone, RSI, EMA, MACD, spread, time_filter
└──────────────────┘
    ↓ (全て満たす)
┌──────────────┐
│ MT5でトレード実行 │
└──────────────┘
```

## 主要コンポーネント

### 1. 構造化ルール生成（1時間毎）

**ファイル**: `src/scheduler/hourly_rule_updater.py`

```python
from src.scheduler import HourlyRuleUpdater

# 自動実行（バックグラウンド）
updater = HourlyRuleUpdater(symbol='USDJPY')
updater.start()  # 毎時00分に自動実行

# 手動実行
updater.update_rule_now()
```

**生成されるルールの例**:
```json
{
  "version": "2.0",
  "generated_at": "2025-01-15T08:00:00Z",
  "valid_until": "2025-01-15T09:00:00Z",
  "entry_conditions": {
    "should_trade": true,
    "direction": "BUY",
    "price_zone": {"min": 149.50, "max": 149.65},
    "indicators": {
      "rsi": {"timeframe": "M15", "min": 50, "max": 70},
      "ema": {"timeframe": "M15", "condition": "price_above", "period": 20},
      "macd": {"timeframe": "M15", "condition": "histogram_positive"}
    },
    "spread": {"max_pips": 10},
    "time_filter": {
      "avoid_times": [
        {"start": "09:50", "end": "10:00", "reason": "Tokyo fixing"}
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
    "max_risk_per_trade_percent": 2.0
  }
}
```

### 2. 構造化ルールエンジン（15分毎）

**ファイル**: `src/rule_engine/structured_rule_engine.py`

```python
from src.rule_engine import StructuredRuleEngine
from src.scheduler import get_latest_rule_from_db

# ルールエンジン初期化
engine = StructuredRuleEngine()

# 最新ルール取得
rule = get_latest_rule_from_db(symbol='USDJPY')

# 市場データ取得
market_data = {
    'current_price': 149.55,
    'spread': 2.5,
    'current_time': '14:30',
    'M15': {
        'rsi': 55,
        'ema_20': 149.40,
        'macd_histogram': 0.05
    }
}

# エントリー条件チェック
is_valid, message = engine.check_entry_conditions(market_data, rule)
if is_valid:
    # トレード実行
    execute_trade()
```

### 3. 決済判断

```python
# ポジション情報
position = {
    'ticket': 12345,
    'entry_price': 149.50,
    'entry_time': '2025-01-15 12:00:00',
    'direction': 'BUY'
}

# 決済条件チェック
should_exit, reason, action = engine.check_exit_conditions(
    position,
    market_data,
    rule
)

if should_exit:
    if action == 'close_all':
        close_position(ticket, 100)
    elif action == 'close_50':
        close_position(ticket, 50)
```

## データベース

### trade_rulesテーブル

```sql
CREATE TABLE trade_rules (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    generated_at TIMESTAMP NOT NULL,
    valid_until TIMESTAMP NOT NULL,
    daily_bias VARCHAR(10),
    confidence DECIMAL(4,3),
    rule_json JSONB NOT NULL
);
```

### マイグレーション実行

```bash
psql -U postgres -d fx_autotrade -f config/migrations/010_create_trade_rules_table.sql
```

## 使用方法

### 1. DBマイグレーション実行

```bash
psql -U postgres -d fx_autotrade -f config/migrations/010_create_trade_rules_table.sql
```

### 2. 1時間毎のルール更新を開始

```python
from src.scheduler import HourlyRuleUpdater

updater = HourlyRuleUpdater(symbol='USDJPY')
updater.start()  # バックグラウンドで実行
```

### 3. トレードエンジンから最新ルールを使用

```python
from src.rule_engine import StructuredRuleEngine
from src.scheduler import get_latest_rule_from_db

# 最新ルール取得
rule = get_latest_rule_from_db('USDJPY')

# ルールエンジンでチェック
engine = StructuredRuleEngine()
is_valid, message = engine.check_entry_conditions(market_data, rule)
```

## テスト

```bash
# 構造化ルールエンジンのテスト
python test_structured_rules.py
```

## 従来との比較

| 項目 | 従来 | 新システム |
|------|------|-----------|
| **パラメータ形式** | 自然言語混在 | 完全に構造化 |
| **エントリー条件** | `required_signals` (文章) | `indicators` (構造化) |
| **プログラム解釈** | ❌ 不可能 | ✅ 可能 |
| **ルール更新頻度** | 1日1回（朝のみ） | 1時間毎 |
| **トレード判断** | AIが毎回介入 | ルールに基づき機械的 |
| **リアルタイム性** | 低い | 高い（1時間毎更新） |

## 構造化データの利点

### ❌ 従来（自然言語）

```json
{
  "required_signals": [
    "M15足でEMA20を上抜け",
    "RSI > 50",
    "MACDがゴールデンクロス済み"
  ]
}
```

→ プログラムが解釈できない（人間が読むためだけ）

### ✅ 新システム（構造化）

```json
{
  "indicators": {
    "rsi": {"timeframe": "M15", "min": 50, "max": 70},
    "ema": {"timeframe": "M15", "condition": "price_above", "period": 20},
    "macd": {"timeframe": "M15", "condition": "histogram_positive"}
  }
}
```

→ プログラムが直接if文で判定可能

## ファイル一覧

```
docs/
  ├─ STRUCTURED_TRADING_RULES.md       # 仕様書
  └─ STRUCTURED_TRADING_SYSTEM.md      # このファイル

src/
  ├─ ai_analysis/prompts/
  │   └─ morning_analysis_v2.txt       # 構造化データ生成プロンプト
  ├─ rule_engine/
  │   └─ structured_rule_engine.py     # 構造化ルールエンジン
  └─ scheduler/
      ├─ __init__.py
      └─ hourly_rule_updater.py        # 1時間毎ルール更新

config/migrations/
  └─ 010_create_trade_rules_table.sql  # DBマイグレーション

test_structured_rules.py                # テストスクリプト
```

## 今後の拡張

1. **AIプロンプトの統合**: morning_analysis_v2.txt を ai_analyzer.py に統合
2. **バックテスト対応**: 構造化ルールでバックテスト実行
3. **複数通貨ペア対応**: 各通貨ペアごとに1時間毎ルール生成
4. **ルール履歴分析**: 過去のルールと実績の相関分析

## トラブルシューティング

### ルールが取得できない

```python
from src.scheduler import get_latest_rule_from_db

rule = get_latest_rule_from_db('USDJPY')
if rule is None:
    print("有効なルールが見つかりません")
    # 手動でルール生成
    from src.scheduler import HourlyRuleUpdater
    updater = HourlyRuleUpdater()
    updater.update_rule_now()
```

### ルールの有効期限切れ

DBから古いルールを削除：

```sql
DELETE FROM trade_rules WHERE valid_until < NOW() - INTERVAL '7 days';
```

## 参考資料

- [構造化トレードルール仕様](./STRUCTURED_TRADING_RULES.md)
- [ルールエンジンアーキテクチャ](./architecture/03_ルールエンジン.md)
