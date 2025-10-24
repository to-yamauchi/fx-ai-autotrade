-- ========================================
-- トレードルールテーブル作成
-- ========================================
--
-- ファイル名: 010_create_trade_rules_table.sql
-- パス: config/migrations/010_create_trade_rules_table.sql
--
-- 【概要】
-- 1時間毎にAIが生成する構造化トレードルールを保存するテーブル。
-- トレード実行エンジンは常に最新の有効なルールを参照して機械的に判断します。
--
-- 【テーブル】
-- - trade_rules: 構造化トレードルール（本番用）
--
-- 【作成日】2025-01-15
-- ========================================

-- ========================================
-- 1. trade_rulesテーブル
-- ========================================

CREATE TABLE IF NOT EXISTS trade_rules (
    -- 基本情報
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    generated_at TIMESTAMP NOT NULL,
    valid_until TIMESTAMP NOT NULL,

    -- ルール概要
    daily_bias VARCHAR(10),  -- BUY, SELL, NEUTRAL
    confidence DECIMAL(4,3) CHECK (confidence >= 0 AND confidence <= 1),

    -- 構造化ルールJSON（完全な構造化データ）
    rule_json JSONB NOT NULL,

    -- メタデータ
    created_at TIMESTAMP DEFAULT NOW(),

    -- インデックス
    CONSTRAINT valid_daily_bias CHECK (daily_bias IN ('BUY', 'SELL', 'NEUTRAL'))
);

-- インデックス作成
CREATE INDEX idx_trade_rules_symbol_valid
    ON trade_rules(symbol, valid_until DESC, generated_at DESC);

CREATE INDEX idx_trade_rules_generated_at
    ON trade_rules(generated_at DESC);

-- GIN インデックス（JSONB検索用）
CREATE INDEX idx_trade_rules_rule_json
    ON trade_rules USING GIN (rule_json);

-- テーブルコメント
COMMENT ON TABLE trade_rules IS '1時間毎にAIが生成する構造化トレードルール';
COMMENT ON COLUMN trade_rules.symbol IS '通貨ペア';
COMMENT ON COLUMN trade_rules.generated_at IS 'ルール生成日時';
COMMENT ON COLUMN trade_rules.valid_until IS 'ルール有効期限';
COMMENT ON COLUMN trade_rules.daily_bias IS '本日のバイアス（BUY/SELL/NEUTRAL）';
COMMENT ON COLUMN trade_rules.confidence IS '確信度（0.000-1.000）';
COMMENT ON COLUMN trade_rules.rule_json IS '構造化トレードルール（完全なJSON）';

-- ========================================
-- 2. サンプルデータ挿入（テスト用）
-- ========================================

-- サンプルルールを挿入（開発・テスト用）
INSERT INTO trade_rules (
    symbol,
    generated_at,
    valid_until,
    daily_bias,
    confidence,
    rule_json
) VALUES (
    'USDJPY',
    NOW(),
    NOW() + INTERVAL '1 hour',
    'BUY',
    0.75,
    '{
        "version": "2.0",
        "generated_at": "2025-01-15T08:00:00Z",
        "valid_until": "2025-01-15T09:00:00Z",
        "daily_bias": "BUY",
        "confidence": 0.75,
        "reasoning": "Sample rule for testing",
        "entry_conditions": {
            "should_trade": true,
            "direction": "BUY",
            "price_zone": {"min": 149.50, "max": 149.65},
            "indicators": {
                "rsi": {"timeframe": "M15", "min": 50, "max": 70},
                "ema": {"timeframe": "M15", "condition": "price_above", "period": 20},
                "macd": {"timeframe": "M15", "condition": "histogram_positive"}
            },
            "spread": {"max_pips": 10},
            "time_filter": {"avoid_times": []}
        },
        "exit_strategy": {
            "take_profit": [
                {"pips": 10, "close_percent": 30},
                {"pips": 20, "close_percent": 40},
                {"pips": 30, "close_percent": 100}
            ],
            "stop_loss": {
                "initial_pips": 15,
                "price_level": 149.40,
                "trailing": {"activate_at_pips": 15, "trail_distance_pips": 10}
            },
            "indicator_exits": [],
            "time_exits": {"max_hold_minutes": 240, "force_close_time": "23:00"}
        },
        "risk_management": {
            "position_size_multiplier": 0.8,
            "max_positions": 1,
            "max_risk_per_trade_percent": 2.0,
            "max_total_exposure_percent": 4.0
        }
    }'::jsonb
);

-- ========================================
-- 3. クリーンアップクエリ（古いルール削除）
-- ========================================

-- 古い期限切れルールを削除するクエリ（手動実行用）
-- DELETE FROM trade_rules WHERE valid_until < NOW() - INTERVAL '7 days';

-- ========================================
-- 完了
-- ========================================

SELECT 'Trade rules table created successfully!' AS status;
