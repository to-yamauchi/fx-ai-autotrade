# モニタリングシステム テストガイド

3層モニタリングシステムのテスト方法を説明します。

## 📋 目次

1. [事前準備](#事前準備)
2. [テスト方法1: モニター起動テスト](#テスト方法1-モニター起動テスト)
3. [テスト方法2: 既存ポジション監視テスト](#テスト方法2-既存ポジション監視テスト)
4. [テスト方法3: 実トレードフローテスト](#テスト方法3-実トレードフローテスト)
5. [確認項目](#確認項目)
6. [トラブルシューティング](#トラブルシューティング)

---

## 事前準備

### 1. 環境変数の確認

`.env` ファイルに以下が設定されていることを確認：

```env
# MT5 接続情報
MT5_LOGIN=あなたのログイン番号
MT5_PASSWORD=あなたのパスワード
MT5_SERVER=あなたのサーバー名

# トレードモード
TRADE_MODE=demo

# Gemini API
GEMINI_API_KEY=あなたのAPIキー
```

### 2. MT5の起動

MetaTrader 5を起動し、ログインしておく。

### 3. データベース接続確認

PostgreSQLが起動していることを確認。

---

## テスト方法1: モニター起動テスト

**目的**: モニターの起動・停止が正常に動作するか確認

**実行方法**:
```bash
python test_monitor_startup.py
```

**確認項目**:
- ✅ 全モニターが正常に起動する
- ✅ スレッドが正常に動作する（thread_alive=True）
- ✅ ステータスが正常に取得できる
- ✅ 正常に停止できる

**期待される出力**:
```
TEST 1: オーケストレーター起動テスト
[成功] モニター起動完了
Layer 1 Running: True
Layer 1 Thread: True
Layer 2 Running: True
Layer 2 Thread: True
Layer 3 Running: True
Layer 3 Thread: True
[合格] 全モニターが正常に起動・動作しました

TEST 2: 個別Layer起動テスト
Layer 1: [成功]
Layer 2: [成功]
Layer 3: [成功]
[合格] 全Layerが個別に正常動作しました

TEST 3: ポジション登録テスト
[成功] ポジション登録完了
[合格] ポジション登録が正常に動作しました

[総合結果] 全テスト合格 ✅
```

---

## テスト方法2: 既存ポジション監視テスト

**目的**: 既にオープンしているポジションを監視できるか確認

**前提条件**: USDJPY のオープンポジションが存在すること

**実行方法**:
```bash
# まずポジションをオープン（なければ）
python main.py

# 別のターミナルで監視テストを実行
python test_monitoring.py
```

**確認項目**:
- ✅ 既存ポジションを検出できる
- ✅ Layer 1が100ms間隔で監視している（ログで確認）
- ✅ Layer 2が5分間隔で監視している
- ✅ Layer 3が30分間隔で監視している
- ✅ 1分ごとにステータスが表示される
- ✅ Ctrl+C で安全に停止できる

**期待される出力**:
```
既存のオープンポジションを確認中 (USDJPY)...
オープンポジション: 1件
  ticket=8235340, type=BUY, volume=1.55, open=152.408, current=152.425, profit=170.00

モニタリング開始
以下を監視中：
  - Layer 1: 緊急停止（100ms間隔、50pips SL、口座2%損失）
  - Layer 2: 異常検知（5分間隔、DD10%、逆行8pips、スプレッド5pips）
  - Layer 3: AI再評価（30分間隔、判断反転、信頼度60%）

[Layer 1] Monitoring position 8235340...
[Layer 2] Checking position 8235340...
[Layer 3] Re-evaluating position 8235340...
```

**監視動作の確認**:

1. **Layer 1 (100ms)**:
   - ログファイル `logs/` を確認
   - `Monitoring position` が頻繁に出力される

2. **Layer 2 (5分)**:
   - 5分ごとに `Checking position` が出力
   - ドローダウン・逆行・スプレッドをチェック

3. **Layer 3 (30分)**:
   - 30分ごとに `Re-evaluating position` が出力
   - AI分析を再実行して判断反転を検知

---

## テスト方法3: 実トレードフローテスト

**目的**: トレード実行から監視開始までの一連の流れを確認

**実行方法**:
```bash
python main.py
```

**確認項目**:
- ✅ AI分析が実行される
- ✅ トレードが実行される
- ✅ トレード成功後、モニタリングが自動起動する
- ✅ ポジションがモニターに登録される
- ✅ 3層すべてが監視を開始する
- ✅ 1分ごとにステータスが表示される

**期待される出力**:
```
DEMOモード開始
3層モニタリングシステムを初期化中...

AI判断: BUY
信頼度: 85%

トレード成功！モニタリングシステムを起動します...

[Layer 1] Starting Emergency Monitor...
  - Interval: 100ms
  - Hard SL: 50 pips
  - Max Loss: 2%

[Layer 2] Starting Anomaly Monitor...
  - Interval: 5 min
  - Drawdown: 10%
  - Reversal: 8 pips
  - Spread: 5 pips

[Layer 3] Starting AI Review Monitor...
  - Interval: 30 min
  - Min Confidence: 60%
  - AI Model: flash

All monitoring layers started successfully

モニタリングシステムが起動しました。
Ctrl+Cで終了します...
```

---

## 確認項目

### Layer 1 (緊急停止)

**正常動作の確認**:
```
# ログで以下を確認
[Layer 1] Monitoring position 12345...
[Layer 1] Position 12345 SL check: 25.3 pips from entry (OK)
```

**アラート発生のテスト**:
- 意図的に50pips以上逆行するまで待つ（または手動で逆ポジションを取る）
- 以下のログが出力されるか確認：
```
[LAYER 1 ALERT] Hard stop loss triggered!
[EMERGENCY] Closing position 12345: Hard SL exceeded (52.3 pips)
```

### Layer 2 (異常検知)

**正常動作の確認**:
```
# 5分ごとに以下を確認
[Layer 2] Checking position 12345...
[Layer 2] Position 12345 drawdown: 3.2% (OK)
```

**アラート発生のテスト**:
- ポジションが含み益から10%以上ドローダウン
- 以下のログが出力されるか確認：
```
[LAYER 2 ALERT] Drawdown detected!
ticket=12345, max_profit=5000, current_profit=4400, drawdown=12%
```

### Layer 3 (AI再評価)

**正常動作の確認**:
```
# 30分ごとに以下を確認
[Layer 3] Re-evaluating position 12345...
Position 12345: AI says BUY (confidence: 82%)
```

**判断反転のテスト**:
- 30分後にAI判断が逆になる（BUY→SELL）
- 以下のログが出力され、自動決済されるか確認：
```
[LAYER 3 ALERT] Judgment reversal detected!
ticket=12345, entry=BUY, current=SELL, confidence=75%
[AUTO CLOSE] Closing position 12345: AI judgment reversal: BUY -> SELL
[SUCCESS] Position 12345 closed successfully
```

---

## トラブルシューティング

### 問題: モニターが起動しない

**確認事項**:
1. MT5が起動してログインしているか
2. `.env` ファイルの設定が正しいか
3. ログファイルでエラーを確認

**解決方法**:
```bash
# MT5の再起動
# .env ファイルの確認
cat .env

# ログの確認
ls -la logs/
```

### 問題: スレッドが動作していない (thread_alive=False)

**原因**:
- スレッド内でエラーが発生している
- MT5接続が切れている

**解決方法**:
```python
# ログレベルをDEBUGに変更
logging.basicConfig(level=logging.DEBUG)
```

### 問題: Layer 3 がAI分析を実行しない

**原因**:
- Gemini API キーが無効
- APIクォータ超過

**解決方法**:
```bash
# .env の GEMINI_API_KEY を確認
echo $GEMINI_API_KEY

# APIキーをテスト
python -c "from src.ai_analysis.ai_analyzer import AIAnalyzer; a = AIAnalyzer(); print(a.analyze_market())"
```

### 問題: アラートが大量に発生する

**原因**:
- クールダウン時間が短い
- 条件が頻繁にトリガーされている

**解決方法**:
```python
# クールダウン時間を調整（各モニターファイル内）
ALERT_COOLDOWN_MINUTES = 60  # 60分に延長
```

---

## パフォーマンス確認

### CPU使用率

```bash
# プロセスのCPU使用率を確認
top -p $(pgrep -f "python main.py")
```

**期待値**: 5-10% 程度

### メモリ使用量

```bash
# メモリ使用量を確認
ps aux | grep "python main.py"
```

**期待値**: 100-200MB 程度

### ログファイルサイズ

```bash
# ログファイルのサイズを確認
ls -lh logs/
```

**注意**: Layer 1 が100msで動作するため、ログが急速に増える可能性あり

**対策**: ログレベルを WARNING 以上に設定
```python
logging.basicConfig(level=logging.WARNING)
```

---

## 本番環境での注意事項

### 1. ログレベルの調整

本番環境では WARNING 以上を推奨：
```python
# main.py
logging.basicConfig(level=logging.WARNING)
```

### 2. アラート通知の実装

現在はログのみですが、本番では以下を実装推奨：
- メール通知 (SMTP)
- SMS通知 (Twilio)
- Slack/Discord通知

実装場所: `src/monitoring/layer*_*.py` の `_send_alert()` メソッド

### 3. バックグラウンド実行

長時間実行する場合は `nohup` または `screen` を使用：
```bash
# nohup で実行
nohup python main.py > output.log 2>&1 &

# または screen で実行
screen -S fx_monitor
python main.py
# Ctrl+A → D でデタッチ
```

---

## まとめ

**推奨テスト順序**:
1. ✅ `python test_monitor_startup.py` - 起動テスト
2. ✅ `python main.py` - 実トレードフロー
3. ✅ `python test_monitoring.py` - 既存ポジション監視（別ターミナル）

**すべてのテストが成功すれば、モニタリングシステムは正常に動作しています！** 🎉
