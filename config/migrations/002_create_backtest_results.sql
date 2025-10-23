-- ================================
-- バックテスト結果テーブル作成
-- ================================
--
-- ファイル名: 002_create_backtest_results.sql
-- パス: config/migrations/002_create_backtest_results.sql
--
-- 【概要】
-- バックテスト結果を保存するテーブルを作成します。
--
-- 【実行方法】
-- psql -U postgres -d fx_autotrade -f config/migrations/002_create_backtest_results.sql
--
-- 【作成日】2025-10-23

-- バックテスト結果テーブル
CREATE TABLE IF NOT EXISTS backtest_results (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    ai_model VARCHAR(20) NOT NULL,

    -- 残高・損益
    initial_balance NUMERIC(15, 2) NOT NULL,
    final_balance NUMERIC(15, 2) NOT NULL,
    net_profit NUMERIC(15, 2) NOT NULL,
    return_pct NUMERIC(10, 2) NOT NULL,

    -- トレード統計
    total_trades INTEGER NOT NULL,
    winning_trades INTEGER NOT NULL,
    losing_trades INTEGER NOT NULL,
    win_rate NUMERIC(5, 2) NOT NULL,

    -- 損益詳細
    total_profit NUMERIC(15, 2) NOT NULL,
    total_loss NUMERIC(15, 2) NOT NULL,
    profit_factor NUMERIC(10, 2) NOT NULL,

    -- リスク指標
    max_drawdown NUMERIC(15, 2) NOT NULL,
    max_drawdown_pct NUMERIC(5, 2) NOT NULL,

    -- 詳細統計（JSON）
    statistics JSONB,

    -- メタデータ
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- インデックス用
    CONSTRAINT unique_backtest UNIQUE (symbol, start_date, end_date, ai_model, created_at)
);

-- コメント追加
COMMENT ON TABLE backtest_results IS 'バックテスト結果を保存するテーブル';
COMMENT ON COLUMN backtest_results.id IS 'バックテストID';
COMMENT ON COLUMN backtest_results.symbol IS '通貨ペア';
COMMENT ON COLUMN backtest_results.start_date IS 'バックテスト開始日';
COMMENT ON COLUMN backtest_results.end_date IS 'バックテスト終了日';
COMMENT ON COLUMN backtest_results.ai_model IS '使用したAIモデル';
COMMENT ON COLUMN backtest_results.initial_balance IS '初期残高';
COMMENT ON COLUMN backtest_results.final_balance IS '最終残高';
COMMENT ON COLUMN backtest_results.net_profit IS '純利益';
COMMENT ON COLUMN backtest_results.return_pct IS 'リターン率（%）';
COMMENT ON COLUMN backtest_results.total_trades IS '総トレード数';
COMMENT ON COLUMN backtest_results.winning_trades IS '勝ちトレード数';
COMMENT ON COLUMN backtest_results.losing_trades IS '負けトレード数';
COMMENT ON COLUMN backtest_results.win_rate IS '勝率（%）';
COMMENT ON COLUMN backtest_results.total_profit IS '総利益';
COMMENT ON COLUMN backtest_results.total_loss IS '総損失';
COMMENT ON COLUMN backtest_results.profit_factor IS 'プロフィットファクター';
COMMENT ON COLUMN backtest_results.max_drawdown IS '最大ドローダウン（金額）';
COMMENT ON COLUMN backtest_results.max_drawdown_pct IS '最大ドローダウン（%）';
COMMENT ON COLUMN backtest_results.statistics IS '詳細統計情報（JSON）';
COMMENT ON COLUMN backtest_results.created_at IS '作成日時';

-- インデックス作成
CREATE INDEX IF NOT EXISTS idx_backtest_symbol ON backtest_results(symbol);
CREATE INDEX IF NOT EXISTS idx_backtest_date ON backtest_results(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_backtest_model ON backtest_results(ai_model);
CREATE INDEX IF NOT EXISTS idx_backtest_created ON backtest_results(created_at DESC);

-- サマリービュー作成
CREATE OR REPLACE VIEW backtest_summary AS
SELECT
    id,
    symbol,
    start_date,
    end_date,
    ai_model,
    initial_balance,
    final_balance,
    net_profit,
    return_pct,
    total_trades,
    win_rate,
    profit_factor,
    max_drawdown_pct,
    created_at,
    -- パフォーマンス評価
    CASE
        WHEN return_pct >= 10 AND win_rate >= 60 AND profit_factor >= 2.0 THEN '優秀'
        WHEN return_pct >= 5 AND win_rate >= 50 AND profit_factor >= 1.5 THEN '良好'
        WHEN return_pct >= 0 AND win_rate >= 40 AND profit_factor >= 1.0 THEN '普通'
        ELSE '要改善'
    END AS performance_rating
FROM backtest_results
ORDER BY created_at DESC;

COMMENT ON VIEW backtest_summary IS 'バックテスト結果のサマリービュー';

-- 権限設定
GRANT SELECT, INSERT ON backtest_results TO PUBLIC;
GRANT SELECT ON backtest_summary TO PUBLIC;
