# リスク管理仕様書

## ドキュメント情報
- **作成日**: 2025-10-21
- **バージョン**: 1.0
- **カテゴリ**: システムアーキテクチャ - リスク管理

---

## 1. 概要

### 1.1 目的

口座資金の保護と持続可能なトレード運用の実現

### 1.2 設計原則

- **多層防御**: 複数のセーフティネットによる重層的保護
- **保守的運用**: リスクを最小化し、着実な成長を目指す
- **自動制御**: ドローダウン時の自動対応

---

## 2. 口座保護の多層防御

### 2.1 全体構造

```
┌──────────────────────────────────────┐
│ Level 1: 保険ストップロス（MT5）      │
│  - 口座の5%                          │
│  - 最終防衛線（システム障害時）       │
└──────────────────────────────────────┘
              ↑ 緊急時
┌──────────────────────────────────────┐
│ Level 2: Layer 1監視                 │
│  - 口座の2%で強制決済                │
│  - ハードストップ50pips               │
│  - 100ms高速監視                     │
└──────────────────────────────────────┘
              ↑ 異常検知
┌──────────────────────────────────────┐
│ Level 3: Layer 2異常検知             │
│  - サポレジブレイク                   │
│  - インジケーター反転                 │
│  - Layer 3へエスカレーション          │
└──────────────────────────────────────┘
              ↑ トリガー時
┌──────────────────────────────────────┐
│ Level 4: Layer 3 AI判断              │
│  - 定期評価（15分）                  │
│  - 緊急評価（トリガー時）             │
│  - 柔軟な意思決定                    │
└──────────────────────────────────────┘
```

### 2.2 各レベル詳細

#### 2.2.1 Level 1: 保険ストップロス

**詳細**: トレード実行システム仕様書を参照

**設定**: 口座の5%

**目的**: システム完全停止時の最終防衛線

#### 2.2.2 Level 2: Layer 1監視

**詳細**: 監視・決済システム仕様書を参照

**設定**:
- 口座の2%で強制決済
- ハードストップ50pips

**目的**: 通常時の損失管理

#### 2.2.3 Level 3-4: Layer 2/3

**詳細**: 監視・決済システム仕様書を参照

**目的**: 市場環境変化への適応的対応

---

## 3. ポジションサイズ管理

### 3.1 基本方針

**原則**: 保守的なサイジング

### 3.2 サイジングルール

#### 3.2.1 基本設定（Phase 1-4）

| パラメータ | 値 | 説明 |
|-----------|-----|------|
| 基本ロット | 0.1 lot | 標準ポジションサイズ |
| 調整範囲 | 0.05〜0.1 lot | AIによる調整後 |
| 最大ポジション数 | 1 | 同時保有制限 |

#### 3.2.2 AI調整倍率

**AIが決定する position_size_multiplier**:

```json
{
  "position_size_multiplier": 0.8,
  "reason": "信頼度0.75だが、日足は下降トレンドのため保守的に"
}
```

**調整基準**:

| 信頼度 | ボラティリティ | 倍率 | 最終ロット |
|-------|--------------|------|-----------|
| 高（0.8+） | 通常 | 1.0 | 0.1 lot |
| 中（0.7-0.79） | 通常 | 0.8 | 0.08 lot |
| 中（0.7-0.79） | 高 | 0.7 | 0.07 lot |
| 低（0.6-0.69） | 通常 | 0.7 | 0.07 lot |
| 低（0.6-0.69） | 高 | 0.5 | 0.05 lot |

**ボラティリティ判定**:
- ATR(H1) > 0.20 (20pips): 高
- ATR(H1) ≤ 0.20: 通常

#### 3.2.3 実装

```python
def calculate_position_size(rule, market_data):
    # 基本ロット
    base_lot = 0.1

    # AI調整倍率
    multiplier = rule['risk_management']['position_size_multiplier']

    # ドローダウン調整
    drawdown_multiplier = get_drawdown_adjustment()

    # 最終ロット
    final_lot = base_lot * multiplier * drawdown_multiplier

    # MT5制約に合わせる
    final_lot = adjust_to_mt5_constraints(final_lot)

    logger.info(f"Position size: {final_lot} (base: {base_lot}, AI: {multiplier}, DD: {drawdown_multiplier})")

    return final_lot

def get_drawdown_adjustment():
    """ドローダウンに応じた調整"""
    current_dd = calculate_current_drawdown()

    if current_dd >= 0.07:  # 7%以上
        return 0.5  # 50%に縮小
    elif current_dd >= 0.05:  # 5%以上
        return 0.7  # 70%に縮小
    else:
        return 1.0  # 調整なし
```

### 3.3 最大ポジション数

**Phase 1-4**: 1ポジション

**理由**:
- シンプルな管理
- リスクの集中回避
- AIの学習データ蓄積優先

**Phase 5以降**: 拡張検討
- 複数通貨ペア対応時
- ポートフォリオ管理の導入

---

## 4. ドローダウン管理

### 4.1 最大許容ドローダウン

**絶対上限**: 10%

**測定方法**:
```python
def calculate_current_drawdown():
    # 最高残高
    peak_balance = db.query("SELECT MAX(balance) FROM account_snapshots").scalar()

    # 現在残高
    current_balance = mt5.account_info().balance

    # ドローダウン率
    drawdown = (peak_balance - current_balance) / peak_balance

    return drawdown
```

### 4.2 段階的対応

#### 4.2.1 警戒レベル（5%到達）

**トリガー**: ドローダウン ≥ 5%

**自動対応**:
```python
if current_dd >= 0.05:
    # 1. ポジションサイズ縮小
    set_drawdown_multiplier(0.7)  # 70%に

    # 2. エントリー条件厳格化
    set_min_confidence(0.75)  # 信頼度0.75以上のみ

    # 3. アラート送信
    send_alert("警戒レベル: ドローダウン5%到達")

    # 4. ログ記録
    logger.warning(f"Drawdown alert: {current_dd*100:.1f}%")
```

**手動確認事項**:
- 最近のトレード分析
- AI判断の精度確認
- プロンプトの見直し

#### 4.2.2 危険レベル（7%到達）

**トリガー**: ドローダウン ≥ 7%

**自動対応**:
```python
if current_dd >= 0.07:
    # 1. ポジションサイズ最小化
    set_drawdown_multiplier(0.5)  # 50%に（最小0.05 lot）

    # 2. エントリー条件最厳格化
    set_min_confidence(0.80)  # 信頼度0.80以上のみ

    # 3. 緊急アラート
    send_urgent_alert("危険レベル: ドローダウン7%到達")

    # 4. 詳細レポート生成
    generate_emergency_report()
```

**手動対応**:
- トレード履歴の徹底分析
- AI判断の問題点特定
- プロンプト大幅修正
- 必要に応じて一時停止検討

#### 4.2.3 停止レベル（10%到達）

**トリガー**: ドローダウン ≥ 10%

**自動対応**:
```python
if current_dd >= 0.10:
    # 1. 全トレード即座停止
    stop_all_trading()

    # 2. 既存ポジション決済
    close_all_positions("Drawdown limit: 10%")

    # 3. 緊急停止アラート
    send_critical_alert("停止レベル: ドローダウン10%到達、全トレード停止")

    # 4. 詳細分析レポート
    generate_full_analysis_report()

    # 5. 管理者通知
    notify_admin()
```

**再開条件**:
1. 徹底的な原因分析完了
2. 明確な改善策の実施
3. バックテストでの検証
4. デモ口座での再確認
5. 管理者の承認

### 4.3 ドローダウン監視

#### 4.3.1 継続監視

```python
def monitor_drawdown():
    """ドローダウンを継続的に監視"""

    while True:
        current_dd = calculate_current_drawdown()

        # ドローダウン記録
        record_drawdown(current_dd)

        # レベル判定と対応
        if current_dd >= 0.10:
            handle_stop_level()
        elif current_dd >= 0.07:
            handle_danger_level()
        elif current_dd >= 0.05:
            handle_warning_level()

        # 1時間ごとにチェック
        time.sleep(3600)
```

#### 4.3.2 記録

**データベース保存**:
```sql
CREATE TABLE drawdown_history (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    peak_balance DECIMAL(12, 2),
    current_balance DECIMAL(12, 2),
    drawdown_percent DECIMAL(6, 4),
    drawdown_level VARCHAR(20),  -- 'normal', 'warning', 'danger', 'stop'
    action_taken TEXT
);
```

---

## 5. リスク・リワード管理

### 5.1 目標比率

**リスク・リワード比**: 1:2以上

**意味**: 1pipsのリスクに対して2pips以上の利益を目指す

### 5.2 AI決済戦略での実現

**例**:
```json
{
  "exit_strategy": {
    "stop_loss": {
      "initial": "account_2_percent",
      "price_level": 149.40
    },
    "take_profit": [
      {"pips": 10, "close_percent": 30},
      {"pips": 20, "close_percent": 40},
      {"pips": 30, "close_percent": 100}
    ]
  }
}
```

**エントリー**: 149.60 BUY
**ストップロス**: 149.40（-20pips）
**利確目標**: +30pips（全決済）

**リスク・リワード比**: 20 / 30 = 1:1.5

**段階的利確考慮**:
- +10pipsで30%決済: 3pips確保
- +20pipsで40%決済: 8pips確保
- +30pipsで残り決済: 9pips確保
- **合計**: 20pips（リスク20pipsに対して1:1）

### 5.3 改善策

**AI判断精度向上**:
- バックテストでの検証
- プロンプト最適化
- 成功パターンの学習

**利益の伸ばし方**:
- トレーリングストップの活用
- トレンド時の追加エントリー（Phase 5以降）

---

## 6. 週次・月次チェック

### 6.1 週次レビュー（金曜23:30）

#### 6.1.1 確認事項

```python
def weekly_review():
    # 1. 損益確認
    week_pnl = calculate_week_pnl()

    # 2. ドローダウンチェック
    max_dd = get_week_max_drawdown()

    # 3. トレード統計
    stats = {
        'total_trades': get_week_trade_count(),
        'win_rate': calculate_week_win_rate(),
        'avg_pips': calculate_week_avg_pips(),
        'profit_factor': calculate_week_profit_factor()
    }

    # 4. AI精度
    ai_accuracy = {
        'direction_accuracy': calculate_week_direction_accuracy(),
        'entry_validity': calculate_week_entry_validity()
    }

    # 5. レポート生成
    report = generate_weekly_report(week_pnl, max_dd, stats, ai_accuracy)

    # 6. 保存
    save_weekly_report(report)

    return report
```

#### 6.1.2 評価基準

| 指標 | 目標 | 警告 |
|------|------|------|
| 週次勝率 | ≥60% | <50% |
| 週次pips | ≥+20pips | <0pips |
| 最大ドローダウン | <5% | ≥5% |
| プロフィットファクター | ≥1.5 | <1.2 |

### 6.2 月次レビュー（月末）

#### 6.2.1 確認事項

```python
def monthly_review():
    # 1. 月次損益
    month_pnl = calculate_month_pnl()

    # 2. バックテストとの比較
    backtest_comparison = compare_with_backtest()

    # 3. AI判断精度の推移
    ai_accuracy_trend = get_ai_accuracy_trend()

    # 4. システム改善点
    improvement_points = identify_improvement_points()

    # 5. コスト確認
    ai_cost = calculate_month_ai_cost()

    # 6. レポート生成
    report = generate_monthly_report(
        month_pnl, backtest_comparison,
        ai_accuracy_trend, improvement_points, ai_cost
    )

    return report
```

#### 6.2.2 評価基準

| 指標 | 目標 | 警告 |
|------|------|------|
| 月次勝率 | ≥60% | <55% |
| 月次リターン | ≥+2% | <+1% |
| 最大ドローダウン | <10% | ≥7% |
| AI方向性的中率 | ≥65% | <60% |
| 月次AIコスト | <$5 | >$10 |

---

## 7. 緊急停止プロトコル

### 7.1 緊急停止条件

**自動停止**:
1. ドローダウン10%到達
2. システムエラー（連続3回）
3. MT5接続不能（5分以上）
4. データ取得失敗（連続5回）

**手動停止**:
1. 管理者判断
2. 市場異常時
3. システムメンテナンス

### 7.2 停止手順

```python
def emergency_stop(reason):
    logger.critical(f"EMERGENCY STOP: {reason}")

    # 1. 新規エントリー停止
    disable_entry_system()

    # 2. 既存ポジション決済
    positions = mt5.positions_get()
    for position in positions:
        close_position(position, reason=f"Emergency stop: {reason}")

    # 3. 全監視システム停止
    stop_all_monitors()

    # 4. アラート送信
    send_critical_alert(f"緊急停止: {reason}")

    # 5. 詳細ログ記録
    log_emergency_stop(reason, positions)

    # 6. 管理者通知
    notify_admin_emergency(reason)
```

### 7.3 再開手順

```python
def resume_trading(approval_code):
    # 1. 承認コード確認
    if not verify_approval_code(approval_code):
        raise PermissionError("Invalid approval code")

    # 2. システム健全性チェック
    if not perform_health_check():
        raise SystemError("System health check failed")

    # 3. バックテスト検証
    if not verify_recent_backtest():
        raise ValidationError("Recent backtest verification required")

    # 4. 段階的再開
    enable_monitoring_systems()
    time.sleep(60)

    enable_entry_system(cautious_mode=True)

    logger.info("Trading resumed with cautious mode")
    send_alert("トレード再開（慎重モード）")
```

---

## 8. リスク指標のモニタリング

### 8.1 リアルタイム監視

```python
def monitor_risk_indicators():
    indicators = {
        'current_drawdown': calculate_current_drawdown(),
        'current_position_risk': calculate_position_risk(),
        'account_leverage': mt5.account_info().leverage,
        'margin_level': mt5.account_info().margin_level,
        'unrealized_pnl': get_unrealized_pnl()
    }

    # 警告判定
    if indicators['current_drawdown'] >= 0.05:
        send_alert(f"Drawdown warning: {indicators['current_drawdown']*100:.1f}%")

    if indicators['margin_level'] < 300:
        send_alert(f"Margin level warning: {indicators['margin_level']:.0f}%")

    # 記録
    record_risk_indicators(indicators)

    return indicators
```

### 8.2 ダッシュボード（将来）

**表示項目**:
- 現在のドローダウン
- 今日/今週/今月の損益
- ポジション状況
- リスク指標
- AI精度統計

---

## 9. 実装ロードマップ

### Phase 1-2（Week 1-2）

**優先度: 最高**

- Layer 1緊急停止
- 保険ストップロス設定
- 基本的なポジションサイズ計算

### Phase 3（Week 3-4）

**優先度: 高**

- ドローダウン監視
- 段階的対応ロジック
- 緊急停止プロトコル

### Phase 4-5（Week 4-8）

**優先度: 中**

- 週次・月次レビュー
- リスク指標モニタリング
- レポート自動生成

---

**以上、リスク管理仕様書**
