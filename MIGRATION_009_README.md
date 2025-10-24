# マイグレーション009: exit_reasonカラム長の拡張

## 概要

`backtest_trades`テーブルの`exit_reason`カラムの長さを`VARCHAR(100)`から`VARCHAR(500)`に拡張します。

## 発生していた問題

決済理由（exit_reason）が100文字を超える場合、以下のエラーが発生していました：

```
ERROR: Failed to save trade to database: 値は型character varying(100)としては長すぎます
```

## 対処内容

### 1. 緊急対応（完了）

`src/backtest/trade_simulator.py`を修正し、exit_reasonを100文字に切り詰めるようにしました。
これにより、マイグレーション実行前でもエラーが発生しなくなります。

### 2. 根本対応（要実行）

以下のいずれかの方法でマイグレーション009を実行してください。

#### 方法1: Pythonスクリプトで実行（推奨）

```bash
python apply_migration_009.py
```

#### 方法2: psqlコマンドで実行

```bash
psql -U postgres -d fx_autotrade -f config/migrations/009_extend_backtest_trades_exit_reason.sql
```

または、PostgreSQLの設定に応じて：

```bash
PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -f config/migrations/009_extend_backtest_trades_exit_reason.sql
```

#### 方法3: PostgreSQLクライアントで直接実行

PostgreSQLクライアント（pgAdmin、DBeaver等）で以下のSQLを実行：

```sql
ALTER TABLE backtest_trades
ALTER COLUMN exit_reason TYPE VARCHAR(500);

COMMENT ON COLUMN backtest_trades.exit_reason IS '決済理由（最大500文字）';
```

## マイグレーション実行後

マイグレーション実行後は、`trade_simulator.py`の切り詰め処理を500文字に変更することができます：

```python
# trade_simulator.py の 528行目付近
if len(exit_reason) > 500:
    exit_reason = exit_reason[:497] + '...'
```

## 確認方法

マイグレーションが正しく実行されたか確認：

```sql
SELECT column_name, data_type, character_maximum_length
FROM information_schema.columns
WHERE table_name = 'backtest_trades' AND column_name = 'exit_reason';
```

期待される結果：
```
 column_name  | data_type | character_maximum_length
--------------+-----------+-------------------------
 exit_reason  | character varying | 500
```
