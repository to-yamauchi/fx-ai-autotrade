-- ========================================
-- FX自動トレードシステム - 拡張データベーススキーマ
-- ========================================
--
-- バックテストモード、DEMOモード用のテーブルを追加
-- 本番モード用のテーブルは既存のdatabase_schema.sqlを使用
--
-- 作成日: 2025-10-23
-- ========================================

-- ========================================
-- バックテストモード用テーブル
-- ========================================

-- バックテストAI判断テーブル
CREATE TABLE IF NOT EXISTS backtest_ai_judgments (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    action VARCHAR(10) NOT NULL CHECK (action IN ('BUY', 'SELL', 'HOLD')),
    confidence INTEGER NOT NULL CHECK (confidence >= 0 AND confidence <= 100),
    reasoning TEXT,
    entry_price DECIMAL(10, 5),
    stop_loss DECIMAL(10, 5),
    take_profit DECIMAL(10, 5),
    indicators JSONB,
    market_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- バックテスト期間識別用
    backtest_start_date DATE NOT NULL,
    backtest_end_date DATE NOT NULL,

    -- インデックス
    CONSTRAINT backtest_ai_judgments_unique UNIQUE (symbol, timestamp, backtest_start_date, backtest_end_date)
);

-- バックテストポジションテーブル
CREATE TABLE IF NOT EXISTS backtest_positions (
    id SERIAL PRIMARY KEY,
    ticket VARCHAR(50) NOT NULL,  -- バックテストではシミュレーションID
    symbol VARCHAR(10) NOT NULL,
    type VARCHAR(10) NOT NULL CHECK (type IN ('BUY', 'SELL')),
    volume DECIMAL(10, 2) NOT NULL,
    open_price DECIMAL(10, 5) NOT NULL,
    close_price DECIMAL(10, 5),
    sl DECIMAL(10, 5),
    tp DECIMAL(10, 5),
    open_time TIMESTAMP NOT NULL,
    close_time TIMESTAMP,
    profit DECIMAL(15, 2),
    commission DECIMAL(10, 2) DEFAULT 0,
    swap DECIMAL(10, 2) DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'CLOSED', 'CANCELLED')),
    comment TEXT,

    -- AI判断との関連
    ai_judgment_id INTEGER REFERENCES backtest_ai_judgments(id),

    -- バックテスト期間識別用
    backtest_start_date DATE NOT NULL,
    backtest_end_date DATE NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================================
-- DEMOモード用テーブル
-- ========================================

-- DEMO AI判断テーブル
CREATE TABLE IF NOT EXISTS demo_ai_judgments (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    action VARCHAR(10) NOT NULL CHECK (action IN ('BUY', 'SELL', 'HOLD')),
    confidence INTEGER NOT NULL CHECK (confidence >= 0 AND confidence <= 100),
    reasoning TEXT,
    entry_price DECIMAL(10, 5),
    stop_loss DECIMAL(10, 5),
    take_profit DECIMAL(10, 5),
    indicators JSONB,
    market_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- インデックス
    CONSTRAINT demo_ai_judgments_unique UNIQUE (symbol, timestamp)
);

-- DEMOポジションテーブル
CREATE TABLE IF NOT EXISTS demo_positions (
    id SERIAL PRIMARY KEY,
    ticket BIGINT NOT NULL UNIQUE,  -- MT5のチケット番号
    symbol VARCHAR(10) NOT NULL,
    type VARCHAR(10) NOT NULL CHECK (type IN ('BUY', 'SELL')),
    volume DECIMAL(10, 2) NOT NULL,
    open_price DECIMAL(10, 5) NOT NULL,
    close_price DECIMAL(10, 5),
    sl DECIMAL(10, 5),
    tp DECIMAL(10, 5),
    open_time TIMESTAMP NOT NULL,
    close_time TIMESTAMP,
    profit DECIMAL(15, 2),
    commission DECIMAL(10, 2) DEFAULT 0,
    swap DECIMAL(10, 2) DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'CLOSED', 'CANCELLED')),
    comment TEXT,

    -- AI判断との関連
    ai_judgment_id INTEGER REFERENCES demo_ai_judgments(id),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================================
-- インデックス作成
-- ========================================

-- バックテスト用インデックス
CREATE INDEX IF NOT EXISTS idx_backtest_ai_judgments_symbol_time
    ON backtest_ai_judgments(symbol, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_backtest_ai_judgments_period
    ON backtest_ai_judgments(backtest_start_date, backtest_end_date);

CREATE INDEX IF NOT EXISTS idx_backtest_positions_symbol_status
    ON backtest_positions(symbol, status);

CREATE INDEX IF NOT EXISTS idx_backtest_positions_period
    ON backtest_positions(backtest_start_date, backtest_end_date);

CREATE INDEX IF NOT EXISTS idx_backtest_positions_ticket
    ON backtest_positions(ticket);

-- DEMO用インデックス
CREATE INDEX IF NOT EXISTS idx_demo_ai_judgments_symbol_time
    ON demo_ai_judgments(symbol, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_demo_positions_symbol_status
    ON demo_positions(symbol, status);

CREATE INDEX IF NOT EXISTS idx_demo_positions_ticket
    ON demo_positions(ticket);

-- ========================================
-- トリガー（updated_atの自動更新）
-- ========================================

-- バックテストポジション更新トリガー
CREATE OR REPLACE FUNCTION update_backtest_positions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_backtest_positions_updated_at
    BEFORE UPDATE ON backtest_positions
    FOR EACH ROW
    EXECUTE FUNCTION update_backtest_positions_updated_at();

-- DEMOポジション更新トリガー
CREATE OR REPLACE FUNCTION update_demo_positions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_demo_positions_updated_at
    BEFORE UPDATE ON demo_positions
    FOR EACH ROW
    EXECUTE FUNCTION update_demo_positions_updated_at();

-- ========================================
-- ビュー（統計用）
-- ========================================

-- バックテスト結果サマリービュー
CREATE OR REPLACE VIEW backtest_summary AS
SELECT
    backtest_start_date,
    backtest_end_date,
    symbol,
    COUNT(*) as total_trades,
    SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) as winning_trades,
    SUM(CASE WHEN profit < 0 THEN 1 ELSE 0 END) as losing_trades,
    SUM(CASE WHEN profit = 0 THEN 1 ELSE 0 END) as breakeven_trades,
    SUM(profit) as total_profit,
    AVG(profit) as avg_profit,
    MAX(profit) as max_profit,
    MIN(profit) as min_profit,
    CASE
        WHEN COUNT(*) > 0
        THEN CAST(SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100
        ELSE 0
    END as win_rate
FROM backtest_positions
WHERE status = 'CLOSED'
GROUP BY backtest_start_date, backtest_end_date, symbol;

-- DEMO結果サマリービュー
CREATE OR REPLACE VIEW demo_summary AS
SELECT
    DATE(open_time) as trade_date,
    symbol,
    COUNT(*) as total_trades,
    SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) as winning_trades,
    SUM(CASE WHEN profit < 0 THEN 1 ELSE 0 END) as losing_trades,
    SUM(profit) as total_profit,
    AVG(profit) as avg_profit,
    MAX(profit) as max_profit,
    MIN(profit) as min_profit,
    CASE
        WHEN COUNT(*) > 0
        THEN CAST(SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100
        ELSE 0
    END as win_rate
FROM demo_positions
WHERE status = 'CLOSED'
GROUP BY DATE(open_time), symbol;

-- ========================================
-- コメント
-- ========================================

COMMENT ON TABLE backtest_ai_judgments IS 'バックテストモード用AI判断テーブル';
COMMENT ON TABLE backtest_positions IS 'バックテストモード用ポジションテーブル';
COMMENT ON TABLE demo_ai_judgments IS 'DEMOモード用AI判断テーブル';
COMMENT ON TABLE demo_positions IS 'DEMOモード用ポジションテーブル';

COMMENT ON VIEW backtest_summary IS 'バックテスト結果サマリー';
COMMENT ON VIEW demo_summary IS 'DEMO取引結果サマリー';
