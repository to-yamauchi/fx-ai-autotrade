-- ================================
-- バックテストトレードテーブル: exit_reasonカラム長の拡張
-- ================================
--
-- ファイル名: 009_extend_backtest_trades_exit_reason.sql
-- パス: config/migrations/009_extend_backtest_trades_exit_reason.sql
--
-- 【概要】
-- backtest_tradesテーブルのexit_reasonカラムの長さをVARCHAR(100)からVARCHAR(500)に拡張します。
-- 日本語の決済理由が長くなる可能性があるため、より長い制限に変更します。
--
-- 【実行方法】
-- psql -U postgres -d fx_autotrade -f config/migrations/009_extend_backtest_trades_exit_reason.sql
--
-- 【作成日】2025-01-26

-- exit_reasonカラムの型を変更
ALTER TABLE backtest_trades
ALTER COLUMN exit_reason TYPE VARCHAR(500);

-- 変更を確認
COMMENT ON COLUMN backtest_trades.exit_reason IS '決済理由（最大500文字）';
