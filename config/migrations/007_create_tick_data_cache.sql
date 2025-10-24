-- ティックデータキャッシュテーブル
-- CSVから読み込んだティックデータを日付別にキャッシュして、次回の読み込みを高速化

CREATE TABLE IF NOT EXISTS tick_data_cache (
    symbol VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    bid DECIMAL(10, 5) NOT NULL,
    ask DECIMAL(10, 5) NOT NULL,
    spread DECIMAL(10, 5) GENERATED ALWAYS AS (ask - bid) STORED,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (symbol, date, timestamp)
);

-- 日付範囲検索用インデックス
CREATE INDEX IF NOT EXISTS idx_tick_cache_symbol_date
ON tick_data_cache (symbol, date);

-- タイムスタンプ検索用インデックス
CREATE INDEX IF NOT EXISTS idx_tick_cache_timestamp
ON tick_data_cache (timestamp);

-- テーブルコメント
COMMENT ON TABLE tick_data_cache IS 'CSVから読み込んだティックデータのキャッシュ。日付別に保存して高速読み込みを実現。';
COMMENT ON COLUMN tick_data_cache.symbol IS '通貨ペア (例: USDJPY)';
COMMENT ON COLUMN tick_data_cache.date IS 'ティックの日付（パーティションキー）';
COMMENT ON COLUMN tick_data_cache.timestamp IS 'ティックのタイムスタンプ';
COMMENT ON COLUMN tick_data_cache.bid IS 'ビッド価格';
COMMENT ON COLUMN tick_data_cache.ask IS 'アスク価格';
COMMENT ON COLUMN tick_data_cache.spread IS 'スプレッド（自動計算）';
COMMENT ON COLUMN tick_data_cache.created_at IS 'キャッシュ作成日時';

-- キャッシュ統計情報を取得するビュー
CREATE OR REPLACE VIEW tick_cache_stats AS
SELECT
    symbol,
    date,
    COUNT(*) as tick_count,
    MIN(timestamp) as first_tick,
    MAX(timestamp) as last_tick,
    AVG(spread) as avg_spread,
    created_at
FROM tick_data_cache
GROUP BY symbol, date, created_at
ORDER BY date DESC;

COMMENT ON VIEW tick_cache_stats IS 'ティックデータキャッシュの統計情報（日付別のティック数など）';
