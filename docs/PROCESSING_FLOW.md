# FX自動トレードシステム - 処理フロー詳細

## 📊 システム全体の構造

```
┌─────────────────────────────────────────────────────────────┐
│                    1日の処理サイクル                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  06:00  Phase 1: デイリーレビュー (Gemini Pro)                │
│         └→ 前日のトレード結果を振り返り                        │
│                                                               │
│  08:00  Phase 2: 朝の詳細分析 (Gemini Pro) ⭐ 新規実装       │
│         └→ 本日の戦略を生成                                   │
│                                                               │
│  12:00  Phase 3: 定期更新① (Gemini Flash)                    │
│         └→ 戦略の妥当性確認・更新                             │
│                                                               │
│  16:00  Phase 3: 定期更新② (Gemini Flash)                    │
│         └→ 戦略の妥当性確認・更新                             │
│                                                               │
│  21:30  Phase 3: 定期更新③ (Gemini Flash)                    │
│         └→ 戦略の妥当性確認・更新                             │
│                                                               │
│  00:00  Phase 4: Layer 3a監視 (Gemini Flash-8B)              │
│  ~24:00 └→ 15分ごとにポジション監視（ポジション保有時のみ）    │
│                                                               │
│  随時    Phase 5: Layer 3b緊急評価 (Gemini Pro)               │
│         └→ 異常検知時に緊急対応（ポジション保有時のみ）        │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## 🔄 処理フローの詳細

### Phase 1: デイリーレビュー（06:00）

**実行タイミング**: 毎日06:00（初日を除く）
**使用モデル**: Gemini 2.5 Pro
**処理時間**: 約5-10秒

```
1. 前日のトレード結果を取得
   └→ データベースから positions テーブルを検索

2. AIAnalyzer.daily_review() 呼び出し
   ├→ プロンプト: prompts/daily_review.txt
   ├→ 入力データ:
   │  ├─ previous_day_trades: 前日の全トレード
   │  ├─ prediction: 前日の予測内容
   │  ├─ actual_market: 実際の市場動向
   │  └─ statistics: 統計情報
   │
   └→ Gemini Pro API呼び出し (温度: 0.3)

3. レビュー結果の生成
   ├→ score: 総合評価（/100点）
   ├→ analysis: 何がうまくいったか/失敗したか
   ├→ lessons_for_today: 本日への教訓（配列）
   └→ pattern_recognition: 成功/失敗パターン

4. データベースに保存
   └→ backtest_daily_reviews / demo_daily_reviews / daily_reviews
```

**実装場所**:
- `backtest_engine.py:210-220` - Phase 1エントリーポイント
- `backtest_engine.py:593-624` - `_run_daily_review()` メソッド
- `ai_analyzer.py:514-612` - `daily_review()` メソッド

---

### Phase 2: 朝の詳細分析（08:00）⭐ 新規実装

**実行タイミング**: 毎日08:00
**使用モデル**: Gemini 2.5 Pro
**処理時間**: 約10-15秒

```
1. 市場データの準備
   ├→ ティックデータ読み込み（過去60日分）
   ├→ 時間足変換（D1/H4/H1/M15）
   ├→ テクニカル指標計算
   │  ├─ EMA（短期20/長期50）
   │  ├─ RSI（14）
   │  ├─ MACD（12/26/9）
   │  ├─ ATR（14）
   │  ├─ ボリンジャーバンド（20/2σ）
   │  └─ サポート&レジスタンス
   │
   └→ データ標準化（JSON形式）

2. 過去統計の計算
   └→ 過去5日のトレード成績を集計

3. AIAnalyzer.morning_analysis() 呼び出し
   ├→ プロンプト: prompts/morning_analysis.txt
   ├→ 入力データ:
   │  ├─ market_data: 標準化済み市場データ
   │  ├─ review_result: Phase 1の振り返り結果
   │  └─ past_statistics: 過去5日の統計
   │
   └→ Gemini Pro API呼び出し (温度: 0.3)

4. 戦略結果の生成
   ├→ daily_bias: BUY/SELL/NEUTRAL
   ├→ confidence: 0.0-1.0（信頼度）
   ├→ reasoning: 判断理由（テキスト）
   ├→ market_environment: {trend, strength, phase}
   ├→ entry_conditions:
   │  ├─ should_trade: true/false
   │  ├─ direction: BUY/SELL
   │  ├─ price_zone: {min, max}
   │  ├─ required_signals: [シグナル配列]
   │  └─ avoid_if: [回避条件配列]
   ├→ exit_strategy:
   │  ├─ take_profit: [{pips, close_percent, reason}, ...]
   │  ├─ stop_loss: {initial, ...}
   │  ├─ indicator_exits: [条件配列]
   │  └─ time_exits: {条件}
   ├→ risk_management:
   │  ├─ position_size_multiplier: 倍率
   │  ├─ max_positions: 最大ポジション数
   │  └─ reason: 理由
   ├→ key_levels:
   │  ├─ entry_target: エントリー目標価格
   │  ├─ invalidation_level: 無効化レベル
   │  ├─ critical_support: 重要サポート
   │  └─ critical_resistance: 重要レジスタンス
   ├→ scenario_planning:
   │  ├─ bullish_scenario: 強気シナリオ
   │  ├─ bearish_scenario: 弱気シナリオ
   │  └─ base_case: ベースケース
   └→ lessons_applied: [適用された教訓配列]

5. データベースに保存
   └→ backtest_daily_strategies / demo_daily_strategies / daily_strategies

6. トレード実行判断
   ├→ entry_conditions.should_trade == true の場合
   └→ _execute_trade_from_strategy() 呼び出し
```

**実装場所**:
- `backtest_engine.py:223-238` - Phase 2エントリーポイント
- `backtest_engine.py:626-693` - `_run_morning_analysis()` メソッド
- `ai_analyzer.py:664-798` - `morning_analysis()` メソッド
- `ai_analyzer.py:800-889` - `_save_morning_analysis_to_database()` メソッド

**データベース保存内容**:
```sql
INSERT INTO backtest_daily_strategies (
    strategy_date,              -- 戦略日付
    symbol,                     -- 通貨ペア
    daily_bias,                 -- BUY/SELL/NEUTRAL
    confidence,                 -- 0.0-1.0
    reasoning,                  -- 判断理由
    market_environment,         -- JSONB
    entry_conditions,           -- JSONB
    exit_strategy,              -- JSONB
    risk_management,            -- JSONB
    key_levels,                 -- JSONB
    scenario_planning,          -- JSONB
    lessons_applied,            -- JSONB
    market_data,                -- JSONB（市場データスナップショット）
    backtest_start_date,        -- バックテスト開始日
    backtest_end_date,          -- バックテスト終了日
    created_at                  -- 作成日時
) VALUES (...);
```

---

### Phase 3: 定期更新（12:00/16:00/21:30）

**実行タイミング**: 12:00、16:00、21:30
**使用モデル**: Gemini 2.5 Flash（コスト削減）
**処理時間**: 約2-5秒

```
1. 現在の市場データ取得
   └→ 最新のティックデータから時間足を再計算

2. 本日のトレード実績取得
   └→ データベースから本日分のポジションを検索

3. AIAnalyzer.periodic_update() 呼び出し
   ├→ プロンプト: prompts/periodic_update.txt
   ├→ 入力データ:
   │  ├─ morning_strategy: Phase 2で生成した戦略
   │  ├─ current_market_data: 現在の市場データ
   │  ├─ today_trades: 本日のトレード実績
   │  ├─ current_positions: 現在のポジション
   │  └─ update_time: "12:00" / "16:00" / "21:30"
   │
   └→ Gemini Flash API呼び出し (温度: 0.3)

4. 更新結果の生成
   ├→ update_type: no_change / bias_change / risk_adjustment / ...
   ├→ market_assessment: 市場評価の変化
   ├→ strategy_validity: 朝の戦略の妥当性
   ├→ recommended_changes: 推奨変更
   ├→ current_positions_action: 既存ポジションへの対応
   └→ new_entry_recommendation: 新規エントリー推奨

5. データベースに保存
   └→ backtest_periodic_updates / demo_periodic_updates / periodic_updates

6. 戦略の更新
   └→ 必要に応じて morning_strategy を上書き
```

**実装場所**:
- `backtest_engine.py:240-259` - Phase 3エントリーポイント
- `ai_analyzer.py:891-1015` - `periodic_update()` メソッド

---

### Phase 4: Layer 3a監視（15分ごと）

**実行タイミング**: ポジション保有時、15分ごと
**使用モデル**: Gemini 2.5 Flash-8B（超軽量）
**処理時間**: 約1秒以下

```
1. ポジション保有確認
   ├→ open_positions が空の場合はスキップ
   └→ 前回監視から15分経過をチェック

2. 各ポジションに対して監視実行
   └→ AIAnalyzer.layer3a_monitor() 呼び出し
      ├→ プロンプト: prompts/layer3a_monitoring.txt
      ├→ 入力データ:
      │  ├─ position: ポジション情報
      │  ├─ current_market_data: 簡易市場データ
      │  └─ daily_strategy: 本日の戦略
      │
      └→ Gemini Flash-8B API呼び出し (温度: 0.2)

3. 監視結果の生成
   ├→ action: HOLD / CLOSE_NOW / ADJUST_SL / PARTIAL_CLOSE
   ├→ urgency: normal / high
   ├→ reason: 判断理由
   ├→ details: {profit_status, risk_level, signals}
   └→ recommended_action: 推奨アクション

4. アクション実行
   ├→ CLOSE_NOW: 即座にポジションクローズ
   ├→ ADJUST_SL: ストップロス調整
   ├→ PARTIAL_CLOSE: 部分決済
   └→ HOLD: 保持継続

5. データベースに保存（バックテストモードのみ）
   └→ backtest_layer3a_monitoring
```

**実装場所**:
- `backtest_engine.py:280-288` - Layer 3a監視トリガー
- `ai_analyzer.py:1110-1205` - `layer3a_monitor()` メソッド

---

### Phase 5: Layer 3b緊急評価（異常検知時）

**実行タイミング**: 異常検知時のみ（ポジション保有時のみ）
**使用モデル**: Gemini 2.5 Pro（高精度判断）
**処理時間**: 約5-10秒

**⚠️ 重要**: ポジションがない場合は、異常が検知されても評価をスキップします（リスクがないためAI評価不要）

```
1. 異常検知
   ├→ 急激な価格変動（1分で±0.5%以上）
   ├→ スプレッド異常拡大（平均の3倍以上）
   ├→ ボラティリティ急増（ATRの2倍以上）
   └→ 含み損急拡大（-3%以上）

2. ポジション保有確認
   ├→ open_positions が空の場合はスキップ
   └→ ポジションがあれば緊急評価を実行

3. 異常検知時の評価実行
   └→ AIAnalyzer.layer3b_emergency() 呼び出し
      ├→ プロンプト: prompts/layer3b_emergency.txt
      ├→ 入力データ:
      │  ├─ anomaly_info: 異常検知情報
      │  ├─ current_positions: 全ポジション
      │  ├─ current_market_data: 現在の市場データ
      │  └─ daily_strategy: 本日の戦略
      │
      └→ Gemini Pro API呼び出し (温度: 0.2)

4. 緊急評価結果の生成
   ├→ severity: low / medium / high / critical
   ├→ action: CONTINUE / CLOSE_ALL / CLOSE_PARTIAL / REVERSE
   ├→ reasoning: 判断理由
   ├→ immediate_actions: [即座に取るべき行動配列]
   └→ risk_assessment: リスク評価

5. 緊急アクション実行
   ├→ CLOSE_ALL: 全ポジションクローズ
   ├→ CLOSE_PARTIAL: リスク高ポジションのみクローズ
   ├→ REVERSE: ポジション反転
   └→ CONTINUE: 継続（軽微な異常）

6. データベースに保存
   └→ backtest_layer3b_emergency / demo_layer3b_emergency / layer3b_emergency
```

**実装場所**:
- `backtest_engine.py:291-302` - Layer 3b緊急評価トリガー
- `ai_analyzer.py:1294-1391` - `layer3b_emergency()` メソッド

---

## 📦 データの流れ

```
ティックデータ（CSVファイル）
    ↓
[TickDataLoader]
    ↓
時間足変換（D1/H4/H1/M15）
    ↓
[TimeframeConverter]
    ↓
テクニカル指標計算
    ↓
[TechnicalIndicators]
    ↓
データ標準化（JSON）
    ↓
[DataStandardizer]
    ↓
AI分析（各Phase）
    ↓
[GeminiClient]
    ↓
判断結果（JSON）
    ↓
[AIAnalyzer]
    ↓
データベース保存 + トレード実行
    ↓
[PostgreSQL] + [TradingSimulator]
```

## 🗄️ データベーステーブル構造

### モード別テーブル

すべてのテーブルは3つのモードで分離されています:

| モード | テーブル接頭辞 | 説明 |
|--------|--------------|------|
| BACKTEST | `backtest_*` | バックテスト用（過去データ） |
| DEMO | `demo_*` | DEMO口座用（リアルタイム） |
| LIVE | なし | 本番口座用（リアルタイム） |

### Phase別データベーステーブル

| Phase | テーブル名 | 保存内容 |
|-------|-----------|---------|
| Phase 1 | `*_daily_reviews` | デイリーレビュー結果 |
| Phase 2 | `*_daily_strategies` | 朝の詳細戦略 ⭐ 新規 |
| Phase 3 | `*_periodic_updates` | 定期更新結果 |
| Phase 4 | `*_layer3a_monitoring` | Layer 3a監視ログ |
| Phase 5 | `*_layer3b_emergency` | Layer 3b緊急対応ログ |
| 共通 | `*_positions` | ポジション履歴 |
| 共通 | `*_ai_judgments` | AI判断履歴（旧） |

## 🔁 バックテスト実行の流れ

```
1. 初期化
   ├→ TradingSimulator作成（初期残高: 100万円）
   ├→ AIAnalyzer作成（Geminiクライアント初期化）
   └→ ティックデータ読み込み

2. 日次ループ（開始日〜終了日）
   │
   ├─【06:00】Phase 1: デイリーレビュー
   │   └→ 前日のトレード結果を分析
   │
   ├─【08:00】Phase 2: 朝の詳細分析 ⭐
   │   ├→ 市場データ準備
   │   ├→ 戦略生成
   │   └→ エントリー判断・実行
   │
   ├─【12:00】Phase 3: 定期更新①
   │   └→ 戦略の妥当性確認
   │
   ├─【16:00】Phase 3: 定期更新②
   │   └→ 戦略の妥当性確認
   │
   ├─【21:30】Phase 3: 定期更新③
   │   └→ 戦略の妥当性確認
   │
   ├─【00:00-24:00】Phase 4 & 5: リアルタイム監視
   │   ├→ ティックごとに市場価格更新
   │   ├→ 15分ごとにLayer 3a監視
   │   └→ 異常検知時にLayer 3b緊急評価
   │
   └─【日次終了】残高・ポジション表示

3. 終了処理
   ├→ 全ポジションクローズ
   ├→ 統計計算
   ├→ 結果表示
   └→ データベース保存
```

## ⚙️ モード別の動作

### バックテストモード (TRADE_MODE=backtest)

```
データソース: data/tick_data/ (CSVファイル)
MT5接続: 不要
テーブル: backtest_*
実行速度: 高速（リアルタイム待機なし）
用途: 戦略検証、過去データ分析
```

### DEMOモード (TRADE_MODE=demo)

```
データソース: MT5（リアルタイム取得）
MT5接続: 必要（DEMO口座）
テーブル: demo_*
実行速度: リアルタイム
用途: DEMO口座での実運用テスト
```

### 本番モード (TRADE_MODE=live)

```
データソース: MT5（リアルタイム取得）
MT5接続: 必要（本番口座）
テーブル: 接頭辞なし
実行速度: リアルタイム
用途: 本番運用
```

## 🎯 Phase 2統合のポイント

### 従来（Phase 1のみ）
```
06:00 デイリーレビュー
  ↓
トレード実行（単純なルールベース）
```

### 現在（Phase 2統合後）⭐
```
06:00 デイリーレビュー
  ↓（教訓を抽出）
08:00 朝の詳細分析 ← Gemini Proで高精度戦略生成
  ↓
  ├─ 市場環境の詳細分析
  ├─ エントリー条件の明確化
  ├─ 決済戦略の計画
  ├─ リスク管理の最適化
  ├─ 重要価格レベルの特定
  └─ シナリオプランニング
  ↓
トレード実行（AIの詳細戦略に基づく）
  ↓
12:00/16:00/21:30 定期更新で戦略を調整
```

## 💡 重要な設計原則

1. **段階的な判断**
   - Phase 1で学習 → Phase 2で計画 → Phase 3で調整 → Phase 4/5で監視

2. **コスト最適化**
   - Phase 1, 2: Gemini Pro（高精度・低頻度）
   - Phase 3: Gemini Flash（中精度・中頻度）
   - Phase 4: Gemini Flash-8B（軽量・高頻度）
   - Phase 5: Gemini Pro（高精度・緊急時のみ）

3. **データの再利用**
   - 朝の戦略（Phase 2）を定期更新（Phase 3）で参照
   - 定期更新結果を監視（Phase 4）で参照
   - すべてデータベースに保存して追跡可能

4. **エラーハンドリング**
   - API失敗時は保守的な判断（NEUTRAL, should_trade=false）
   - 緊急時（Phase 5）はデフォルトで全決済を推奨

## 📝 まとめ

現在のシステムは**5つのPhase**で構成されており、Phase 2（朝の詳細分析）が新たに追加されました。

Phase 2により、単純なルールベースのトレードから、**AIによる高度な戦略生成**へと進化しています。朝の段階で詳細な分析を行い、エントリー条件、決済戦略、リスク管理を明確化することで、より精度の高いトレードが可能になります。

次のステップは、Phase 2を実際にテストして、生成される戦略の品質を確認することです！
