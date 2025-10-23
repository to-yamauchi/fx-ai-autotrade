-- ========================================
-- マイグレーション: ai_judgmentsテーブルにtimeframe列を追加
-- ========================================
--
-- 作成日: 2025-10-23
-- 理由: demo_ai_judgmentsとbacktest_ai_judgmentsとの整合性を保つため
-- ========================================

-- ai_judgmentsテーブルにtimeframe列を追加
ALTER TABLE ai_judgments
ADD COLUMN IF NOT EXISTS timeframe VARCHAR(10) NOT NULL DEFAULT 'MULTI';

-- デフォルト値を削除（今後はINSERT時に明示的に指定）
ALTER TABLE ai_judgments
ALTER COLUMN timeframe DROP DEFAULT;

-- コメント追加
COMMENT ON COLUMN ai_judgments.timeframe IS '分析時間足（MULTI: 複数時間足統合分析）';

-- 確認
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'ai_judgments'
ORDER BY ordinal_position;
