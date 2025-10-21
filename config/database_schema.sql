-- ========================================
-- FX自動トレードシステム データベーススキーマ
-- ========================================
-- ファイル名: database_schema.sql
-- 説明: PostgreSQLデータベースのテーブル定義
-- 作成日: 2025-10-21
-- ========================================

-- データベース作成（必要に応じて実行）
-- CREATE DATABASE fx_autotrade;

-- ========================================
-- ティックデータテーブル
-- ========================================
-- 用途: MT5から取得した生のティックデータを保存
-- 保存内容: タイムスタンプ、通貨ペア、Bid/Ask価格、出来高
CREATE TABLE IF NOT EXISTS tick_data (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,           -- 通貨ペア（例: USDJPY）
    timestamp TIMESTAMP NOT NULL,          -- ティック発生時刻
    bid DECIMAL(10, 5) NOT NULL,          -- Bid価格
    ask DECIMAL(10, 5) NOT NULL,          -- Ask価格
    volume INTEGER,                        -- 出来高
    UNIQUE(symbol, timestamp)              -- 重複データ防止
);

-- インデックス作成（検索高速化）
CREATE INDEX IF NOT EXISTS idx_tick_timestamp ON tick_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_tick_symbol_timestamp ON tick_data(symbol, timestamp);

COMMENT ON TABLE tick_data IS 'MT5から取得した生のティックデータ';
COMMENT ON COLUMN tick_data.symbol IS '通貨ペア（例: USDJPY）';
COMMENT ON COLUMN tick_data.timestamp IS 'ティック発生時刻（UTC）';
COMMENT ON COLUMN tick_data.bid IS 'Bid価格（売値）';
COMMENT ON COLUMN tick_data.ask IS 'Ask価格（買値）';
COMMENT ON COLUMN tick_data.volume IS '出来高';

-- ========================================
-- 時間足データテーブル
-- ========================================
-- 用途: ティックデータから生成したOHLCVデータを保存
-- 時間足: D1, H4, H1, M15
CREATE TABLE IF NOT EXISTS timeframe_data (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,           -- 通貨ペア
    timeframe VARCHAR(5) NOT NULL,         -- 時間足（D1/H4/H1/M15）
    timestamp TIMESTAMP NOT NULL,          -- 足の開始時刻
    open DECIMAL(10, 5) NOT NULL,         -- 始値
    high DECIMAL(10, 5) NOT NULL,         -- 高値
    low DECIMAL(10, 5) NOT NULL,          -- 安値
    close DECIMAL(10, 5) NOT NULL,        -- 終値
    volume INTEGER,                        -- 出来高
    UNIQUE(symbol, timeframe, timestamp)   -- 重複データ防止
);

-- インデックス作成
CREATE INDEX IF NOT EXISTS idx_timeframe_timestamp ON timeframe_data(symbol, timeframe, timestamp);

COMMENT ON TABLE timeframe_data IS 'ティックデータから生成したOHLCVデータ';
COMMENT ON COLUMN timeframe_data.timeframe IS '時間足（D1: 日足, H4: 4時間足, H1: 1時間足, M15: 15分足）';
COMMENT ON COLUMN timeframe_data.open IS '始値';
COMMENT ON COLUMN timeframe_data.high IS '高値';
COMMENT ON COLUMN timeframe_data.low IS '安値';
COMMENT ON COLUMN timeframe_data.close IS '終値';

-- ========================================
-- AIトレード判断テーブル
-- ========================================
-- 用途: Gemini APIによるトレード判断結果を保存
-- 保存内容: 判断時刻、アクション、信頼度、判断理由
CREATE TABLE IF NOT EXISTS ai_judgments (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,          -- 判断時刻
    symbol VARCHAR(10) NOT NULL,           -- 通貨ペア
    action VARCHAR(10) NOT NULL,           -- アクション（BUY/SELL/HOLD）
    confidence DECIMAL(5, 2),              -- 信頼度（0-100）
    reasoning TEXT,                        -- 判断理由
    market_data JSONB,                     -- 判断時のマーケットデータ（JSON形式）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- インデックス作成
CREATE INDEX IF NOT EXISTS idx_ai_judgments_timestamp ON ai_judgments(timestamp);
CREATE INDEX IF NOT EXISTS idx_ai_judgments_symbol ON ai_judgments(symbol);

COMMENT ON TABLE ai_judgments IS 'Gemini APIによるAIトレード判断結果';
COMMENT ON COLUMN ai_judgments.action IS 'トレードアクション（BUY: 買い, SELL: 売り, HOLD: 待機）';
COMMENT ON COLUMN ai_judgments.confidence IS '判断の信頼度（0-100%）';
COMMENT ON COLUMN ai_judgments.reasoning IS 'AIの判断理由（テキスト）';
COMMENT ON COLUMN ai_judgments.market_data IS '判断時のマーケットデータ（JSONB形式）';

-- ========================================
-- ポジションテーブル
-- ========================================
-- 用途: オープン中および決済済みのポジション情報を管理
-- 保存内容: チケット番号、エントリー/決済価格、損益など
CREATE TABLE IF NOT EXISTS positions (
    id BIGSERIAL PRIMARY KEY,
    ticket BIGINT UNIQUE,                  -- MT5チケット番号
    symbol VARCHAR(10) NOT NULL,           -- 通貨ペア
    type VARCHAR(10) NOT NULL,             -- ポジションタイプ（BUY/SELL）
    volume DECIMAL(10, 2) NOT NULL,       -- ロット数
    open_price DECIMAL(10, 5) NOT NULL,   -- エントリー価格
    sl DECIMAL(10, 5),                    -- ストップロス
    tp DECIMAL(10, 5),                    -- テイクプロフィット
    open_time TIMESTAMP NOT NULL,          -- オープン時刻
    close_time TIMESTAMP,                  -- クローズ時刻
    close_price DECIMAL(10, 5),           -- 決済価格
    profit DECIMAL(10, 2),                -- 損益
    status VARCHAR(20) NOT NULL           -- ステータス（OPEN/CLOSED）
);

-- インデックス作成
CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status);
CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol);
CREATE INDEX IF NOT EXISTS idx_positions_open_time ON positions(open_time);

COMMENT ON TABLE positions IS 'オープン中および決済済みのポジション情報';
COMMENT ON COLUMN positions.ticket IS 'MT5のチケット番号（一意）';
COMMENT ON COLUMN positions.type IS 'ポジションタイプ（BUY: 買い, SELL: 売り）';
COMMENT ON COLUMN positions.volume IS 'ロット数（取引量）';
COMMENT ON COLUMN positions.sl IS 'ストップロス価格（損切り価格）';
COMMENT ON COLUMN positions.tp IS 'テイクプロフィット価格（利確価格）';
COMMENT ON COLUMN positions.status IS 'ポジションステータス（OPEN: オープン中, CLOSED: 決済済み）';

-- ========================================
-- バックテスト結果テーブル
-- ========================================
-- 用途: バックテスト実行結果を保存・分析
-- 保存内容: テスト期間、トレード数、勝率、方向性精度など
CREATE TABLE IF NOT EXISTS backtest_results (
    id BIGSERIAL PRIMARY KEY,
    test_name VARCHAR(100) NOT NULL,       -- テスト名
    start_date DATE NOT NULL,              -- テスト開始日
    end_date DATE NOT NULL,                -- テスト終了日
    total_trades INTEGER,                  -- 総トレード数
    win_rate DECIMAL(5, 2),               -- 勝率
    direction_accuracy DECIMAL(5, 2),     -- 方向性精度（目標60%以上）
    judgment_consistency DECIMAL(5, 2),   -- 判断の一貫性（目標85%以上）
    profit_factor DECIMAL(10, 2),         -- プロフィットファクター
    max_drawdown DECIMAL(10, 2),          -- 最大ドローダウン
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- インデックス作成
CREATE INDEX IF NOT EXISTS idx_backtest_created_at ON backtest_results(created_at);

COMMENT ON TABLE backtest_results IS 'バックテスト実行結果';
COMMENT ON COLUMN backtest_results.test_name IS 'バックテストの識別名';
COMMENT ON COLUMN backtest_results.direction_accuracy IS 'AIの方向性予測精度（目標60%以上）';
COMMENT ON COLUMN backtest_results.judgment_consistency IS 'AIの判断一貫性（目標85%以上）';
COMMENT ON COLUMN backtest_results.profit_factor IS '総利益/総損失の比率';
COMMENT ON COLUMN backtest_results.max_drawdown IS '最大ドローダウン（最大損失）';
