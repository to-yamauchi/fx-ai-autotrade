# バックテスト仕様書

## ドキュメント情報
- **作成日**: 2025-10-21
- **バージョン**: 1.0
- **カテゴリ**: システムアーキテクチャ - 検証システム

---

## 1. 概要

### 1.1 疑似バックテストの概念

#### 1.1.1 従来のバックテストとの違い

**従来のバックテスト**:
- 固定された戦略を過去データでシミュレーション
- パラメータ最適化が主目的
- 損益の検証

**疑似バックテスト（本システム）**:
- AIの判断を過去データで再現・評価
- AI判断の精度と一貫性を検証
- 本番運用前の信頼性評価

#### 1.1.2 目的

1. **AI判断精度の検証**: 方向性、タイミングの的中率
2. **判断の一貫性確認**: 同じデータから同じ結論を導くか
3. **実運用前の信頼性評価**: デモ運用前の事前確認
4. **プロンプト最適化**: 判断精度向上のための改善

---

## 2. バックテストの種類

### 2.1 タイプA: AI判断精度バックテスト

**目的**: AIの市場予測能力を評価

**実行内容**:
1. 過去の各営業日08:00時点のデータを再現
2. AIに朝の詳細分析を実行させる
3. その日の実際の動きと比較
4. 的中率・一貫性を評価

### 2.2 タイプB: ルール妥当性バックテスト

**目的**: 生成されたルールの有効性を評価

**実行内容**:
1. AIが生成したエントリー条件を過去に適用
2. 条件を満たした場合の仮想エントリー
3. 決済ルールに従った仮想決済
4. 仮想損益を計算

### 2.3 タイプC: システム全体バックテスト

**目的**: エンドツーエンドの動作確認

**実行内容**:
1. データ処理から決済まで全フロー実行
2. Layer 1/2/3の動作確認
3. 緊急停止の発動状況確認

---

## 3. タイプA: AI判断精度バックテスト

### 3.1 実行プロセス

```
【期間指定】例: 2024年9月1日〜30日

【各営業日ごとに】

1. 08:00時点のデータスナップショット取得
   ├─ その時点から見た過去データ（D1, H4, H1, M15）
   ├─ テクニカル指標
   └─ 市場環境情報

2. データ標準化
   └─ 本番と同じフォーマットに変換

3. AI分析を3回実行（再現性確認）
   ├─ 同じデータで3回分析
   ├─ temperature: 0.3（本番と同じ）
   └─ 各応答を記録

4. 一貫性チェック
   ├─ 3回の予測が一致するか
   ├─ daily_bias の一致率
   └─ confidence の標準偏差

5. 実際の結果取得
   ├─ その日の高値・安値・終値
   ├─ 値幅
   └─ 方向性

6. 評価
   ├─ 予測の的中/外れ
   ├─ エントリー判断の妥当性
   └─ スコア算出
```

### 3.2 実装例

```python
import pandas as pd
from datetime import datetime, timedelta

def run_ai_judgment_backtest(start_date, end_date):
    results = []

    # 営業日を取得
    business_days = get_business_days(start_date, end_date)

    for date in business_days:
        print(f"Testing {date}...")

        # 1. データスナップショット取得（08:00時点）
        snapshot_time = datetime.combine(date, datetime.min.time().replace(hour=8))
        market_data = get_historical_market_data(snapshot_time)

        # 2. データ標準化
        standardized_data = standardize_market_data(market_data)

        # 3. AI分析を3回実行
        ai_responses = []
        for i in range(3):
            response = call_gemini_pro_analysis(
                market_data=standardized_data,
                temperature=0.3,
                prompt_version="v1.0.0"
            )
            ai_responses.append(response)

        # 4. 一貫性チェック
        consistency = check_consistency(ai_responses)

        # 5. 実際の結果取得
        actual_result = get_actual_market_result(date)

        # 6. 評価
        evaluation = evaluate_prediction(ai_responses[0], actual_result, consistency)

        # 結果保存
        results.append({
            'date': date,
            'ai_prediction': ai_responses[0],
            'consistency': consistency,
            'actual_result': actual_result,
            'evaluation': evaluation
        })

    # レポート生成
    report = generate_backtest_report(results)
    return report

def check_consistency(ai_responses):
    """3回の応答の一貫性をチェック"""

    # daily_bias の一致率
    biases = [r['daily_bias'] for r in ai_responses]
    bias_consistency = biases.count(biases[0]) / len(biases)

    # confidence の標準偏差
    confidences = [r['confidence'] for r in ai_responses]
    confidence_std = np.std(confidences)

    # should_trade の一致率
    should_trades = [r['entry_conditions']['should_trade'] for r in ai_responses]
    should_trade_consistency = should_trades.count(should_trades[0]) / len(should_trades)

    return {
        'bias_consistency': bias_consistency,
        'confidence_std': confidence_std,
        'should_trade_consistency': should_trade_consistency,
        'overall_score': (bias_consistency + should_trade_consistency) / 2
    }

def evaluate_prediction(ai_prediction, actual_result, consistency):
    """予測と実際の結果を比較評価"""

    evaluation = {
        'direction_correct': False,
        'entry_judgment_valid': False,
        'consistency_score': consistency['overall_score']
    }

    # 方向性の的中
    predicted_bias = ai_prediction['daily_bias']
    actual_direction = actual_result['direction']

    if predicted_bias == actual_direction:
        evaluation['direction_correct'] = True
    elif predicted_bias == 'NEUTRAL' and abs(actual_result['range_pips']) < 20:
        evaluation['direction_correct'] = True

    # エントリー判断の妥当性
    should_trade = ai_prediction['entry_conditions']['should_trade']

    if should_trade and actual_result['range_pips'] >= 20:
        evaluation['entry_judgment_valid'] = True
    elif not should_trade and actual_result['range_pips'] < 20:
        evaluation['entry_judgment_valid'] = True

    # 総合スコア
    evaluation['total_score'] = (
        evaluation['direction_correct'] * 40 +
        evaluation['entry_judgment_valid'] * 30 +
        evaluation['consistency_score'] * 30
    )

    return evaluation
```

### 3.3 評価指標

#### 3.3.1 方向性的中率

**計算**:
```python
def calculate_direction_accuracy(results):
    correct = sum(1 for r in results if r['evaluation']['direction_correct'])
    total = len(results)
    return correct / total
```

**目標**: 65%以上

#### 3.3.2 エントリー判断妥当性

**計算**:
```python
def calculate_entry_validity(results):
    valid = sum(1 for r in results if r['evaluation']['entry_judgment_valid'])
    total = len(results)
    return valid / total
```

**目標**: 70%以上

#### 3.3.3 判断の一貫性

**計算**:
```python
def calculate_overall_consistency(results):
    consistency_scores = [r['consistency']['overall_score'] for r in results]
    return np.mean(consistency_scores)
```

**目標**: 90%以上

---

## 4. タイプB: ルール妥当性バックテスト

### 4.1 実行プロセス

```
【各営業日ごとに】

1. AIにルール生成させる（朝の分析）

2. その日の1分足データでシミュレーション
   ├─ エントリー条件監視
   ├─ 条件達成時に仮想エントリー
   └─ エントリー価格・時刻を記録

3. 決済条件監視
   ├─ 段階的利確
   ├─ ストップロス
   ├─ インジケーター決済
   └─ 時間管理

4. 仮想決済
   └─ 決済価格・時刻・pips・損益を記録

5. 日次集計
   └─ 勝敗・損益・保有時間等を集計
```

### 4.2 実装例

```python
def run_rule_validity_backtest(start_date, end_date):
    results = []

    for date in get_business_days(start_date, end_date):
        # 1. AIにルール生成
        morning_data = get_historical_market_data(date, hour=8)
        rule = generate_ai_rule(morning_data)

        # 2. その日のシミュレーション
        day_result = simulate_day_trading(date, rule)

        results.append(day_result)

    # 統計計算
    stats = calculate_trading_stats(results)
    return stats

def simulate_day_trading(date, rule):
    """1日のトレードをシミュレーション"""

    # その日の1分足データを取得
    m1_data = get_m1_data(date)

    position = None
    trades = []

    for timestamp, candle in m1_data.iterrows():
        # ポジションなし → エントリー監視
        if position is None:
            if check_entry_conditions(rule, candle, m1_data, timestamp):
                position = {
                    'entry_time': timestamp,
                    'entry_price': candle['close'],
                    'direction': rule['entry_conditions']['direction'],
                    'lot_size': 0.1 * rule['risk_management']['position_size_multiplier']
                }
                print(f"  Virtual entry: {position['direction']} @ {position['entry_price']}")

        # ポジションあり → 決済監視
        else:
            exit_reason = check_exit_conditions(rule, position, candle, timestamp)

            if exit_reason:
                trade = close_virtual_position(position, candle['close'], exit_reason)
                trades.append(trade)
                position = None
                print(f"  Virtual exit: {exit_reason}, {trade['pips']}pips")

    # 23:00に強制決済
    if position is not None:
        trade = close_virtual_position(position, m1_data.iloc[-1]['close'], "Force close 23:00")
        trades.append(trade)

    return {
        'date': date,
        'rule': rule,
        'trades': trades
    }

def check_entry_conditions(rule, candle, m1_data, timestamp):
    """エントリー条件チェック（簡易版）"""

    # Step 1: トレード可否
    if rule['daily_bias'] == 'NEUTRAL':
        return False
    if not rule['entry_conditions']['should_trade']:
        return False

    # Step 2: 価格ゾーン
    price_zone = rule['entry_conditions']['price_zone']
    if not (price_zone['min'] <= candle['close'] <= price_zone['max']):
        return False

    # Step 3-5: 簡易実装（実際はルールエンジンと同じロジック）
    # ...

    return True

def check_exit_conditions(rule, position, candle, timestamp):
    """決済条件チェック"""

    current_pips = calculate_pips(position['entry_price'], candle['close'], position['direction'])

    # Layer 1: 緊急停止
    if current_pips <= -50:
        return "Hard stop: 50pips"

    # 段階的利確
    for level in rule['exit_strategy']['take_profit']:
        if current_pips >= level['pips'] and not is_level_executed(level['pips']):
            return f"Take profit: {level['pips']}pips"

    # 時間管理: 23:00
    if timestamp.hour >= 23:
        return "Force close: 23:00"

    # その他の決済条件...

    return None
```

### 4.3 評価指標

```python
def calculate_trading_stats(results):
    all_trades = []
    for day in results:
        all_trades.extend(day['trades'])

    df = pd.DataFrame(all_trades)

    stats = {
        'total_trades': len(df),
        'winning_trades': len(df[df['pips'] > 0]),
        'losing_trades': len(df[df['pips'] < 0]),
        'win_rate': len(df[df['pips'] > 0]) / len(df),

        'total_pips': df['pips'].sum(),
        'average_win': df[df['pips'] > 0]['pips'].mean(),
        'average_loss': df[df['pips'] < 0]['pips'].mean(),

        'largest_win': df['pips'].max(),
        'largest_loss': df['pips'].min(),

        'profit_factor': abs(df[df['pips'] > 0]['pips'].sum() / df[df['pips'] < 0]['pips'].sum()),

        'max_consecutive_losses': calculate_max_consecutive_losses(df),
    }

    return stats
```

---

## 5. 結果レポート

### 5.1 サマリーレポート

```json
{
  "backtest_info": {
    "type": "AI判断精度バックテスト",
    "start_date": "2024-09-01",
    "end_date": "2024-09-30",
    "business_days": 22,
    "prompt_version": "v1.0.0",
    "model": "Gemini 2.5 Pro"
  },

  "ai_judgment_accuracy": {
    "direction_accuracy": 0.68,
    "entry_judgment_validity": 0.73,
    "judgment_consistency": 0.92
  },

  "virtual_trading_performance": {
    "total_trades": 18,
    "win_rate": 0.61,
    "total_pips": 125,
    "average_win": 28,
    "average_loss": -15,
    "profit_factor": 1.85,
    "largest_win": 45,
    "largest_loss": -30
  },

  "market_environment_breakdown": {
    "trending_up": {
      "days": 8,
      "accuracy": 0.75,
      "avg_pips": 22
    },
    "trending_down": {
      "days": 7,
      "accuracy": 0.71,
      "avg_pips": 18
    },
    "ranging": {
      "days": 7,
      "accuracy": 0.57,
      "avg_pips": -5
    }
  },

  "success_patterns": [
    "EMA配列が明確な時の方向性的中率: 85%",
    "RSI中立圏（40-60）でのエントリー判断: 妥当性80%",
    "欧州市場開始後のエントリー: 勝率70%"
  ],

  "failure_patterns": [
    "レンジ相場での方向性予測: 的中率50%",
    "東京時間の小動きでの早期エントリー: 勝率40%",
    "ボラティリティ低下時のトレード: 平均+3pips"
  ],

  "recommendations": [
    "プロンプト改善: レンジ判定の精度向上",
    "ルール調整: 東京時間のエントリー条件を厳格化",
    "パラメータ調整: ボラティリティ低時はposition_multiplier 0.5に"
  ]
}
```

### 5.2 詳細レポート（日次）

```csv
date,daily_bias,confidence,direction_correct,entry_valid,consistency,trades,win_rate,pips
2024-09-01,BUY,0.75,True,True,0.95,1,100%,25
2024-09-02,SELL,0.68,True,True,0.88,1,100%,18
2024-09-03,NEUTRAL,0.45,True,True,0.92,0,-,0
2024-09-04,BUY,0.72,False,False,0.91,1,0%,-15
...
```

---

## 6. プロンプト改善サイクル

### 6.1 改善フロー

```
1. バックテスト実行
   ↓
2. 失敗パターン分析
   ↓
3. プロンプト修正
   ↓
4. 再バックテスト
   ↓
5. 改善確認
   ↓
6. バージョン更新
```

### 6.2 例: レンジ判定改善

**問題**: レンジ相場での方向性的中率が50%

**分析**:
- AIがレンジをトレンドと誤判定
- ボリンジャーバンド幅が狭い時の判断が不安定

**プロンプト修正**:
```
【追加】
レンジ判定基準:
- ボリンジャーバンド幅 < 20pips
- EMA20とEMA50の差 < 10pips
- 過去3時間の値幅 < 30pips
上記3つ全て該当 → daily_bias: NEUTRAL
```

**再テスト**:
- レンジ相場での方向性的中率: 50% → 85%（NEUTRAL判定）
- 全体的中率: 68% → 72%

**バージョン更新**: v1.0.0 → v1.1.0

---

## 7. データベース保存

### 7.1 バックテスト結果テーブル

**スキーマ**: データベース仕様書を参照

### 7.2 保存例

```python
def save_backtest_results(results, config):
    run_id = generate_uuid()

    db.insert(
        table='backtest_results',
        data={
            'run_id': run_id,
            'run_date': datetime.now(),
            'start_date': config['start_date'],
            'end_date': config['end_date'],
            'prompt_version': config['prompt_version'],
            'model_name': config['model_name'],
            'total_days': len(results),
            'direction_accuracy': calculate_direction_accuracy(results),
            'entry_judgment_validity': calculate_entry_validity(results),
            'consistency_score': calculate_consistency_score(results),
            'virtual_total_pips': calculate_total_pips(results),
            'virtual_profit_loss': calculate_profit_loss(results),
            'virtual_win_rate': calculate_win_rate(results),
            'daily_results': json.dumps(results)
        }
    )
```

---

## 8. 実装ロードマップ

### Phase 4（Week 4）

**優先度: 高**

- タイプA: AI判断精度バックテスト
- 一貫性チェック機能
- 評価指標計算
- レポート生成

### Phase 5（Week 5-8）

**優先度: 中**

- タイプB: ルール妥当性バックテスト
- 仮想トレードシミュレーション
- 詳細統計分析

### Phase 6以降

**優先度: 低**

- タイプC: システム全体バックテスト
- プロンプト自動最適化

---

**以上、バックテスト仕様書**
