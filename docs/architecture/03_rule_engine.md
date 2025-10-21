# ルールエンジン仕様書

## ドキュメント情報
- **作成日**: 2025-10-21
- **バージョン**: 1.0
- **カテゴリ**: システムアーキテクチャ - 高速実行層

---

## 1. 概要

### 1.1 役割

AI生成ルールを高速に解釈・実行し、エントリー・決済を機械的に判定するコンポーネント

### 1.2 位置づけ

```
AI分析エンジン → 【ルールエンジン】 → MT5実行
                      ↓
                  3層監視システム
```

### 1.3 設計原則

- **高速性**: AI判断を待たない、100ms〜5分間隔の高頻度処理
- **確実性**: ルールベースの機械的判定、曖昧さなし
- **安全性**: 多層防御による口座保護最優先

---

## 2. アーキテクチャ

### 2.1 全体構成

```
┌─────────────────────────────────────────┐
│         ルールエンジン                    │
├─────────────────────────────────────────┤
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ Layer 1: 緊急停止（100ms）        │   │
│  │  - 口座2%損失監視                │   │
│  │  - ハードストップ50pips           │   │
│  │  - スプレッド異常                │   │
│  │  - フラッシュクラッシュ            │   │
│  └─────────────────────────────────┘   │
│           ↓ 緊急時                      │
│  ┌─────────────────────────────────┐   │
│  │ Layer 2: 異常検知（1分/5分）      │   │
│  │  - サポレジブレイク               │   │
│  │  - インジケーター反転              │   │
│  │  - 連続逆行                       │   │
│  │  - AI回避条件発生                 │   │
│  └─────────────────────────────────┘   │
│           ↓ トリガー時                  │
│  ┌─────────────────────────────────┐   │
│  │ Layer 3: AI再評価                │   │
│  │  - 3a: 定期評価（15分）           │   │
│  │  - 3b: 緊急評価（トリガー時）      │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ エントリー監視（1分）              │   │
│  │  - トレード可否確認                │   │
│  │  - 価格ゾーンチェック              │   │
│  │  - 必須シグナルチェック            │   │
│  │  - 回避条件チェック                │   │
│  │  - 最終ガードレール                │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ 決済監視（1分）                    │   │
│  │  - 段階的利確                      │   │
│  │  - トレーリングストップ            │   │
│  │  - インジケーター決済              │   │
│  │  - 時間管理                        │   │
│  └─────────────────────────────────┘   │
│                                         │
└─────────────────────────────────────────┘
```

---

## 3. Layer 1: 緊急停止（100msごと）

### 3.1 目的

致命的損失の即座防止

### 3.2 監視項目

#### 3.2.1 口座の2%損失

**検知条件**:
```python
position_loss = current_price - entry_price  # SELL時は逆
loss_amount = position_loss * lot_size * pip_value
account_balance = get_account_balance()

if loss_amount > account_balance * 0.02:
    trigger_emergency_close("2% loss limit")
```

**処理**:
- 即座に成行決済
- 記録: "Emergency: 2% loss limit"
- Layer 2/3への通知（事後）

#### 3.2.2 ハードストップ（50pips）

**検知条件**:
```python
pips_from_entry = abs(current_price - entry_price) * 100

if position_direction == "BUY" and current_price < entry_price:
    if pips_from_entry >= 50:
        trigger_emergency_close("Hard stop: 50pips")
elif position_direction == "SELL" and current_price > entry_price:
    if pips_from_entry >= 50:
        trigger_emergency_close("Hard stop: 50pips")
```

**処理**:
- 即座に成行決済
- 記録: "Hard stop: 50pips"

#### 3.2.3 スプレッド異常

**検知条件**:
```python
spread = (ask - bid) * 100  # pips

if spread > 20:
    trigger_emergency_close("Spread alert")
```

**理由**: 異常スプレッド時は決済価格が大幅に不利になる可能性

#### 3.2.4 フラッシュクラッシュ

**検知条件**:
```python
# 0.1秒間の価格変動を監視
price_change_100ms = abs(current_price - price_100ms_ago) * 100

if price_change_100ms >= 30:
    trigger_emergency_close("Flash crash detected")
```

**理由**: 異常な急変動は市場の流動性危機やシステムエラーの可能性

### 3.3 実装詳細

#### 3.3.1 監視ループ

```python
import time

def layer1_monitor():
    while True:
        start_time = time.time()

        # ポジション確認
        positions = get_open_positions()

        for position in positions:
            # 2%損失チェック
            check_2percent_loss(position)

            # 50pipsハードストップチェック
            check_hard_stop(position)

            # スプレッドチェック
            check_spread_anomaly()

            # フラッシュクラッシュチェック
            check_flash_crash()

        # 100ms間隔を維持
        elapsed = time.time() - start_time
        sleep_time = max(0, 0.1 - elapsed)
        time.sleep(sleep_time)
```

#### 3.3.2 緊急決済実行

```python
def trigger_emergency_close(reason):
    logger.critical(f"EMERGENCY CLOSE: {reason}")

    # 成行決済
    result = mt5.Close(
        position_id=position.id,
        volume=position.volume,
        deviation=50  # 大きめの許容スリッページ
    )

    # 記録
    record_emergency_close(position, reason, result)

    # アラート
    send_alert(f"緊急決済: {reason}")
```

### 3.4 パフォーマンス要件

- **応答時間**: 100ms以内
- **決済実行**: 検知から500ms以内（MT5通信含む）
- **稼働率**: 99.99%

---

## 4. Layer 2: 異常検知（1分/5分定期）

### 4.1 目的

市場環境変化の早期発見、Layer 3へのエスカレーション

### 4.2 1分ごとの監視

#### 4.2.1 重要レベルブレイク

**検知条件**:
```python
# AI生成のcritical_support/resistanceを使用
if position_direction == "BUY":
    if current_price < critical_support:
        escalate_to_layer3("Critical support broken")

elif position_direction == "SELL":
    if current_price > critical_resistance:
        escalate_to_layer3("Critical resistance broken")
```

#### 4.2.2 インジケーター反転

**MACD クロス**:
```python
# BUYポジション保有中
if position_direction == "BUY":
    if macd_previous > macd_signal_previous and macd_current < macd_signal_current:
        escalate_to_layer3("MACD dead cross")

# SELLポジション保有中
elif position_direction == "SELL":
    if macd_previous < macd_signal_previous and macd_current > macd_signal_current:
        escalate_to_layer3("MACD golden cross")
```

**EMA クロス**:
```python
# M15足のEMA20/50クロス
if position_direction == "BUY":
    if ema20_m15 < ema50_m15:
        escalate_to_layer3("M15 EMA bearish cross")
```

#### 4.2.3 連続逆行

**検知条件**:
```python
# 15分足で3本連続逆方向
m15_candles = get_m15_last_3()

if position_direction == "BUY":
    if all(c['close'] < c['open'] for c in m15_candles):
        escalate_to_layer3("3 consecutive bearish M15 candles")

elif position_direction == "SELL":
    if all(c['close'] > c['open'] for c in m15_candles):
        escalate_to_layer3("3 consecutive bullish M15 candles")
```

### 4.3 5分ごとの監視

#### 4.3.1 AI避けるべき条件

**検知条件**:
```python
# AI生成のavoid_if条件をチェック
avoid_conditions = rule_json['entry_conditions']['avoid_if']

for condition in avoid_conditions:
    if evaluate_condition(condition):
        escalate_to_layer3(f"Avoid condition met: {condition}")
```

**条件評価例**:
```python
def evaluate_condition(condition):
    if "RSI" in condition and ">" in condition:
        threshold = extract_number(condition)
        return rsi_current > threshold

    if "スプレッド" in condition:
        threshold = extract_number(condition)
        return current_spread > threshold

    # その他の条件...
```

#### 4.3.2 RSI過熱

**検知条件**:
```python
if position_direction == "BUY" and rsi > 80:
    escalate_to_layer3("RSI overbought (>80)")

elif position_direction == "SELL" and rsi < 20:
    escalate_to_layer3("RSI oversold (<20)")
```

### 4.4 エスカレーション処理

```python
def escalate_to_layer3(trigger_reason):
    logger.warning(f"Layer 2 trigger: {trigger_reason}")

    # Layer 3b（緊急評価）を呼び出し
    ai_response = call_layer3b_emergency_evaluation(
        position=current_position,
        trigger_reason=trigger_reason,
        market_data=get_current_market_data()
    )

    # AI判断に基づいて実行
    execute_ai_decision(ai_response)
```

---

## 5. Layer 3: AI再評価

### 5.1 Layer 3a: 定期評価（15分ごと）

**詳細**: AI分析エンジン仕様書を参照

**ルールエンジンでの処理**:
```python
def layer3a_periodic_evaluation():
    if not has_open_positions():
        return  # ポジションなしなら実行しない

    # Flash-Lite呼び出し
    ai_response = call_gemini_flash_lite(
        compressed_data=compress_position_data()
    )

    # 応答処理
    if ai_response['s'] == 'DANGER':
        # Layer 3bへエスカレーション
        escalate_to_layer3b()
    elif ai_response['a'] in ['CLOSE_PARTIAL', 'CLOSE_ALL']:
        execute_ai_decision(ai_response)
    else:
        # 記録のみ
        log_layer3a_result(ai_response)
```

### 5.2 Layer 3b: 緊急評価（トリガー時）

**呼び出し条件**:
- Layer 2が異常検知
- Layer 3aがDANGERを返した

**処理**:
```python
def call_layer3b_emergency_evaluation(position, trigger_reason, market_data):
    # Gemini Pro呼び出し
    ai_response = call_gemini_pro(
        position_info=position,
        trigger_reason=trigger_reason,
        market_data=market_data,
        original_prediction=get_original_prediction()
    )

    return ai_response

def execute_ai_decision(ai_response):
    decision = ai_response['decision']

    if decision == 'HOLD':
        # ストップロス調整のみ
        if 'stop_loss_adjustment' in ai_response:
            adjust_stop_loss(ai_response['stop_loss_adjustment'])

    elif decision.startswith('CLOSE_'):
        percent = extract_percent(decision)  # CLOSE_50 -> 50
        close_position_partial(percent)

    # 記録
    record_layer3b_decision(ai_response)
```

---

## 6. エントリー監視（1分ごと）

### 6.1 エントリー判断フロー

```python
def entry_monitor():
    # Step 1: トレード可否確認
    if not should_trade_today():
        return

    # Step 2: 価格ゾーンチェック
    if not in_price_zone():
        return

    # Step 3: 必須シグナルチェック
    if not all_required_signals_met():
        return

    # Step 4: 回避条件チェック
    if any_avoid_condition_met():
        return

    # Step 5: 最終ガードレール
    if not final_guardrails_pass():
        return

    # 全てクリア → エントリー実行
    execute_entry()
```

### 6.2 各ステップ詳細

#### 6.2.1 Step 1: トレード可否確認

```python
def should_trade_today():
    rule = get_current_rule_json()

    # daily_biasがNEUTRAL
    if rule['daily_bias'] == 'NEUTRAL':
        logger.info("Entry skipped: daily_bias is NEUTRAL")
        return False

    # should_tradeがfalse
    if not rule['entry_conditions']['should_trade']:
        logger.info("Entry skipped: should_trade is false")
        return False

    # 既にポジション保有中
    if has_open_positions():
        logger.info("Entry skipped: already in position")
        return False

    return True
```

#### 6.2.2 Step 2: 価格ゾーンチェック

```python
def in_price_zone():
    rule = get_current_rule_json()
    price_zone = rule['entry_conditions']['price_zone']

    current_price = get_current_price()

    if price_zone['min'] <= current_price <= price_zone['max']:
        return True
    else:
        logger.debug(f"Price {current_price} outside zone {price_zone}")
        return False
```

#### 6.2.3 Step 3: 必須シグナルチェック

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
    # 自然言語条件をプログラム的に評価
    if "EMA20を上抜け" in signal:
        return current_price > ema20_m15

    if "RSI > 50" in signal:
        return rsi > 50

    if "MACDがゴールデンクロス" in signal:
        return macd > macd_signal

    if "スプレッド < 10pips" in signal:
        return current_spread < 10

    # その他の条件...
```

#### 6.2.4 Step 4: 回避条件チェック

```python
def any_avoid_condition_met():
    rule = get_current_rule_json()
    avoid_if = rule['entry_conditions']['avoid_if']

    for condition in avoid_if:
        if evaluate_condition(condition):
            logger.info(f"Entry avoided: {condition}")
            return True

    return False
```

#### 6.2.5 Step 5: 最終ガードレール

```python
def final_guardrails_pass():
    # スプレッドチェック
    if current_spread > 10:
        logger.info("Entry blocked: spread > 10pips")
        return False

    # 口座残高チェック
    if not has_sufficient_balance():
        logger.warning("Entry blocked: insufficient balance")
        return False

    # 重要指標発表チェック
    if is_near_major_news(minutes=30):
        logger.info("Entry blocked: major news within 30 minutes")
        return False

    return True
```

### 6.3 エントリー実行

```python
def execute_entry():
    rule = get_current_rule_json()

    # ポジションサイズ決定
    lot_size = calculate_lot_size(rule)

    # ストップロス計算
    stop_loss = calculate_stop_loss(rule)

    # 保険ストップロス（MT5に設定、口座の5%）
    insurance_sl = calculate_insurance_stop_loss()

    # 注文実行
    direction = rule['entry_conditions']['direction']

    if direction == "BUY":
        result = mt5.Buy(
            symbol="USDJPY",
            volume=lot_size,
            sl=insurance_sl,
            comment="AI Entry BUY"
        )
    else:
        result = mt5.Sell(
            symbol="USDJPY",
            volume=lot_size,
            sl=insurance_sl,
            comment="AI Entry SELL"
        )

    # 記録
    record_entry(result, rule)
```

---

## 7. 決済監視（1分ごと）

### 7.1 段階的利確

```python
def check_take_profit():
    position = get_current_position()
    rule = get_current_rule_json()
    take_profit_levels = rule['exit_strategy']['take_profit']

    current_pips = calculate_current_pips(position)

    for level in take_profit_levels:
        if current_pips >= level['pips'] and not is_level_executed(level):
            close_percent = level['close_percent']
            close_position_partial(close_percent)
            mark_level_executed(level)
            logger.info(f"Take profit: {close_percent}% at +{level['pips']}pips")
```

### 7.2 トレーリングストップ

```python
def update_trailing_stop():
    position = get_current_position()
    rule = get_current_rule_json()
    trailing = rule['exit_strategy']['stop_loss']['trailing']

    current_pips = calculate_current_pips(position)

    # トレーリング開始条件
    if current_pips >= trailing['activate_at_pips']:
        # 保護する利益
        protected_pips = current_pips * trailing['trail_percent'] / 100

        # 新しいストップ位置
        new_stop = position.entry_price + (protected_pips / 100)  # BUY時

        # 現在のストップより有利な場合のみ更新
        if new_stop > position.current_stop_loss:
            update_stop_loss(new_stop)
            logger.info(f"Trailing stop updated to +{protected_pips}pips")
```

### 7.3 インジケーター決済

```python
def check_indicator_exits():
    rule = get_current_rule_json()
    indicator_exits = rule['exit_strategy']['indicator_exits']

    for exit_rule in indicator_exits:
        condition = exit_rule['condition']
        action = exit_rule['action']

        if evaluate_condition(condition):
            logger.info(f"Indicator exit: {condition}")
            execute_exit_action(action)
```

### 7.4 時間管理

```python
def check_time_exits():
    position = get_current_position()
    rule = get_current_rule_json()
    time_exits = rule['exit_strategy']['time_exits']

    # 保有時間チェック
    hold_minutes = calculate_hold_minutes(position)

    if hold_minutes >= time_exits['max_hold_minutes']:
        # 含み益確認
        if position.profit > 0:
            close_position_all("Time limit: profitable")
        elif position.profit > -account_balance * 0.01:  # -1%以内
            logger.info("Max hold time reached, but within -1%, continue")
        else:
            close_position_all("Time limit: loss exceeded -1%")

    # 強制決済時刻チェック（23:00）
    current_time = datetime.now().time()
    force_close_time = datetime.strptime(time_exits['force_close_time'], "%H:%M").time()

    if current_time >= force_close_time:
        close_position_all("Force close: 23:00")
```

---

## 8. ルールJSON管理

### 8.1 ルール更新

```python
def update_rule_json(new_rule):
    # バージョン管理
    current_version = get_current_rule_version()
    new_version = increment_version(current_version)

    # 保存
    save_rule_json(new_rule, new_version)

    # アクティブ化
    set_active_rule(new_version)

    logger.info(f"Rule updated: v{current_version} -> v{new_version}")
```

### 8.2 ルール検証

```python
def validate_rule_json(rule):
    required_fields = [
        'daily_bias',
        'entry_conditions',
        'exit_strategy',
        'risk_management'
    ]

    for field in required_fields:
        if field not in rule:
            raise ValueError(f"Missing required field: {field}")

    # 値の範囲チェック
    if rule['confidence'] < 0 or rule['confidence'] > 1:
        raise ValueError("Confidence must be between 0 and 1")

    # その他の検証...
```

---

## 9. パフォーマンス要件

### 9.1 処理速度

| 処理 | 頻度 | 目標時間 |
|------|------|---------|
| Layer 1監視 | 100ms | 50ms以内 |
| Layer 2監視（1分） | 1分 | 500ms以内 |
| Layer 2監視（5分） | 5分 | 1秒以内 |
| エントリー監視 | 1分 | 1秒以内 |
| 決済監視 | 1分 | 1秒以内 |

### 9.2 信頼性

- **稼働率**: 99.9%以上
- **緊急停止応答**: 100ms以内
- **エントリー実行成功率**: 95%以上

---

## 10. 実装ロードマップ

### Phase 1（Week 2）

**優先度: 最高**

- Layer 1緊急停止システム
- 基本的な監視ループ
- MT5決済実行

### Phase 3（Week 3-4）

**優先度: 最高**

- ルールエンジン本体
- エントリー監視と実行
- Layer 2異常検知
- Layer 3統合
- 決済システム

---

**以上、ルールエンジン仕様書**
