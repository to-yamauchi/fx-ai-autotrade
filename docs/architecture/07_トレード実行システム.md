# トレード実行システム仕様書

## ドキュメント情報
- **作成日**: 2025-10-21
- **バージョン**: 1.0
- **カテゴリ**: システムアーキテクチャ - トレード実行

---

## 1. 概要

### 1.1 役割

AIが生成したルールに基づき、エントリー条件を監視し、適切なタイミングで注文を実行するコンポーネント

### 1.2 設計原則

- **ルールベース**: AIルールの機械的な判定、曖昧さなし
- **安全性**: 多段階のチェックによるリスク管理
- **確実性**: エントリー条件の厳格な確認

---

## 2. エントリー判断フロー

### 2.1 全体フロー

```
【継続的監視（1分ごと）】

┌─────────────────────────────────┐
│ Step 1: トレード可否確認         │
│  - daily_bias が NEUTRAL?       │
│  - should_trade が false?       │
│  - 既にポジション保有中?         │
└─────────────────────────────────┘
        ↓ OK
┌─────────────────────────────────┐
│ Step 2: 価格ゾーンチェック       │
│  - 現在価格が price_zone 内?    │
└─────────────────────────────────┘
        ↓ OK
┌─────────────────────────────────┐
│ Step 3: 必須シグナルチェック     │
│  - required_signals 全て達成?   │
└─────────────────────────────────┘
        ↓ OK
┌─────────────────────────────────┐
│ Step 4: 回避条件チェック         │
│  - avoid_if いずれか該当?       │
└─────────────────────────────────┘
        ↓ OK
┌─────────────────────────────────┐
│ Step 5: 最終ガードレール         │
│  - スプレッド > 10pips?         │
│  - 口座残高不足?                │
│  - 重要指標発表30分以内?        │
└─────────────────────────────────┘
        ↓ 全てクリア
┌─────────────────────────────────┐
│ エントリー実行                   │
└─────────────────────────────────┘
```

---

## 3. 各ステップ詳細

### 3.1 Step 1: トレード可否確認

#### 3.1.1 概要

**目的**: 本日トレードすべきかの基本判断

#### 3.1.2 チェック項目

**1. daily_bias が NEUTRAL**
```python
def check_daily_bias():
    rule = get_current_rule_json()
    if rule['daily_bias'] == 'NEUTRAL':
        logger.info("Entry skipped: daily_bias is NEUTRAL")
        return False
    return True
```

**理由**: AIが方向性を判断できない場合はエントリーしない

**2. should_trade が false**
```python
def check_should_trade():
    rule = get_current_rule_json()
    if not rule['entry_conditions']['should_trade']:
        logger.info("Entry skipped: should_trade is false")
        return False
    return True
```

**理由**: AIが市場環境を不適切と判断した場合

**3. 既にポジション保有中**
```python
def check_no_existing_position():
    if has_open_positions():
        logger.debug("Entry skipped: already in position")
        return False
    return True
```

**理由**: Phase 1-4では1ポジションのみ（max_positions = 1）

### 3.2 Step 2: 価格ゾーンチェック

#### 3.2.1 概要

**目的**: エントリーに適した価格帯か確認

#### 3.2.2 実装

```python
def in_price_zone():
    rule = get_current_rule_json()
    price_zone = rule['entry_conditions']['price_zone']

    current_price = get_current_price()

    if price_zone['min'] <= current_price <= price_zone['max']:
        logger.debug(f"Price {current_price} in zone [{price_zone['min']}, {price_zone['max']}]")
        return True
    else:
        logger.debug(f"Price {current_price} outside zone")
        return False
```

**AI生成例**:
```json
{
  "price_zone": {
    "min": 149.50,
    "max": 149.65
  }
}
```

**理由**: 高値掴み・安値売りを避ける

### 3.3 Step 3: 必須シグナルチェック

#### 3.3.1 概要

**目的**: 全てのエントリー条件が揃っているか確認

#### 3.3.2 AI生成ルール例

```json
{
  "required_signals": [
    "現在価格が149.50〜149.65の範囲内",
    "M15足でEMA20を上抜け",
    "RSI > 50",
    "MACDがゴールデンクロス済み、またはヒストグラムが正",
    "スプレッド < 10pips"
  ]
}
```

#### 3.3.3 実装

```python
def all_required_signals_met():
    rule = get_current_rule_json()
    required_signals = rule['entry_conditions']['required_signals']

    for signal in required_signals:
        if not evaluate_signal(signal):
            logger.debug(f"Required signal not met: {signal}")
            return False

    logger.info("All required signals met")
    return True

def evaluate_signal(signal):
    """自然言語条件をプログラム的に評価"""

    # 価格範囲
    if "範囲内" in signal:
        min_price, max_price = extract_price_range(signal)
        current_price = get_current_price()
        return min_price <= current_price <= max_price

    # EMAクロス
    if "EMA20を上抜け" in signal:
        current_price = get_current_price()
        ema20_m15 = get_ema20('M15')
        return current_price > ema20_m15

    # RSI
    if "RSI >" in signal:
        threshold = extract_number(signal)
        rsi = get_rsi('H1')
        return rsi > threshold

    # MACDゴールデンクロス
    if "MACDがゴールデンクロス" in signal or "ヒストグラムが正" in signal:
        macd = get_macd('H1')
        macd_signal = get_macd_signal('H1')
        histogram = get_macd_histogram('H1')

        golden_cross = macd > macd_signal
        histogram_positive = histogram > 0

        return golden_cross or histogram_positive

    # スプレッド
    if "スプレッド <" in signal:
        threshold = extract_number(signal)
        spread = get_current_spread()
        return spread < threshold

    # その他の条件...
    logger.warning(f"Unknown signal format: {signal}")
    return False
```

### 3.4 Step 4: 回避条件チェック

#### 3.4.1 概要

**目的**: エントリーを避けるべき状況の検知

#### 3.4.2 AI生成ルール例

```json
{
  "avoid_if": [
    "現在価格が149.50を明確に下抜け（5pips以上）",
    "スプレッド > 10pips",
    "RSI > 70（買われすぎ）",
    "重要指標発表30分以内"
  ]
}
```

#### 3.4.3 実装

```python
def any_avoid_condition_met():
    rule = get_current_rule_json()
    avoid_if = rule['entry_conditions']['avoid_if']

    for condition in avoid_if:
        if evaluate_avoid_condition(condition):
            logger.info(f"Entry avoided: {condition}")
            return True

    return False

def evaluate_avoid_condition(condition):
    """回避条件の評価"""

    # 価格ブレイク
    if "下抜け" in condition:
        price_level = extract_number(condition)
        pips_threshold = extract_pips_threshold(condition)  # 「5pips以上」
        current_price = get_current_price()

        return current_price < (price_level - pips_threshold / 100)

    # スプレッド
    if "スプレッド >" in condition:
        threshold = extract_number(condition)
        spread = get_current_spread()
        return spread > threshold

    # RSI
    if "RSI >" in condition:
        threshold = extract_number(condition)
        rsi = get_rsi('H1')
        return rsi > threshold

    # 重要指標発表
    if "重要指標発表" in condition:
        minutes = extract_number(condition)
        return is_near_major_news(minutes)

    return False
```

### 3.5 Step 5: 最終ガードレール

#### 3.5.1 概要

**目的**: システムレベルの安全チェック

#### 3.5.2 実装

```python
def final_guardrails_pass():
    # 1. スプレッドチェック（ハードコード）
    spread = get_current_spread()
    if spread > 10:
        logger.info(f"Entry blocked: spread {spread}pips > 10pips")
        return False

    # 2. 口座残高チェック
    if not has_sufficient_balance():
        logger.warning("Entry blocked: insufficient balance")
        send_alert("Insufficient balance for new position")
        return False

    # 3. 重要指標発表チェック
    if is_near_major_news(minutes=30):
        logger.info("Entry blocked: major news within 30 minutes")
        return False

    # 4. 取引時間チェック（週末など）
    if not is_trading_hours():
        logger.info("Entry blocked: outside trading hours")
        return False

    # 5. システム正常性チェック
    if not is_system_healthy():
        logger.error("Entry blocked: system health check failed")
        return False

    return True

def has_sufficient_balance():
    account_balance = mt5.account_info().balance
    required_margin = calculate_required_margin()

    # 証拠金維持率200%以上を確保
    return account_balance >= required_margin * 2

def is_near_major_news(minutes=30):
    # 経済指標カレンダーチェック（将来実装）
    # 現在は簡易実装
    return False

def is_trading_hours():
    now = datetime.now()
    day_of_week = now.weekday()

    # 土日は取引停止
    if day_of_week >= 5:  # 5=土曜, 6=日曜
        return False

    # 月曜07:00以降のみ
    if day_of_week == 0 and now.hour < 7:
        return False

    return True

def is_system_healthy():
    # MT5接続確認
    if not mt5.terminal_info():
        return False

    # データ取得成功確認
    if not can_fetch_market_data():
        return False

    return True
```

---

## 4. エントリー実行

### 4.1 ポジションサイズ決定

#### 4.1.1 基本方針

**基本ロット**: 0.1 lot

**調整倍率**: AI生成の position_size_multiplier（0.5〜1.0）

**最終ロット** = 基本ロット × 調整倍率

#### 4.1.2 実装

```python
def calculate_lot_size(rule):
    # 基本ロット
    base_lot = 0.1

    # AI調整倍率
    multiplier = rule['risk_management']['position_size_multiplier']

    # 最終ロット
    final_lot = base_lot * multiplier

    # 最小ロット確認（MT5制約）
    min_lot = mt5.symbol_info("USDJPY").volume_min
    if final_lot < min_lot:
        final_lot = min_lot

    # 最大ロット確認（MT5制約）
    max_lot = mt5.symbol_info("USDJPY").volume_max
    if final_lot > max_lot:
        final_lot = max_lot

    # ロットステップに丸める
    lot_step = mt5.symbol_info("USDJPY").volume_step
    final_lot = round(final_lot / lot_step) * lot_step

    logger.info(f"Lot size: {final_lot} (base: {base_lot}, multiplier: {multiplier})")

    return final_lot
```

#### 4.1.3 調整倍率の例

```json
{
  "risk_management": {
    "position_size_multiplier": 0.8,
    "reason": "信頼度0.75だが、日足は下降トレンドのため保守的に"
  }
}
```

**ケース別**:
- 確信度高い、ボラティリティ通常: 1.0倍（0.1 lot）
- 確信度中程度: 0.7倍（0.07 lot）
- 確信度低い、ボラティリティ高: 0.5倍（0.05 lot）

### 4.2 ストップロス設定

#### 4.2.1 2段階の防御

**1. 保険ストップロス（MT5に設定）**

**目的**: 万が一のシステム障害時の最終防衛線

**設定値**: 口座の5%に相当

```python
def calculate_insurance_stop_loss(entry_price, direction, lot_size):
    account_balance = mt5.account_info().balance
    max_loss_usd = account_balance * 0.05

    # 1 lotあたりのpip価値（USDJPY: 約$10/pip/lot）
    pip_value_per_lot = 10

    # 許容pips
    allowed_pips = max_loss_usd / (lot_size * pip_value_per_lot)

    # ストップロス価格
    if direction == "BUY":
        stop_loss = entry_price - (allowed_pips / 100)
    else:  # SELL
        stop_loss = entry_price + (allowed_pips / 100)

    logger.info(f"Insurance SL: {stop_loss} ({allowed_pips}pips, 5% of account)")

    return stop_loss
```

**例**:
- 口座: 10万ドル
- ロット: 0.1 lot
- 最大損失: $5,000（5%）
- 許容pips: $5,000 / (0.1 × $10) = 5,000pips
- BUY 149.60エントリー: SL = 149.60 - 50.00 = 99.60

**2. 実質ストップロス（Layer 1で監視）**

**設定値**:
- 口座の2%で強制決済
- ハードストップ: 50pips

**詳細**: 監視・決済システム仕様書のLayer 1を参照

#### 4.2.2 なぜ2段階か

**保険SL（5%、MT5設定）**:
- システム完全停止時の保護
- MT5サーバー側で動作
- 実際には発動させない（Layer 1が先に動作）

**実質SL（2%、Layer 1監視）**:
- 通常時の損失管理
- 100ms高速監視
- 実際の損失はこちらで制御

### 4.3 注文実行

#### 4.3.1 注文タイプ

**成行注文**（推奨）:
- 即座のエントリーが必要な場合
- スリッページ許容

**指値注文**（オプション）:
- 価格ゾーンのエッジでのエントリー狙い
- 未達の可能性あり

#### 4.3.2 実装

```python
def execute_entry():
    rule = get_current_rule_json()
    direction = rule['entry_conditions']['direction']

    # ポジションサイズ決定
    lot_size = calculate_lot_size(rule)

    # 現在価格
    current_price = get_current_price()

    # 保険ストップロス計算
    insurance_sl = calculate_insurance_stop_loss(current_price, direction, lot_size)

    # 注文実行
    if direction == "BUY":
        result = mt5.Buy(
            symbol="USDJPY",
            volume=lot_size,
            price=mt5.symbol_info_tick("USDJPY").ask,
            sl=insurance_sl,
            tp=None,  # 利確は動的管理
            deviation=20,  # 許容スリッページ（pips）
            magic=12345,  # マジックナンバー
            comment="AI Entry BUY"
        )
    else:  # SELL
        result = mt5.Sell(
            symbol="USDJPY",
            volume=lot_size,
            price=mt5.symbol_info_tick("USDJPY").bid,
            sl=insurance_sl,
            tp=None,
            deviation=20,
            magic=12345,
            comment="AI Entry SELL"
        )

    # 結果処理
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        logger.info(f"Entry successful: {direction} {lot_size} lot @ {result.price}")

        # 記録
        record_entry(result, rule)

        # アラート（オプション）
        send_alert(f"エントリー成功: {direction} {lot_size} lot @ {result.price}")
    else:
        logger.error(f"Entry failed: {result.comment}")
        send_alert(f"エントリー失敗: {result.comment}")
```

### 4.4 記録

#### 4.4.1 保存情報

```python
def record_entry(result, rule):
    # 市場データスナップショット
    snapshot_id = save_market_data_snapshot()

    # AI判断ID（朝の分析）
    ai_judgment_id = get_latest_morning_analysis_id()

    # トレード記録
    trade_id = db.insert(
        table='trades',
        data={
            'trade_date': datetime.now().date(),
            'entry_time': datetime.now(),
            'symbol': 'USDJPY',
            'direction': rule['entry_conditions']['direction'],
            'lot_size': result.volume,
            'entry_price': result.price,
            'entry_spread': get_current_spread(),
            'rule_version': rule['version'],
            'ai_judgment_id': ai_judgment_id,
            'market_data_snapshot_id': snapshot_id
        }
    )

    # エントリー理由を別テーブルに保存
    db.insert(
        table='entry_reasons',
        data={
            'trade_id': trade_id,
            'satisfied_signals': get_satisfied_signals(rule),
            'confidence': rule['confidence'],
            'daily_bias': rule['daily_bias'],
            'reasoning': rule['reasoning']
        }
    )

    return trade_id
```

---

## 5. エラーハンドリング

### 5.1 注文失敗

```python
def handle_order_error(result):
    error_code = result.retcode

    # リトライ可能なエラー
    if error_code in [mt5.TRADE_RETCODE_REQUOTE, mt5.TRADE_RETCODE_PRICE_OFF]:
        logger.warning(f"Retriable error: {result.comment}, retrying...")
        time.sleep(1)
        return "RETRY"

    # 致命的なエラー
    elif error_code in [mt5.TRADE_RETCODE_NO_MONEY, mt5.TRADE_RETCODE_INVALID_VOLUME]:
        logger.error(f"Fatal error: {result.comment}")
        send_alert(f"エントリー失敗（致命的）: {result.comment}")
        return "FATAL"

    # その他のエラー
    else:
        logger.error(f"Unknown error: {error_code} - {result.comment}")
        return "UNKNOWN"
```

### 5.2 リトライロジック

```python
def execute_entry_with_retry(max_retries=3):
    for attempt in range(max_retries):
        result = execute_entry()

        if result.retcode == mt5.TRADE_RETCODE_DONE:
            return result

        error_type = handle_order_error(result)

        if error_type == "FATAL":
            break

        if error_type == "RETRY" and attempt < max_retries - 1:
            continue

    logger.error("Entry failed after all retries")
    return None
```

---

## 6. パフォーマンス要件

### 6.1 処理速度

| 処理 | 目標時間 |
|------|---------|
| エントリー判断（全ステップ） | 1秒以内 |
| 注文実行（MT5通信含む） | 2秒以内 |
| 記録保存 | 500ms以内（非同期） |

### 6.2 信頼性

- **エントリー実行成功率**: 95%以上
- **シグナル検知精度**: 100%（ルールベースなので確実）

---

## 7. 実装ロードマップ

### Phase 3（Week 3-4）

**優先度: 最高**

- エントリー判断フロー全体
- ポジションサイズ計算
- ストップロス設定
- MT5注文実行
- エラーハンドリング
- 記録機能

---

**以上、トレード実行システム仕様書**
