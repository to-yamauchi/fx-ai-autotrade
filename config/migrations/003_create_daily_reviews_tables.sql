-- ========================================
-- Daily Reviews Tables Creation
-- ========================================
--
-- Purpose: Store AI-generated daily reviews for backtest and demo modes
-- Created: 2025-10-23
-- ========================================

-- ========================================
-- Backtest Daily Reviews Table
-- ========================================

CREATE TABLE IF NOT EXISTS backtest_daily_reviews (
    id SERIAL PRIMARY KEY,
    review_date DATE NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    total_score VARCHAR(20),  -- e.g., "88/100点"
    score_breakdown JSONB,     -- Detailed scores (direction, entry, exit, risk)
    analysis JSONB,            -- what_worked, what_failed, missed_signals
    lessons JSONB,             -- lessons_for_today array
    patterns JSONB,            -- success_patterns and failure_patterns
    trades_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Backtest identification
    backtest_start_date DATE,
    backtest_end_date DATE,

    -- Unique constraint
    CONSTRAINT backtest_daily_reviews_unique UNIQUE (review_date, symbol, backtest_start_date, backtest_end_date)
);

-- Index for query performance
CREATE INDEX IF NOT EXISTS idx_backtest_reviews_date ON backtest_daily_reviews(review_date);
CREATE INDEX IF NOT EXISTS idx_backtest_reviews_symbol ON backtest_daily_reviews(symbol);

-- ========================================
-- Demo Daily Reviews Table
-- ========================================

CREATE TABLE IF NOT EXISTS demo_daily_reviews (
    id SERIAL PRIMARY KEY,
    review_date DATE NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    total_score VARCHAR(20),  -- e.g., "88/100点"
    score_breakdown JSONB,     -- Detailed scores (direction, entry, exit, risk)
    analysis JSONB,            -- what_worked, what_failed, missed_signals
    lessons JSONB,             -- lessons_for_today array
    patterns JSONB,            -- success_patterns and failure_patterns
    trades_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Unique constraint
    CONSTRAINT demo_daily_reviews_unique UNIQUE (review_date, symbol)
);

-- Index for query performance
CREATE INDEX IF NOT EXISTS idx_demo_reviews_date ON demo_daily_reviews(review_date);
CREATE INDEX IF NOT EXISTS idx_demo_reviews_symbol ON demo_daily_reviews(symbol);

-- ========================================
-- Live Daily Reviews Table
-- ========================================

CREATE TABLE IF NOT EXISTS daily_reviews (
    id SERIAL PRIMARY KEY,
    review_date DATE NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    total_score VARCHAR(20),  -- e.g., "88/100点"
    score_breakdown JSONB,     -- Detailed scores (direction, entry, exit, risk)
    analysis JSONB,            -- what_worked, what_failed, missed_signals
    lessons JSONB,             -- lessons_for_today array
    patterns JSONB,            -- success_patterns and failure_patterns
    trades_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Unique constraint
    CONSTRAINT daily_reviews_unique UNIQUE (review_date, symbol)
);

-- Index for query performance
CREATE INDEX IF NOT EXISTS idx_reviews_date ON daily_reviews(review_date);
CREATE INDEX IF NOT EXISTS idx_reviews_symbol ON daily_reviews(symbol);

-- ========================================
-- Example Queries
-- ========================================

-- Get today's review
-- SELECT * FROM backtest_daily_reviews WHERE review_date = CURRENT_DATE;

-- Get recent reviews
-- SELECT review_date, symbol, total_score, trades_count
-- FROM backtest_daily_reviews
-- ORDER BY review_date DESC
-- LIMIT 7;

-- Get lessons from past week
-- SELECT review_date, lessons
-- FROM backtest_daily_reviews
-- WHERE review_date >= CURRENT_DATE - INTERVAL '7 days'
-- ORDER BY review_date DESC;

-- Get success patterns
-- SELECT review_date, patterns->'success_patterns' as success_patterns
-- FROM backtest_daily_reviews
-- WHERE patterns->'success_patterns' IS NOT NULL
-- ORDER BY review_date DESC;
