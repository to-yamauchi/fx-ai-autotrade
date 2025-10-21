# データベース仕様書

## ドキュメント情報
- **作成日**: 2025-10-21
- **バージョン**: 1.0
- **カテゴリ**: システムアーキテクチャ - データ永続化層

---

## 1. 概要

### 1.1 役割

全記録の永続化、分析・改善のためのデータ蓄積

### 1.2 目的

- **トレースability**: 全判断と実行の完全な記録
- **再現性**: バックテストでの検証に必要なデータ保存
- **分析**: パフォーマンス改善のためのデータ蓄積
- **監査**: 問題発生時の追跡と原因究明

### 1.3 技術選定

**推奨**: PostgreSQL

**理由**:
- JSONB型でルールJSONを効率的に保存
- 強力なインデックス機能
- トランザクション保証
- 無料・オープンソース

**代替案**: SQLite（開発初期、単一サーバー環境）

---

## 2. データベーススキーマ

### 2.1 トレード記録テーブル

#### trades

```sql
CREATE TABLE trades (
    -- 基本情報
    id SERIAL PRIMARY KEY,
    trade_date DATE NOT NULL,
    entry_time TIMESTAMP NOT NULL,
    exit_time TIMESTAMP,

    -- ポジション情報
    symbol VARCHAR(10) NOT NULL DEFAULT 'USDJPY',
    direction VARCHAR(4) NOT NULL CHECK (direction IN ('BUY', 'SELL')),
    lot_size DECIMAL(10, 2) NOT NULL,

    -- 価格情報
    entry_price DECIMAL(10, 5) NOT NULL,
    exit_price DECIMAL(10, 5),
    entry_spread DECIMAL(6, 2),
    exit_spread DECIMAL(6, 2),

    -- 損益情報
    pips DECIMAL(10, 2),
    profit_loss_usd DECIMAL(10, 2),
    profit_loss_percent DECIMAL(6, 4),

    -- 決済理由
    exit_reason VARCHAR(100),
    exit_category VARCHAR(50) CHECK (exit_category IN (
        'take_profit', 'stop_loss', 'emergency', 'time_limit',
        'indicator_signal', 'ai_decision', 'manual'
    )),

    -- 関連データ
    rule_version VARCHAR(20),
    ai_judgment_id INTEGER REFERENCES ai_judgments(id),
    market_data_snapshot_id INTEGER REFERENCES market_data_snapshots(id),

    -- メタデータ
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- インデックス
    INDEX idx_trade_date (trade_date),
    INDEX idx_entry_time (entry_time),
    INDEX idx_symbol_direction (symbol, direction),
    INDEX idx_exit_reason (exit_reason)
);
```

### 2.2 AI判断履歴テーブル

#### ai_judgments

```sql
CREATE TABLE ai_judgments (
    -- 基本情報
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,

    -- 判断タイプ
    judgment_type VARCHAR(50) NOT NULL CHECK (judgment_type IN (
        'review', 'morning_analysis', 'periodic_update',
        'layer3a_evaluation', 'layer3b_evaluation'
    )),

    -- AI情報
    model_name VARCHAR(50) NOT NULL,
    prompt_version VARCHAR(20) NOT NULL,
    temperature DECIMAL(3, 2),

    -- 入力データ
    input_data_hash VARCHAR(64),
    input_tokens INTEGER,
    input_data JSONB,  -- 圧縮せずに保存（分析用）

    -- 出力データ
    output_tokens INTEGER,
    response_json JSONB NOT NULL,

    -- コスト情報
    cost_usd DECIMAL(10, 6),

    -- パフォーマンス
    execution_time_ms INTEGER,
    api_response_time_ms INTEGER,

    -- メタデータ
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- インデックス
    INDEX idx_timestamp (timestamp),
    INDEX idx_judgment_type (judgment_type),
    INDEX idx_model_name (model_name),
    INDEX idx_input_hash (input_data_hash),
    INDEX idx_prompt_version (prompt_version)
);
```

### 2.3 ルール履歴テーブル

#### rule_history

```sql
CREATE TABLE rule_history (
    -- 基本情報
    id SERIAL PRIMARY KEY,
    version VARCHAR(20) NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- ルール内容
    rule_json JSONB NOT NULL,

    -- 生成情報
    generated_by VARCHAR(50),  -- 'morning_analysis', 'periodic_update'
    ai_judgment_id INTEGER REFERENCES ai_judgments(id),

    -- 有効期間
    active_from TIMESTAMP NOT NULL,
    active_until TIMESTAMP,
    is_active BOOLEAN DEFAULT true,

    -- メタデータ
    comment TEXT,

    -- インデックス
    INDEX idx_version (version),
    INDEX idx_active_from (active_from),
    INDEX idx_is_active (is_active)
);
```

### 2.4 市場データスナップショットテーブル

#### market_data_snapshots

```sql
CREATE TABLE market_data_snapshots (
    -- 基本情報
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    symbol VARCHAR(10) NOT NULL DEFAULT 'USDJPY',

    -- データハッシュ（再現性確保）
    data_hash VARCHAR(64) NOT NULL UNIQUE,

    -- 標準化データ
    market_data JSONB NOT NULL,

    -- メタデータ
    generation_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- インデックス
    INDEX idx_timestamp (timestamp),
    INDEX idx_data_hash (data_hash),
    INDEX idx_symbol (symbol)
);
```

### 2.5 緊急停止履歴テーブル

#### emergency_stops

```sql
CREATE TABLE emergency_stops (
    -- 基本情報
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,

    -- トレード情報
    trade_id INTEGER REFERENCES trades(id),

    -- 緊急停止理由
    stop_reason VARCHAR(100) NOT NULL CHECK (stop_reason IN (
        '2% loss limit', 'Hard stop: 50pips',
        'Spread alert', 'Flash crash detected'
    )),

    -- 市場状況
    current_price DECIMAL(10, 5),
    entry_price DECIMAL(10, 5),
    pips_from_entry DECIMAL(10, 2),
    loss_amount DECIMAL(10, 2),
    account_balance DECIMAL(12, 2),

    -- メタデータ
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- インデックス
    INDEX idx_timestamp (timestamp),
    INDEX idx_stop_reason (stop_reason),
    INDEX idx_trade_id (trade_id)
);
```

### 2.6 パフォーマンス統計テーブル

#### performance_stats

```sql
CREATE TABLE performance_stats (
    -- 基本情報
    id SERIAL PRIMARY KEY,
    stat_date DATE NOT NULL UNIQUE,

    -- トレード統計
    total_trades INTEGER,
    winning_trades INTEGER,
    losing_trades INTEGER,
    win_rate DECIMAL(6, 4),

    -- 損益統計
    total_pips DECIMAL(10, 2),
    total_profit_loss DECIMAL(12, 2),
    average_win DECIMAL(10, 2),
    average_loss DECIMAL(10, 2),
    profit_factor DECIMAL(6, 4),

    -- リスク統計
    max_drawdown DECIMAL(6, 4),
    max_consecutive_losses INTEGER,
    largest_loss DECIMAL(10, 2),

    -- AI精度統計
    direction_accuracy DECIMAL(6, 4),
    entry_timing_score DECIMAL(6, 4),

    -- メタデータ
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- インデックス
    INDEX idx_stat_date (stat_date)
);
```

### 2.7 システムログテーブル

#### system_logs

```sql
CREATE TABLE system_logs (
    -- 基本情報
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- ログレベル
    level VARCHAR(20) NOT NULL CHECK (level IN (
        'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
    )),

    -- ログ内容
    component VARCHAR(50),  -- 'data_engine', 'ai_engine', 'rule_engine'
    message TEXT NOT NULL,
    details JSONB,

    -- コンテキスト
    trade_id INTEGER REFERENCES trades(id),
    ai_judgment_id INTEGER REFERENCES ai_judgments(id),

    -- インデックス
    INDEX idx_timestamp (timestamp),
    INDEX idx_level (level),
    INDEX idx_component (component)
);
```

### 2.8 バックテスト結果テーブル

#### backtest_results

```sql
CREATE TABLE backtest_results (
    -- 基本情報
    id SERIAL PRIMARY KEY,
    run_id UUID NOT NULL,
    run_date TIMESTAMP NOT NULL,

    -- バックテスト設定
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    prompt_version VARCHAR(20),
    model_name VARCHAR(50),

    -- 結果統計
    total_days INTEGER,
    direction_accuracy DECIMAL(6, 4),
    entry_judgment_validity DECIMAL(6, 4),
    consistency_score DECIMAL(6, 4),

    -- 仮想損益
    virtual_total_pips DECIMAL(10, 2),
    virtual_profit_loss DECIMAL(12, 2),
    virtual_win_rate DECIMAL(6, 4),

    -- 詳細結果（日次）
    daily_results JSONB,

    -- メタデータ
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- インデックス
    INDEX idx_run_id (run_id),
    INDEX idx_run_date (run_date),
    INDEX idx_date_range (start_date, end_date)
);
```

---

## 3. データ保存ポリシー

### 3.1 保存タイミング

| データ | 保存タイミング | 優先度 |
|--------|--------------|--------|
| AI判断履歴 | AI実行直後（非同期） | 高 |
| ルール履歴 | ルール生成・更新時 | 高 |
| 市場データ | スナップショット作成時（非同期） | 中 |
| トレード記録（エントリー） | エントリー実行直後 | 最高 |
| トレード記録（決済） | 決済実行直後 | 最高 |
| 緊急停止履歴 | 緊急停止発生時 | 最高 |
| システムログ | 随時（バッファリング） | 中 |
| パフォーマンス統計 | 日次バッチ処理 | 低 |

### 3.2 データ保持期間

| データ | 保持期間 | 理由 |
|--------|---------|------|
| トレード記録 | 永久 | 分析・税務 |
| AI判断履歴 | 永久 | 改善・検証 |
| ルール履歴 | 永久 | トレースability |
| 市場データ | 1年 | バックテスト用 |
| 緊急停止履歴 | 永久 | 安全性分析 |
| システムログ（INFO以下） | 3ヶ月 | ディスク容量 |
| システムログ（WARNING以上） | 1年 | トラブル分析 |
| パフォーマンス統計 | 永久 | 長期分析 |

---

## 4. データアクセスパターン

### 4.1 書き込み操作

#### 4.1.1 トレードエントリー記録

```python
def record_trade_entry(entry_info, rule, ai_judgment_id, snapshot_id):
    query = """
    INSERT INTO trades (
        trade_date, entry_time, symbol, direction, lot_size,
        entry_price, entry_spread, rule_version,
        ai_judgment_id, market_data_snapshot_id
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    ) RETURNING id
    """
    params = (
        entry_info.date, entry_info.time, 'USDJPY',
        entry_info.direction, entry_info.lot_size,
        entry_info.price, entry_info.spread,
        rule.version, ai_judgment_id, snapshot_id
    )
    trade_id = db.execute(query, params).fetchone()[0]
    return trade_id
```

#### 4.1.2 AI判断記録

```python
def record_ai_judgment(judgment_type, model, prompt_version, input_data, response, cost, exec_time):
    query = """
    INSERT INTO ai_judgments (
        timestamp, judgment_type, model_name, prompt_version,
        temperature, input_data_hash, input_tokens, input_data,
        output_tokens, response_json, cost_usd, execution_time_ms
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    ) RETURNING id
    """
    data_hash = generate_data_hash(input_data)
    params = (
        datetime.now(), judgment_type, model, prompt_version,
        0.3, data_hash, input_data['tokens'], Json(input_data),
        response['tokens'], Json(response), cost, exec_time
    )
    judgment_id = db.execute(query, params).fetchone()[0]
    return judgment_id
```

### 4.2 読み込み操作

#### 4.2.1 最新ルール取得

```python
def get_active_rule():
    query = """
    SELECT rule_json, version
    FROM rule_history
    WHERE is_active = true
    ORDER BY active_from DESC
    LIMIT 1
    """
    result = db.execute(query).fetchone()
    return result['rule_json'], result['version']
```

#### 4.2.2 前日のトレード取得（振り返り用）

```python
def get_yesterday_trades():
    query = """
    SELECT
        t.*,
        aj.response_json as ai_prediction
    FROM trades t
    LEFT JOIN ai_judgments aj ON t.ai_judgment_id = aj.id
    WHERE t.trade_date = CURRENT_DATE - INTERVAL '1 day'
    ORDER BY t.entry_time
    """
    return db.execute(query).fetchall()
```

#### 4.2.3 過去N日の統計取得

```python
def get_recent_stats(days=5):
    query = """
    SELECT *
    FROM performance_stats
    WHERE stat_date >= CURRENT_DATE - INTERVAL '%s days'
    ORDER BY stat_date DESC
    """
    return db.execute(query, (days,)).fetchall()
```

---

## 5. パフォーマンス最適化

### 5.1 インデックス戦略

**頻繁にクエリされるカラム**:
- timestamp系（全テーブル）
- trade_date, entry_time
- judgment_type, model_name
- data_hash（ユニーク制約兼インデックス）

**JSONB GINインデックス**:
```sql
CREATE INDEX idx_ai_judgments_response ON ai_judgments USING GIN (response_json);
CREATE INDEX idx_rule_history_rule ON rule_history USING GIN (rule_json);
CREATE INDEX idx_market_data ON market_data_snapshots USING GIN (market_data);
```

### 5.2 パーティショニング

**大規模データ対策（将来）**:
```sql
-- trades テーブルを月次パーティション
CREATE TABLE trades (
    ...
) PARTITION BY RANGE (entry_time);

CREATE TABLE trades_2025_10 PARTITION OF trades
    FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');

CREATE TABLE trades_2025_11 PARTITION OF trades
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');
```

### 5.3 非同期書き込み

**優先度の低い記録**:
```python
import asyncio
from queue import Queue

write_queue = Queue()

async def background_writer():
    while True:
        if not write_queue.empty():
            write_func, params = write_queue.get()
            await write_func(**params)
        await asyncio.sleep(0.1)

def async_record_market_data(snapshot):
    write_queue.put((record_market_data, {'snapshot': snapshot}))
```

---

## 6. バックアップ戦略

### 6.1 日次バックアップ

**スケジュール**: 毎日04:00（取引時間外）

**方法**:
```bash
#!/bin/bash
# daily_backup.sh

DATE=$(date +%Y%m%d)
BACKUP_DIR="/backup/postgres"
DB_NAME="fx_autotrade"

pg_dump -U postgres -F c -b -v -f "$BACKUP_DIR/fx_autotrade_$DATE.backup" $DB_NAME

# 30日以上古いバックアップを削除
find $BACKUP_DIR -name "*.backup" -mtime +30 -delete
```

### 6.2 トランザクションログ

**WALアーカイブ**: 継続的バックアップ
```sql
-- postgresql.conf
wal_level = replica
archive_mode = on
archive_command = 'cp %p /backup/wal_archive/%f'
```

### 6.3 リストア手順

```bash
# データベース削除（既存）
dropdb fx_autotrade

# リストア実行
pg_restore -U postgres -C -d postgres /backup/postgres/fx_autotrade_20251020.backup
```

---

## 7. セキュリティ

### 7.1 アクセス制御

```sql
-- アプリケーション専用ユーザー
CREATE USER fx_app WITH PASSWORD 'secure_password';

-- 必要最小限の権限
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO fx_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO fx_app;

-- DELETE権限は付与しない（データ保護）
```

### 7.2 暗号化

**保存時**:
- PostgreSQL透過的データ暗号化（TDE）
- 機密データは個別暗号化（将来）

**転送時**:
- SSL/TLS接続必須
```python
conn = psycopg2.connect(
    host="localhost",
    database="fx_autotrade",
    user="fx_app",
    password="secure_password",
    sslmode="require"
)
```

---

## 8. 監視とメンテナンス

### 8.1 定期メンテナンス

**VACUUM（週次）**:
```sql
-- 不要領域の回収
VACUUM ANALYZE;
```

**統計更新（日次）**:
```sql
ANALYZE;
```

### 8.2 容量監視

```sql
-- テーブルサイズ確認
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## 9. 実装ロードマップ

### Phase 1（Week 1-2）

**優先度: 最高**

- PostgreSQLセットアップ
- 基本テーブル作成（trades, ai_judgments, rule_history, market_data_snapshots）
- 基本的なCRUD操作実装

### Phase 2-3（Week 3-4）

**優先度: 高**

- 残りのテーブル作成（emergency_stops, system_logs）
- インデックス最適化
- バックアップスクリプト

### Phase 4以降

**優先度: 中**

- パフォーマンス統計自動計算
- バックテスト結果保存
- 高度なクエリ最適化

---

**以上、データベース仕様書**
