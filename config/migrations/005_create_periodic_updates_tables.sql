-- ========================================
-- 005: 定期更新テーブル作成マイグレーション
-- ========================================
-- 作成日: 2025-10-23
-- 目的: 定期更新（12:00/16:00/21:30）の結果を保存するテーブル
--

-- ========================================
-- 1. バックテストモード用テーブル
-- ========================================
CREATE TABLE IF NOT EXISTS backtest_periodic_updates (
    id SERIAL PRIMARY KEY,
    update_date DATE NOT NULL,
    update_time VARCHAR(10) NOT NULL,  -- "12:00", "16:00", "21:30"
    symbol VARCHAR(10) NOT NULL,

    -- 更新タイプ
    update_type VARCHAR(30) NOT NULL,  -- no_change, bias_change, risk_adjustment, exit_adjustment, multiple_changes

    -- 分析結果（JSONB形式）
    market_assessment JSONB,           -- {trend_change, volatility_change, key_events}
    strategy_validity JSONB,           -- {morning_bias_valid, confidence_change, reasoning}
    recommended_changes JSONB,         -- {bias, risk_management, exit_strategy}
    positions_action JSONB,            -- {keep_open, close_reason, adjust_sl}
    entry_recommendation JSONB,        -- {should_enter_now, direction, reason, entry_price_zone}
    summary TEXT,                      -- 更新の要約

    -- 市場データスナップショット
    market_data JSONB,

    -- バックテスト識別用
    backtest_start_date DATE,
    backtest_end_date DATE,

    -- メタデータ
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- インデックス用制約
    CONSTRAINT backtest_periodic_updates_unique
        UNIQUE (update_date, update_time, symbol, backtest_start_date, backtest_end_date)
);

-- インデックス作成
CREATE INDEX IF NOT EXISTS idx_backtest_updates_date_time
    ON backtest_periodic_updates(update_date, update_time);
CREATE INDEX IF NOT EXISTS idx_backtest_updates_symbol
    ON backtest_periodic_updates(symbol);
CREATE INDEX IF NOT EXISTS idx_backtest_updates_type
    ON backtest_periodic_updates(update_type);
CREATE INDEX IF NOT EXISTS idx_backtest_updates_backtest_period
    ON backtest_periodic_updates(backtest_start_date, backtest_end_date);

COMMENT ON TABLE backtest_periodic_updates IS '定期更新結果（バックテストモード）';
COMMENT ON COLUMN backtest_periodic_updates.update_time IS '更新時刻（12:00/16:00/21:30）';
COMMENT ON COLUMN backtest_periodic_updates.update_type IS '更新タイプ（no_change/bias_change/risk_adjustment等）';
COMMENT ON COLUMN backtest_periodic_updates.recommended_changes IS '推奨される変更内容';

-- ========================================
-- 2. DEMOモード用テーブル
-- ========================================
CREATE TABLE IF NOT EXISTS demo_periodic_updates (
    id SERIAL PRIMARY KEY,
    update_date DATE NOT NULL,
    update_time VARCHAR(10) NOT NULL,
    symbol VARCHAR(10) NOT NULL,

    -- 更新タイプ
    update_type VARCHAR(30) NOT NULL,

    -- 分析結果（JSONB形式）
    market_assessment JSONB,
    strategy_validity JSONB,
    recommended_changes JSONB,
    positions_action JSONB,
    entry_recommendation JSONB,
    summary TEXT,

    -- 市場データスナップショット
    market_data JSONB,

    -- メタデータ
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- ユニーク制約
    CONSTRAINT demo_periodic_updates_unique
        UNIQUE (update_date, update_time, symbol)
);

-- インデックス作成
CREATE INDEX IF NOT EXISTS idx_demo_updates_date_time
    ON demo_periodic_updates(update_date, update_time);
CREATE INDEX IF NOT EXISTS idx_demo_updates_symbol
    ON demo_periodic_updates(symbol);
CREATE INDEX IF NOT EXISTS idx_demo_updates_type
    ON demo_periodic_updates(update_type);

COMMENT ON TABLE demo_periodic_updates IS '定期更新結果（DEMOモード）';

-- ========================================
-- 3. 本番モード用テーブル
-- ========================================
CREATE TABLE IF NOT EXISTS periodic_updates (
    id SERIAL PRIMARY KEY,
    update_date DATE NOT NULL,
    update_time VARCHAR(10) NOT NULL,
    symbol VARCHAR(10) NOT NULL,

    -- 更新タイプ
    update_type VARCHAR(30) NOT NULL,

    -- 分析結果（JSONB形式）
    market_assessment JSONB,
    strategy_validity JSONB,
    recommended_changes JSONB,
    positions_action JSONB,
    entry_recommendation JSONB,
    summary TEXT,

    -- 市場データスナップショット
    market_data JSONB,

    -- メタデータ
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- ユニーク制約
    CONSTRAINT periodic_updates_unique
        UNIQUE (update_date, update_time, symbol)
);

-- インデックス作成
CREATE INDEX IF NOT EXISTS idx_updates_date_time
    ON periodic_updates(update_date, update_time);
CREATE INDEX IF NOT EXISTS idx_updates_symbol
    ON periodic_updates(symbol);
CREATE INDEX IF NOT EXISTS idx_updates_type
    ON periodic_updates(update_type);

COMMENT ON TABLE periodic_updates IS '定期更新結果（本番モード）';

-- マイグレーション完了
SELECT 'Migration 005: Periodic updates tables created successfully' AS status;
