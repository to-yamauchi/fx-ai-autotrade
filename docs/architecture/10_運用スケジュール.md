# 運用スケジュール仕様書

## ドキュメント情報
- **作成日**: 2025-10-21
- **バージョン**: 1.0
- **カテゴリ**: システムアーキテクチャ - 運用管理

---

## 1. 概要

### 1.1 目的

システムの定期的な処理スケジュールと週末停止機能の管理

### 1.2 設計原則

- **自動化**: 全処理を自動実行
- **週末停止**: 土日の完全停止
- **時刻厳守**: 定刻処理の確実な実行

---

## 2. 週末停止機能

### 2.1 停止条件

**土日の処理**:
- 新規エントリー: 完全停止
- Layer 1: 稼働継続（万が一のポジション監視）
- その他の処理: 全停止

**金曜日23:00**:
- 全ポジション強制決済
- 日次クローズ

**月曜日07:00**:
- 全機能自動復帰

### 2.2 実装

```python
def is_trading_day():
    """取引可能日か判定"""
    now = datetime.now()
    day_of_week = now.weekday()

    # 土日は取引停止
    if day_of_week >= 5:  # 5=土曜, 6=日曜
        return False

    # 月曜07:00以降のみ
    if day_of_week == 0 and now.hour < 7:
        return False

    return True

def check_weekend_shutdown():
    """週末停止チェック"""
    now = datetime.now()

    # 金曜23:00
    if now.weekday() == 4 and now.hour >= 23:
        shutdown_for_weekend()

    # 土日
    if not is_trading_day():
        ensure_weekend_mode()

def shutdown_for_weekend():
    """週末停止処理"""
    logger.info("Weekend shutdown initiated")

    # 1. 全ポジション強制決済
    close_all_positions("Weekend close")

    # 2. エントリーシステム停止
    disable_entry_system()

    # 3. Layer 2/3停止
    stop_layer2_monitoring()
    stop_layer3_monitoring()

    # 4. Layer 1のみ稼働継続
    ensure_layer1_running()

    # 5. 記録
    log_weekend_shutdown()

    logger.info("Weekend mode: Entry disabled, Layer 1 only")

def resume_from_weekend():
    """月曜朝の復帰処理"""
    now = datetime.now()

    # 月曜07:00チェック
    if now.weekday() == 0 and now.hour >= 7:
        logger.info("Resuming from weekend")

        # 1. 全システム再起動
        restart_all_systems()

        # 2. データ取得確認
        verify_data_connection()

        # 3. 記録
        log_system_resume()

        logger.info("System resumed from weekend")
```

---

## 3. 平日スケジュール

### 3.1 スケジュール一覧

| 時刻 | 処理 | モデル | 1回コスト | 目的 |
|------|------|--------|---------|------|
| 06:00 | 前日振り返り | Gemini 2.5 Pro | $0.018 | 教訓抽出 |
| 08:00 | 朝の詳細分析 | Gemini 2.5 Pro | $0.024 | 市場分析、戦略生成 |
| 12:00 | 定期更新（昼） | Gemini 2.5 Flash | $0.002 | 午前の総括 |
| 16:00 | 定期更新（夕方） | Gemini 2.5 Flash | $0.002 | 欧州前チェック |
| 21:30 | 定期更新（夜） | Gemini 2.5 Flash | $0.002 | NY前チェック |
| 23:00 | 強制決済 | - | - | 日次クローズ |

**1日の戦略生成コスト合計**: $0.048

### 3.2 継続監視

| 監視種類 | 頻度 | 使用技術 | コスト | 目的 |
|---------|------|---------|--------|------|
| Layer 1緊急停止 | 100ms | ルールベース | $0 | 致命的損失防止 |
| エントリー監視 | 1分 | ルールベース | $0 | 条件達成チェック |
| Layer 2異常検知 | 1分/5分 | ルールベース | $0 | 環境変化検知 |
| 決済監視 | 1分 | ルールベース | $0 | 利確・損切・時間管理 |
| Layer 3a定期評価 | 15分 | Flash-Lite（従量） | 超低 | ポジション簡易チェック |
| Layer 3b緊急評価 | トリガー時 | Pro（従量） | 中 | 異常時詳細分析 |

---

## 4. 詳細スケジュール

### 4.1 06:00 - 前日振り返り

#### 4.1.1 処理内容

```python
def schedule_daily_review():
    """毎日06:00に実行"""

    logger.info("Starting daily review at 06:00")

    # 1. 前日のトレード記録取得
    yesterday_trades = get_yesterday_trades()

    if not yesterday_trades:
        logger.info("No trades yesterday, skipping review")
        return

    # 2. 前日のAI予測取得
    yesterday_prediction = get_yesterday_morning_prediction()

    # 3. 実際の市場動向取得
    yesterday_market = get_yesterday_market_result()

    # 4. AI振り返り実行
    review = call_gemini_pro_review(
        trades=yesterday_trades,
        prediction=yesterday_prediction,
        market=yesterday_market
    )

    # 5. 結果保存
    save_daily_review(review)

    logger.info(f"Daily review completed: Score {review['score']['total']}/100")
```

#### 4.1.2 スケジューラ設定

```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

scheduler.add_job(
    func=schedule_daily_review,
    trigger='cron',
    hour=6,
    minute=0,
    id='daily_review',
    name='Daily Review at 06:00'
)
```

### 4.2 08:00 - 朝の詳細分析

#### 4.2.1 処理内容

```python
def schedule_morning_analysis():
    """毎日08:00に実行"""

    logger.info("Starting morning analysis at 08:00")

    # 1. 市場データ取得
    market_data = get_current_market_data()

    # 2. データ標準化
    standardized_data = standardize_market_data(market_data)

    # 3. 前日の振り返り取得
    yesterday_review = get_latest_review()

    # 4. 過去5日の統計
    recent_stats = get_recent_stats(days=5)

    # 5. AI分析実行
    analysis = call_gemini_pro_morning_analysis(
        market_data=standardized_data,
        yesterday_review=yesterday_review,
        recent_stats=recent_stats
    )

    # 6. ルールJSON生成
    rule_json = analysis

    # 7. ルール保存・有効化
    rule_version = save_and_activate_rule(rule_json)

    logger.info(f"Morning analysis completed: {rule_json['daily_bias']}, confidence {rule_json['confidence']}")

    # 8. エントリーシステム有効化
    enable_entry_monitoring()
```

#### 4.2.2 スケジューラ設定

```python
scheduler.add_job(
    func=schedule_morning_analysis,
    trigger='cron',
    hour=8,
    minute=0,
    id='morning_analysis',
    name='Morning Analysis at 08:00'
)
```

### 4.3 12:00 / 16:00 / 21:30 - 定期更新

#### 4.3.1 処理内容

```python
def schedule_periodic_update(update_time):
    """定期更新（12:00, 16:00, 21:30）"""

    logger.info(f"Starting periodic update at {update_time}")

    # 1. 現在のルール取得
    current_rule = get_current_rule()

    # 2. 更新時刻までの市場動向
    market_since_morning = get_market_data_since_morning()

    # 3. 現在の市場状況
    current_market = get_current_market_data()

    # 4. AI更新評価
    update_result = call_gemini_flash_periodic_update(
        current_rule=current_rule,
        market_since_morning=market_since_morning,
        current_market=current_market
    )

    # 5. 修正が必要な場合
    if update_result['action'] == '修正':
        update_rule(update_result['rule_updates'])
        logger.info("Rule updated based on periodic update")
    else:
        logger.info("Rule remains valid, no update needed")

    # 6. 結果保存
    save_periodic_update(update_time, update_result)
```

#### 4.3.2 スケジューラ設定

```python
scheduler.add_job(
    func=lambda: schedule_periodic_update("12:00"),
    trigger='cron',
    hour=12,
    minute=0,
    id='update_noon',
    name='Periodic Update at 12:00'
)

scheduler.add_job(
    func=lambda: schedule_periodic_update("16:00"),
    trigger='cron',
    hour=16,
    minute=0,
    id='update_afternoon',
    name='Periodic Update at 16:00'
)

scheduler.add_job(
    func=lambda: schedule_periodic_update("21:30"),
    trigger='cron',
    hour=21,
    minute=30,
    id='update_night',
    name='Periodic Update at 21:30'
)
```

### 4.4 23:00 - 強制決済

#### 4.4.1 処理内容

```python
def schedule_daily_close():
    """毎日23:00に実行"""

    logger.info("Starting daily close at 23:00")

    # 1. 全ポジション決済
    positions = mt5.positions_get()

    if positions:
        for position in positions:
            close_position(position, reason="Force close: 23:00")
        logger.info(f"Closed {len(positions)} positions for daily close")
    else:
        logger.info("No positions to close")

    # 2. エントリー監視停止（翌朝まで）
    disable_entry_monitoring()

    # 3. 日次統計計算
    daily_stats = calculate_daily_stats()

    # 4. パフォーマンス記録
    save_daily_performance(daily_stats)

    logger.info(f"Daily close completed: {daily_stats['total_trades']} trades, {daily_stats['total_pips']} pips")
```

#### 4.4.2 スケジューラ設定

```python
scheduler.add_job(
    func=schedule_daily_close,
    trigger='cron',
    hour=23,
    minute=0,
    id='daily_close',
    name='Daily Close at 23:00'
)
```

---

## 5. バッチ処理

### 5.1 日次バッチ

#### 5.1.1 04:00 - データベースバックアップ

```python
def schedule_database_backup():
    """毎日04:00に実行"""

    logger.info("Starting database backup")

    # バックアップ実行
    result = subprocess.run([
        '/bin/bash',
        '/scripts/daily_backup.sh'
    ], capture_output=True)

    if result.returncode == 0:
        logger.info("Database backup completed successfully")
    else:
        logger.error(f"Database backup failed: {result.stderr}")
        send_alert("Database backup failed")

scheduler.add_job(
    func=schedule_database_backup,
    trigger='cron',
    hour=4,
    minute=0,
    id='db_backup',
    name='Database Backup at 04:00'
)
```

#### 5.1.2 05:00 - ログローテーション

```python
def schedule_log_rotation():
    """毎日05:00に実行"""

    logger.info("Starting log rotation")

    # 古いログの圧縮・削除
    rotate_logs(
        log_dir='/var/log/fx_autotrade',
        keep_days=30,
        compress=True
    )

    logger.info("Log rotation completed")

scheduler.add_job(
    func=schedule_log_rotation,
    trigger='cron',
    hour=5,
    minute=0,
    id='log_rotation',
    name='Log Rotation at 05:00'
)
```

### 5.2 週次バッチ

#### 5.2.1 金曜23:30 - 週次レビュー

```python
def schedule_weekly_review():
    """毎週金曜23:30に実行"""

    logger.info("Starting weekly review")

    # 週次レビュー実行
    report = weekly_review()

    # レポート保存
    save_weekly_report(report)

    # アラート送信（オプション）
    if report['win_rate'] < 0.50:
        send_alert(f"週次勝率警告: {report['win_rate']*100:.1f}%")

    logger.info(f"Weekly review completed: Win rate {report['win_rate']*100:.1f}%")

scheduler.add_job(
    func=schedule_weekly_review,
    trigger='cron',
    day_of_week='fri',
    hour=23,
    minute=30,
    id='weekly_review',
    name='Weekly Review (Friday 23:30)'
)
```

### 5.3 月次バッチ

#### 5.3.1 月末 - 月次レビュー

```python
def schedule_monthly_review():
    """毎月末に実行"""

    logger.info("Starting monthly review")

    # 月次レビュー実行
    report = monthly_review()

    # レポート保存
    save_monthly_report(report)

    logger.info(f"Monthly review completed: Return {report['month_return']*100:.2f}%")

scheduler.add_job(
    func=schedule_monthly_review,
    trigger='cron',
    day='last',
    hour=23,
    minute=45,
    id='monthly_review',
    name='Monthly Review (Last day of month)'
)
```

---

## 6. スケジューラ管理

### 6.1 スケジューラ起動

```python
def start_scheduler():
    """スケジューラ起動"""

    logger.info("Starting scheduler")

    # スケジューラ開始
    scheduler.start()

    # 稼働確認
    jobs = scheduler.get_jobs()
    logger.info(f"Scheduler started with {len(jobs)} jobs")

    for job in jobs:
        logger.info(f"  - {job.name} (next run: {job.next_run_time})")
```

### 6.2 スケジューラ停止

```python
def stop_scheduler():
    """スケジューラ停止"""

    logger.info("Stopping scheduler")

    scheduler.shutdown(wait=True)

    logger.info("Scheduler stopped")
```

### 6.3 ジョブ管理

```python
def list_scheduled_jobs():
    """スケジュール済みジョブ一覧"""

    jobs = scheduler.get_jobs()

    for job in jobs:
        print(f"{job.id}: {job.name}")
        print(f"  Next run: {job.next_run_time}")
        print(f"  Trigger: {job.trigger}")
        print()

def pause_job(job_id):
    """ジョブ一時停止"""
    scheduler.pause_job(job_id)
    logger.info(f"Job paused: {job_id}")

def resume_job(job_id):
    """ジョブ再開"""
    scheduler.resume_job(job_id)
    logger.info(f"Job resumed: {job_id}")
```

---

## 7. エラーハンドリング

### 7.1 ジョブ失敗時の対応

```python
def job_listener(event):
    """ジョブイベントリスナー"""

    if event.exception:
        logger.error(f"Job {event.job_id} failed: {event.exception}")

        # アラート送信
        send_alert(f"Scheduled job failed: {event.job_id}")

        # リトライ（特定のジョブのみ）
        if event.job_id in ['morning_analysis', 'daily_review']:
            retry_job(event.job_id)

scheduler.add_listener(
    job_listener,
    EVENT_JOB_ERROR | EVENT_JOB_EXECUTED
)

def retry_job(job_id, max_retries=3):
    """ジョブリトライ"""

    for attempt in range(max_retries):
        try:
            logger.info(f"Retrying job {job_id}, attempt {attempt+1}/{max_retries}")

            # ジョブ実行
            job = scheduler.get_job(job_id)
            job.func()

            logger.info(f"Job {job_id} retry successful")
            return

        except Exception as e:
            logger.error(f"Job {job_id} retry failed: {e}")

            if attempt == max_retries - 1:
                send_alert(f"Job {job_id} failed after {max_retries} retries")
```

---

## 8. 監視とログ

### 8.1 スケジューラ稼働監視

```python
def monitor_scheduler():
    """スケジューラ稼働監視（1分ごと）"""

    while True:
        if not scheduler.running:
            logger.critical("Scheduler is not running!")
            send_alert("スケジューラ停止検知")

            # 自動再起動
            try:
                start_scheduler()
                logger.info("Scheduler auto-restarted")
            except Exception as e:
                logger.error(f"Failed to restart scheduler: {e}")

        time.sleep(60)
```

### 8.2 ジョブ実行ログ

```python
def log_job_execution(job_id, success, duration_ms, details=None):
    """ジョブ実行ログ記録"""

    db.insert(
        table='scheduled_job_logs',
        data={
            'timestamp': datetime.now(),
            'job_id': job_id,
            'success': success,
            'duration_ms': duration_ms,
            'details': json.dumps(details) if details else None
        }
    )
```

---

## 9. 実装ロードマップ

### Phase 1（Week 1-2）

**優先度: 最高**

- スケジューラ基盤構築
- 週末停止機能
- 23:00強制決済

### Phase 2（Week 3）

**優先度: 最高**

- 06:00 前日振り返り
- 08:00 朝の詳細分析
- 定期更新（12:00, 16:00, 21:30）

### Phase 3-4（Week 3-4）

**優先度: 中**

- バッチ処理（バックアップ、ログローテーション）
- エラーハンドリング
- ジョブ監視

### Phase 5以降

**優先度: 低**

- 週次・月次レビュー自動化
- 高度なスケジュール管理

---

**以上、運用スケジュール仕様書**
