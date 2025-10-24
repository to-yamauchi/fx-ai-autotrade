-- ================================
-- バックテストトレードテーブル作成
-- ================================
--
-- ファイル名: 008_create_backtest_trades.sql
-- パス: config/migrations/008_create_backtest_trades.sql
--
-- 【概要】
-- バックテストで実行された個々のトレード（エントリー・決済）を保存するテーブルを作成します。
--
-- 【実行方法】
-- psql -U postgres -d fx_autotrade -f config/migrations/008_create_backtest_trades.sql
--
-- 【作成日】2025-01-26

-- バックテストトレードテーブル
CREATE TABLE IF NOT EXISTS backtest_trades (
    id SERIAL PRIMARY KEY,

    -- バックテスト識別
    symbol VARCHAR(20) NOT NULL,
    backtest_start_date DATE NOT NULL,
    backtest_end_date DATE NOT NULL,

    -- トレード基本情報
    ticket INTEGER NOT NULL,
    action VARCHAR(10) NOT NULL,  -- BUY or SELL
    volume NUMERIC(10, 2) NOT NULL,

    -- エントリー情報
    entry_time TIMESTAMP NOT NULL,
    entry_price NUMERIC(10, 5) NOT NULL,

    -- 決済情報
    exit_time TIMESTAMP,
    exit_price NUMERIC(10, 5),
    exit_reason VARCHAR(100),  -- TP, SL, Manual close, Layer3a, Layer3b, etc.

    -- リスク管理
    stop_loss NUMERIC(10, 5),
    take_profit NUMERIC(10, 5),

    -- 損益
    profit_loss NUMERIC(15, 2),  -- 損益（円）
    profit_pips NUMERIC(10, 2),  -- 損益（pips）

    -- コメント
    comment TEXT,

    -- メタデータ
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- インデックス用
    CONSTRAINT unique_backtest_trade UNIQUE (symbol, backtest_start_date, backtest_end_date, ticket)
);

-- コメント追加
COMMENT ON TABLE backtest_trades IS 'バックテストで実行された個々のトレード情報';
COMMENT ON COLUMN backtest_trades.id IS 'トレードID';
COMMENT ON COLUMN backtest_trades.symbol IS '通貨ペア';
COMMENT ON COLUMN backtest_trades.backtest_start_date IS 'バックテスト開始日';
COMMENT ON COLUMN backtest_trades.backtest_end_date IS 'バックテスト終了日';
COMMENT ON COLUMN backtest_trades.ticket IS 'チケット番号';
COMMENT ON COLUMN backtest_trades.action IS 'トレード方向（BUY/SELL）';
COMMENT ON COLUMN backtest_trades.volume IS 'ロット数';
COMMENT ON COLUMN backtest_trades.entry_time IS 'エントリー時刻';
COMMENT ON COLUMN backtest_trades.entry_price IS 'エントリー価格';
COMMENT ON COLUMN backtest_trades.exit_time IS '決済時刻';
COMMENT ON COLUMN backtest_trades.exit_price IS '決済価格';
COMMENT ON COLUMN backtest_trades.exit_reason IS '決済理由';
COMMENT ON COLUMN backtest_trades.stop_loss IS 'ストップロス';
COMMENT ON COLUMN backtest_trades.take_profit IS 'テイクプロフィット';
COMMENT ON COLUMN backtest_trades.profit_loss IS '損益（円）';
COMMENT ON COLUMN backtest_trades.profit_pips IS '損益（pips）';
COMMENT ON COLUMN backtest_trades.comment IS 'コメント';
COMMENT ON COLUMN backtest_trades.created_at IS '作成日時';

-- インデックス作成
CREATE INDEX IF NOT EXISTS idx_backtest_trades_symbol ON backtest_trades(symbol);
CREATE INDEX IF NOT EXISTS idx_backtest_trades_date ON backtest_trades(backtest_start_date, backtest_end_date);
CREATE INDEX IF NOT EXISTS idx_backtest_trades_entry_time ON backtest_trades(entry_time);
CREATE INDEX IF NOT EXISTS idx_backtest_trades_ticket ON backtest_trades(ticket);

-- サマリービュー作成
CREATE OR REPLACE VIEW backtest_trades_summary AS
SELECT
    symbol,
    backtest_start_date,
    backtest_end_date,
    COUNT(*) AS total_trades,
    COUNT(*) FILTER (WHERE profit_loss > 0) AS winning_trades,
    COUNT(*) FILTER (WHERE profit_loss <= 0) AS losing_trades,
    ROUND(100.0 * COUNT(*) FILTER (WHERE profit_loss > 0) / NULLIF(COUNT(*), 0), 2) AS win_rate,
    SUM(profit_loss) FILTER (WHERE profit_loss > 0) AS total_profit,
    SUM(profit_loss) FILTER (WHERE profit_loss <= 0) AS total_loss,
    SUM(profit_loss) AS net_profit,
    SUM(profit_pips) AS total_pips,
    AVG(profit_loss) AS avg_profit_loss,
    MAX(profit_loss) AS max_win,
    MIN(profit_loss) AS max_loss
FROM backtest_trades
WHERE exit_time IS NOT NULL
GROUP BY symbol, backtest_start_date, backtest_end_date
ORDER BY backtest_start_date DESC;

COMMENT ON VIEW backtest_trades_summary IS 'バックテストトレードのサマリービュー';

-- 権限設定
GRANT SELECT, INSERT, UPDATE ON backtest_trades TO PUBLIC;
GRANT SELECT ON backtest_trades_summary TO PUBLIC;
