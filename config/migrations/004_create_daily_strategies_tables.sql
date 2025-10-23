-- ========================================
-- 004: デイリー戦略テーブル作成マイグレーション
-- ========================================
-- 作成日: 2025-10-23
-- 目的: 朝の詳細分析（08:00）の戦略結果を保存するテーブル
--

-- ========================================
-- 1. バックテストモード用テーブル
-- ========================================
CREATE TABLE IF NOT EXISTS backtest_daily_strategies (
    id SERIAL PRIMARY KEY,
    strategy_date DATE NOT NULL,
    symbol VARCHAR(10) NOT NULL,

    -- 基本戦略情報
    daily_bias VARCHAR(10) NOT NULL,  -- BUY/SELL/NEUTRAL
    confidence DECIMAL(4,3) CHECK (confidence >= 0 AND confidence <= 1),  -- 0.000-1.000
    reasoning TEXT,

    -- 詳細分析結果（JSONB形式）
    market_environment JSONB,       -- {trend, strength, phase}
    entry_conditions JSONB,         -- {should_trade, direction, price_zone, required_signals, avoid_if}
    exit_strategy JSONB,            -- {take_profit, stop_loss, indicator_exits, time_exits}
    risk_management JSONB,          -- {position_size_multiplier, max_positions, reason}
    key_levels JSONB,               -- {entry_target, invalidation_level, critical_support, critical_resistance}
    scenario_planning JSONB,        -- {bullish_scenario, bearish_scenario, base_case}
    lessons_applied JSONB,          -- Array of lessons from daily review

    -- 市場データスナップショット
    market_data JSONB,

    -- バックテスト識別用
    backtest_start_date DATE,
    backtest_end_date DATE,

    -- メタデータ
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- ユニーク制約（同じバックテスト内で同じ日の戦略は1つまで）
    CONSTRAINT backtest_daily_strategies_unique
        UNIQUE (strategy_date, symbol, backtest_start_date, backtest_end_date)
);

-- インデックス作成
CREATE INDEX IF NOT EXISTS idx_backtest_strategies_date
    ON backtest_daily_strategies(strategy_date);
CREATE INDEX IF NOT EXISTS idx_backtest_strategies_symbol
    ON backtest_daily_strategies(symbol);
CREATE INDEX IF NOT EXISTS idx_backtest_strategies_backtest_period
    ON backtest_daily_strategies(backtest_start_date, backtest_end_date);
CREATE INDEX IF NOT EXISTS idx_backtest_strategies_bias
    ON backtest_daily_strategies(daily_bias);

COMMENT ON TABLE backtest_daily_strategies IS '朝の詳細分析結果（バックテストモード）';
COMMENT ON COLUMN backtest_daily_strategies.daily_bias IS '本日のバイアス（BUY/SELL/NEUTRAL）';
COMMENT ON COLUMN backtest_daily_strategies.confidence IS '信頼度（0.000-1.000）';
COMMENT ON COLUMN backtest_daily_strategies.entry_conditions IS 'エントリー条件（price_zone, required_signals等）';
COMMENT ON COLUMN backtest_daily_strategies.exit_strategy IS '決済戦略（TP/SL/インジケーター決済等）';
COMMENT ON COLUMN backtest_daily_strategies.lessons_applied IS '前日の振り返りから得た教訓の適用';

-- ========================================
-- 2. DEMOモード用テーブル
-- ========================================
CREATE TABLE IF NOT EXISTS demo_daily_strategies (
    id SERIAL PRIMARY KEY,
    strategy_date DATE NOT NULL,
    symbol VARCHAR(10) NOT NULL,

    -- 基本戦略情報
    daily_bias VARCHAR(10) NOT NULL,
    confidence DECIMAL(4,3) CHECK (confidence >= 0 AND confidence <= 1),
    reasoning TEXT,

    -- 詳細分析結果（JSONB形式）
    market_environment JSONB,
    entry_conditions JSONB,
    exit_strategy JSONB,
    risk_management JSONB,
    key_levels JSONB,
    scenario_planning JSONB,
    lessons_applied JSONB,

    -- 市場データスナップショット
    market_data JSONB,

    -- メタデータ
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- ユニーク制約（1日1戦略）
    CONSTRAINT demo_daily_strategies_unique UNIQUE (strategy_date, symbol)
);

-- インデックス作成
CREATE INDEX IF NOT EXISTS idx_demo_strategies_date
    ON demo_daily_strategies(strategy_date);
CREATE INDEX IF NOT EXISTS idx_demo_strategies_symbol
    ON demo_daily_strategies(symbol);
CREATE INDEX IF NOT EXISTS idx_demo_strategies_bias
    ON demo_daily_strategies(daily_bias);

COMMENT ON TABLE demo_daily_strategies IS '朝の詳細分析結果（DEMOモード）';

-- ========================================
-- 3. 本番モード用テーブル
-- ========================================
CREATE TABLE IF NOT EXISTS daily_strategies (
    id SERIAL PRIMARY KEY,
    strategy_date DATE NOT NULL,
    symbol VARCHAR(10) NOT NULL,

    -- 基本戦略情報
    daily_bias VARCHAR(10) NOT NULL,
    confidence DECIMAL(4,3) CHECK (confidence >= 0 AND confidence <= 1),
    reasoning TEXT,

    -- 詳細分析結果（JSONB形式）
    market_environment JSONB,
    entry_conditions JSONB,
    exit_strategy JSONB,
    risk_management JSONB,
    key_levels JSONB,
    scenario_planning JSONB,
    lessons_applied JSONB,

    -- 市場データスナップショット
    market_data JSONB,

    -- メタデータ
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- ユニーク制約（1日1戦略）
    CONSTRAINT daily_strategies_unique UNIQUE (strategy_date, symbol)
);

-- インデックス作成
CREATE INDEX IF NOT EXISTS idx_strategies_date
    ON daily_strategies(strategy_date);
CREATE INDEX IF NOT EXISTS idx_strategies_symbol
    ON daily_strategies(symbol);
CREATE INDEX IF NOT EXISTS idx_strategies_bias
    ON daily_strategies(daily_bias);

COMMENT ON TABLE daily_strategies IS '朝の詳細分析結果（本番モード）';

-- マイグレーション完了
SELECT 'Migration 004: Daily strategies tables created successfully' AS status;
