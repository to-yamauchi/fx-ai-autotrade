-- ========================================
-- 006: Layer 3監視テーブル作成マイグレーション
-- ========================================
-- 作成日: 2025-10-23
-- 目的: Layer 3a監視（15分ごと）とLayer 3b緊急評価（異常時）のテーブル
--

-- ========================================
-- Part 1: Layer 3a 監視テーブル（15分ごと、ポジション保有時）
-- ========================================

-- バックテストモード用
CREATE TABLE IF NOT EXISTS backtest_layer3a_monitoring (
    id SERIAL PRIMARY KEY,
    check_timestamp TIMESTAMP NOT NULL,
    symbol VARCHAR(10) NOT NULL,

    -- 監視結果
    action VARCHAR(20) NOT NULL,  -- HOLD, CLOSE_NOW, ADJUST_SL, PARTIAL_CLOSE
    urgency VARCHAR(10) NOT NULL DEFAULT 'normal',  -- normal, high
    reason TEXT,

    -- 詳細情報（JSONB）
    details JSONB,                     -- {profit_status, risk_level, signals}
    recommended_action JSONB,          -- {close_percent, new_sl, reason}

    -- ポジション情報と市場データ
    position_info JSONB,
    market_data JSONB,

    -- バックテスト識別用
    backtest_start_date DATE,
    backtest_end_date DATE,

    -- メタデータ
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- インデックス作成
CREATE INDEX IF NOT EXISTS idx_backtest_layer3a_timestamp
    ON backtest_layer3a_monitoring(check_timestamp);
CREATE INDEX IF NOT EXISTS idx_backtest_layer3a_symbol
    ON backtest_layer3a_monitoring(symbol);
CREATE INDEX IF NOT EXISTS idx_backtest_layer3a_action
    ON backtest_layer3a_monitoring(action);

COMMENT ON TABLE backtest_layer3a_monitoring IS 'Layer 3a 監視結果（15分ごと、バックテスト）';
COMMENT ON COLUMN backtest_layer3a_monitoring.action IS '推奨アクション（HOLD/CLOSE_NOW/ADJUST_SL/PARTIAL_CLOSE）';

-- DEMOモード用
CREATE TABLE IF NOT EXISTS demo_layer3a_monitoring (
    id SERIAL PRIMARY KEY,
    check_timestamp TIMESTAMP NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    action VARCHAR(20) NOT NULL,
    urgency VARCHAR(10) NOT NULL DEFAULT 'normal',
    reason TEXT,
    details JSONB,
    recommended_action JSONB,
    position_info JSONB,
    market_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_demo_layer3a_timestamp
    ON demo_layer3a_monitoring(check_timestamp);

COMMENT ON TABLE demo_layer3a_monitoring IS 'Layer 3a 監視結果（15分ごと、DEMO）';

-- 本番モード用
CREATE TABLE IF NOT EXISTS layer3a_monitoring (
    id SERIAL PRIMARY KEY,
    check_timestamp TIMESTAMP NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    action VARCHAR(20) NOT NULL,
    urgency VARCHAR(10) NOT NULL DEFAULT 'normal',
    reason TEXT,
    details JSONB,
    recommended_action JSONB,
    position_info JSONB,
    market_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_layer3a_timestamp
    ON layer3a_monitoring(check_timestamp);

COMMENT ON TABLE layer3a_monitoring IS 'Layer 3a 監視結果（15分ごと、本番）';

-- ========================================
-- Part 2: Layer 3b 緊急評価テーブル（異常検知時）
-- ========================================

-- バックテストモード用
CREATE TABLE IF NOT EXISTS backtest_layer3b_emergency (
    id SERIAL PRIMARY KEY,
    event_timestamp TIMESTAMP NOT NULL,
    symbol VARCHAR(10) NOT NULL,

    -- 評価結果
    severity VARCHAR(10) NOT NULL,  -- low, medium, high, critical
    action VARCHAR(20) NOT NULL,    -- CONTINUE, CLOSE_ALL, CLOSE_PARTIAL, REVERSE, HEDGE
    reasoning TEXT,

    -- 詳細情報（JSONB）
    immediate_actions JSONB,        -- Array of immediate actions
    risk_assessment JSONB,          -- {current_risk, potential_loss, time_sensitivity, recommendation}

    -- 異常情報と市場データ
    anomaly_info JSONB,             -- Layer 2 anomaly detection info
    market_data JSONB,

    -- バックテスト識別用
    backtest_start_date DATE,
    backtest_end_date DATE,

    -- メタデータ
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- インデックス作成
CREATE INDEX IF NOT EXISTS idx_backtest_layer3b_timestamp
    ON backtest_layer3b_emergency(event_timestamp);
CREATE INDEX IF NOT EXISTS idx_backtest_layer3b_symbol
    ON backtest_layer3b_emergency(symbol);
CREATE INDEX IF NOT EXISTS idx_backtest_layer3b_severity
    ON backtest_layer3b_emergency(severity);
CREATE INDEX IF NOT EXISTS idx_backtest_layer3b_action
    ON backtest_layer3b_emergency(action);

COMMENT ON TABLE backtest_layer3b_emergency IS 'Layer 3b 緊急評価結果（異常検知時、バックテスト）';
COMMENT ON COLUMN backtest_layer3b_emergency.severity IS '深刻度（low/medium/high/critical）';
COMMENT ON COLUMN backtest_layer3b_emergency.action IS '推奨アクション（CONTINUE/CLOSE_ALL/CLOSE_PARTIAL/REVERSE/HEDGE）';

-- DEMOモード用
CREATE TABLE IF NOT EXISTS demo_layer3b_emergency (
    id SERIAL PRIMARY KEY,
    event_timestamp TIMESTAMP NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    severity VARCHAR(10) NOT NULL,
    action VARCHAR(20) NOT NULL,
    reasoning TEXT,
    immediate_actions JSONB,
    risk_assessment JSONB,
    anomaly_info JSONB,
    market_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_demo_layer3b_timestamp
    ON demo_layer3b_emergency(event_timestamp);
CREATE INDEX IF NOT EXISTS idx_demo_layer3b_severity
    ON demo_layer3b_emergency(severity);

COMMENT ON TABLE demo_layer3b_emergency IS 'Layer 3b 緊急評価結果（異常検知時、DEMO）';

-- 本番モード用
CREATE TABLE IF NOT EXISTS layer3b_emergency (
    id SERIAL PRIMARY KEY,
    event_timestamp TIMESTAMP NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    severity VARCHAR(10) NOT NULL,
    action VARCHAR(20) NOT NULL,
    reasoning TEXT,
    immediate_actions JSONB,
    risk_assessment JSONB,
    anomaly_info JSONB,
    market_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_layer3b_timestamp
    ON layer3b_emergency(event_timestamp);
CREATE INDEX IF NOT EXISTS idx_layer3b_severity
    ON layer3b_emergency(severity);

COMMENT ON TABLE layer3b_emergency IS 'Layer 3b 緊急評価結果（異常検知時、本番）';

-- マイグレーション完了
SELECT 'Migration 006: Layer 3 monitoring tables created successfully' AS status;
