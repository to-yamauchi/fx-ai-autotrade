# 監視・決済システム仕様書

## ドキュメント情報
- **作成日**: 2025-10-21
- **バージョン**: 1.0
- **カテゴリ**: システムアーキテクチャ - 監視・決済

---

## 1. 概要

### 1.1 役割

ポジション保有中の継続的監視と、適切なタイミングでの決済実行

### 1.2 設計原則

- **多層防御**: 3層の監視システムによる重層的な安全装置
- **即応性**: Layer 1は100ms、Layer 2は1分間隔の高速監視
- **柔軟性**: Layer 3でAI判断を組み込み、市場変化に適応

---

## 2. 3層監視構造

### 2.1 全体像

```
┌─────────────────────────────────────────┐
│   Layer 1: 緊急停止（100ms）              │
│   - 口座2%損失                           │
│   - ハードストップ50pips                  │
│   - スプレッド異常                        │
│   - フラッシュクラッシュ                  │
│   → 即座に成行決済                       │
└─────────────────────────────────────────┘
                ↑ 緊急時
┌─────────────────────────────────────────┐
│   Layer 2: 異常検知（1分/5分）            │
│   【1分ごと】                            │
│   - 重要レベルブレイク                    │
│   - インジケーター反転                    │
│   - 連続逆行                             │
│   【5分ごと】                            │
│   - AI回避条件発生                       │
│   - RSI過熱                              │
│   → Layer 3へエスカレーション            │
└─────────────────────────────────────────┘
                ↑ トリガー時
┌─────────────────────────────────────────┐
│   Layer 3: AI再評価                      │
│   【3a: 定期評価（15分）】               │
│   - Flash-Lite: 簡易チェック             │
│   - OK/WARNING/DANGER判定                │
│   【3b: 緊急評価（トリガー時）】         │
│   - Pro: 詳細分析                        │
│   - HOLD/CLOSE判断                       │
└─────────────────────────────────────────┘
```

### 2.2 Layer 1: 緊急停止（詳細）

**ルールエンジン仕様書を参照**

**重要ポイント**:
- 完全にルールベース（AI不使用）
- 100ms間隔の高速監視
- 検知即決済（躊躇なし）

### 2.3 Layer 2: 異常検知（詳細）

**ルールエンジン仕様書を参照**

**重要ポイント**:
- 市場環境変化の早期検知
- 自動決済はしない（Layer 3に委ねる）
- トリガー時は即座にエスカレーション

### 2.4 Layer 3: AI再評価（詳細）

**AI分析エンジン仕様書を参照**

**重要ポイント**:
- 定期評価（15分）で継続的チェック
- 緊急評価（トリガー時）で詳細判断
- 柔軟な意思決定（HOLD/部分決済/全決済）

---

## 3. 決済戦略

### 3.1 段階的利確

#### 3.1.1 概要

**目的**:
- 利益の確実な確保
- ポジション全体が逆行するリスク低減
- 大きな利益を伸ばす機会も維持

#### 3.1.2 実装

**AI生成ルール例**:
```json
{
  "take_profit": [
    {"pips": 10, "close_percent": 30, "reason": "早期利益確保"},
    {"pips": 20, "close_percent": 40, "reason": "主要利益確定"},
    {"pips": 30, "close_percent": 100, "reason": "目標達成"}
  ]
}
```

**実行フロー**:
```python
def check_take_profit():
    position = get_current_position()
    rule = get_current_rule_json()
    take_profit_levels = rule['exit_strategy']['take_profit']

    current_pips = calculate_current_pips(position)

    for level in take_profit_levels:
        # 達成済みかチェック
        if is_level_executed(level['pips']):
            continue

        # 目標pipsに到達
        if current_pips >= level['pips']:
            close_percent = level['close_percent']
            reason = level['reason']

            # 部分決済実行
            close_volume = position.volume * close_percent / 100
            result = mt5.Close(
                position_id=position.id,
                volume=close_volume,
                comment=f"TP: {reason}"
            )

            # 記録
            mark_level_executed(level['pips'])
            logger.info(f"Take profit: {close_percent}% at +{current_pips}pips ({reason})")
```

**例**:
- エントリー: 0.1 lot @ 149.60 BUY
- +10pips（149.70）到達: 0.03 lot決済、残り0.07 lot
- +20pips（149.80）到達: 0.04 lot決済（元の40%）、残り0.03 lot
- +30pips（149.90）到達: 0.03 lot決済、全決済完了

### 3.2 トレーリングストップ

#### 3.2.1 概要

**目的**: 含み益が一定水準を超えたら利益を守る

**特徴**:
- 利益を伸ばしながら、逆行時の保護
- 動的にストップロス位置を調整

#### 3.2.2 パラメータ

**AI生成ルール例**:
```json
{
  "stop_loss": {
    "initial": "account_2_percent",
    "trailing": {
      "activate_at_pips": 15,
      "trail_percent": 50,
      "comment": "+15pips到達で利益の50%を保護"
    }
  }
}
```

#### 3.2.3 実装

```python
def update_trailing_stop():
    position = get_current_position()
    rule = get_current_rule_json()
    trailing = rule['exit_strategy']['stop_loss']['trailing']

    current_pips = calculate_current_pips(position)

    # トレーリング未開始
    if current_pips < trailing['activate_at_pips']:
        return

    # 保護する利益を計算
    protected_pips = current_pips * trailing['trail_percent'] / 100

    # 新しいストップ位置
    if position.direction == "BUY":
        new_stop = position.entry_price + (protected_pips / 100)
    else:  # SELL
        new_stop = position.entry_price - (protected_pips / 100)

    # 現在のストップより有利な場合のみ更新
    if should_update_stop(position, new_stop):
        # MT5のストップロスは更新しない（保険SLは維持）
        # 内部管理のみ
        set_internal_trailing_stop(new_stop)
        logger.info(f"Trailing stop updated: protect +{protected_pips}pips")

def check_trailing_stop():
    internal_stop = get_internal_trailing_stop()
    if internal_stop is None:
        return

    position = get_current_position()
    current_price = get_current_price()

    # ストップ発動
    if position.direction == "BUY" and current_price <= internal_stop:
        close_position_all("Trailing stop hit")
    elif position.direction == "SELL" and current_price >= internal_stop:
        close_position_all("Trailing stop hit")
```

**動作例（BUY 149.60エントリー）**:
- +10pips（149.70）: トレーリング未開始
- +15pips（149.75）: トレーリング開始、ストップ = 149.60 + 7.5pips = 149.675
- +20pips（149.80）: ストップ更新 = 149.60 + 10pips = 149.70
- +30pips（149.90）: ストップ更新 = 149.60 + 15pips = 149.75
- 価格が149.75まで戻る: ストップ発動、+15pipsで決済

### 3.3 インジケーター決済

#### 3.3.1 概要

**目的**: テクニカル指標の反転シグナルで早期撤退

**特徴**:
- AI生成ルールで柔軟な条件設定
- 部分決済または全決済を選択

#### 3.3.2 AI生成ルール例

```json
{
  "indicator_exits": [
    {
      "condition": "MACDデッドクロス",
      "action": "CLOSE_50",
      "reason": "モメンタム低下の兆候"
    },
    {
      "condition": "M15足でEMA20を明確に下抜け（2本連続で下）",
      "action": "CLOSE_ALL",
      "reason": "短期トレンド転換"
    },
    {
      "condition": "RSI < 30",
      "action": "CLOSE_50",
      "reason": "売られすぎ反転の可能性"
    }
  ]
}
```

#### 3.3.3 実装

```python
def check_indicator_exits():
    rule = get_current_rule_json()
    indicator_exits = rule['exit_strategy']['indicator_exits']

    for exit_rule in indicator_exits:
        condition = exit_rule['condition']
        action = exit_rule['action']
        reason = exit_rule['reason']

        if evaluate_indicator_condition(condition):
            logger.info(f"Indicator exit triggered: {condition}")
            execute_exit_action(action, reason)

def evaluate_indicator_condition(condition):
    if "MACDデッドクロス" in condition:
        return check_macd_dead_cross()

    if "EMA20を明確に下抜け" in condition:
        return check_ema20_breakdown()

    if "RSI" in condition:
        threshold = extract_number(condition)
        operator = extract_operator(condition)  # '<' or '>'
        rsi = get_rsi()
        return eval(f"{rsi} {operator} {threshold}")

    # その他の条件...

def execute_exit_action(action, reason):
    if action == "CLOSE_ALL":
        close_position_all(reason)
    elif action.startswith("CLOSE_"):
        percent = int(action.split("_")[1])
        close_position_partial(percent, reason)
```

### 3.4 時間管理

#### 3.4.1 概要

**目的**: 長時間のポジション保有を避け、機会損失を防ぐ

**ルール**:
1. 2時間経過 かつ ±5pips以内 → 決済（機会損失回避）
2. 4時間経過 → 条件付き決済
3. 23:00到達 → 強制決済（日次クローズ）

#### 3.4.2 実装

```python
def check_time_exits():
    position = get_current_position()
    rule = get_current_rule_json()
    time_exits = rule['exit_strategy']['time_exits']

    hold_minutes = calculate_hold_minutes(position)
    current_pips = calculate_current_pips(position)

    # ルール1: 2時間 かつ 横ばい
    if hold_minutes >= 120 and abs(current_pips) <= 5:
        close_position_all("Time limit: 2h and sideways")
        return

    # ルール2: 4時間経過
    if hold_minutes >= time_exits['max_hold_minutes']:
        if position.profit > 0:
            close_position_all("Time limit: 4h and profitable")
        elif position.profit > -get_account_balance() * 0.01:
            logger.info("Max hold time reached, but within -1%, continue")
        else:
            close_position_all("Time limit: 4h and loss exceeded -1%")
        return

    # ルール3: 23:00強制決済
    current_time = datetime.now().time()
    force_close_time = datetime.strptime(time_exits['force_close_time'], "%H:%M").time()

    if current_time >= force_close_time:
        close_position_all("Force close: 23:00")
```

---

## 4. 決済実行

### 4.1 部分決済

```python
def close_position_partial(percent, reason="Partial close"):
    position = get_current_position()

    # 決済ロット計算
    close_volume = position.volume * percent / 100

    # MT5最小ロット確認
    if close_volume < 0.01:
        logger.warning(f"Close volume {close_volume} too small, skip")
        return

    # 決済実行
    result = mt5.Close(
        position_id=position.id,
        volume=close_volume,
        deviation=20,
        comment=reason
    )

    # 記録
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        logger.info(f"Partial close: {percent}% ({close_volume} lot) - {reason}")
        record_partial_close(position, close_volume, reason, result)
    else:
        logger.error(f"Partial close failed: {result.comment}")
```

### 4.2 全決済

```python
def close_position_all(reason="Full close"):
    position = get_current_position()

    # 決済実行
    result = mt5.Close(
        position_id=position.id,
        volume=position.volume,
        deviation=20,
        comment=reason
    )

    # 記録
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        logger.info(f"Full close: {position.volume} lot - {reason}")

        # トレード完了記録
        finalize_trade_record(
            trade_id=position.trade_id,
            exit_time=datetime.now(),
            exit_price=result.price,
            exit_spread=get_current_spread(),
            pips=calculate_final_pips(position, result.price),
            profit_loss=result.profit,
            exit_reason=reason,
            exit_category=categorize_exit_reason(reason)
        )
    else:
        logger.error(f"Full close failed: {result.comment}")
```

---

## 5. 統合監視ループ

### 5.1 メインループ

```python
import time
import threading

def monitoring_main():
    # Layer 1: 別スレッドで100ms監視
    layer1_thread = threading.Thread(target=layer1_monitor, daemon=True)
    layer1_thread.start()

    # Layer 2 + 決済監視: 1分ループ
    layer2_counter = 0
    layer3a_counter = 0

    while True:
        start_time = time.time()

        # ポジション確認
        if has_open_positions():
            # Layer 2: 1分ごと
            layer2_1min_checks()

            # Layer 2: 5分ごと
            layer2_counter += 1
            if layer2_counter >= 5:
                layer2_5min_checks()
                layer2_counter = 0

            # Layer 3a: 15分ごと
            layer3a_counter += 1
            if layer3a_counter >= 15:
                layer3a_periodic_evaluation()
                layer3a_counter = 0

            # 決済監視
            check_take_profit()
            update_trailing_stop()
            check_trailing_stop()
            check_indicator_exits()
            check_time_exits()

        # 1分間隔を維持
        elapsed = time.time() - start_time
        sleep_time = max(0, 60 - elapsed)
        time.sleep(sleep_time)
```

### 5.2 エラーハンドリング

```python
def monitoring_main_with_error_handling():
    while True:
        try:
            monitoring_main()
        except MT5ConnectionError as e:
            logger.error(f"MT5 connection error: {e}")
            time.sleep(5)
            reconnect_mt5()
        except Exception as e:
            logger.critical(f"Unexpected error in monitoring: {e}")
            send_alert(f"Monitoring system error: {e}")
            time.sleep(10)
```

---

## 6. パフォーマンス要件

### 6.1 応答時間

| 処理 | 頻度 | 目標時間 |
|------|------|---------|
| Layer 1監視 | 100ms | 50ms以内 |
| Layer 2監視 | 1分 | 500ms以内 |
| Layer 3a評価 | 15分 | 3秒以内 |
| Layer 3b評価 | トリガー時 | 10秒以内 |
| 決済実行 | 随時 | 1秒以内 |

### 6.2 信頼性

- **緊急停止応答**: 100ms以内
- **決済実行成功率**: 98%以上
- **稼働率**: 99.9%以上

---

## 7. ログとアラート

### 7.1 ログ記録

**重要イベント**:
- Layer 1緊急停止（CRITICAL）
- Layer 2トリガー（WARNING）
- Layer 3判断（INFO）
- 決済実行（INFO）
- エラー発生（ERROR）

### 7.2 アラート送信

**即座アラート**:
- Layer 1緊急停止
- 決済実行失敗
- システムエラー

**定期レポート**（将来）:
- 日次サマリー（23:30）
- 週次レポート（金曜23:30）

---

## 8. 実装ロードマップ

### Phase 1（Week 2）

**優先度: 最高**

- Layer 1緊急停止システム

### Phase 3（Week 3-4）

**優先度: 最高**

- Layer 2異常検知
- Layer 3統合
- 段階的利確
- トレーリングストップ
- インジケーター決済
- 時間管理
- 決済実行機能

---

**以上、監視・決済システム仕様書**
