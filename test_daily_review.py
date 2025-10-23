"""
Daily Review Function Test Script

このスクリプトはAIAnalyzerのdaily_review()メソッドをテストします。
サンプルデータを使用して振り返り機能を確認できます。

実行方法:
    python test_daily_review.py

必要な環境:
    - .envファイルにGEMINI_API_KEYが設定されていること
    - PostgreSQLが起動していること
    - daily_reviews系テーブルが作成されていること
"""

import logging
import sys
from datetime import datetime, timedelta

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main():
    """メイン処理"""
    logger.info("=" * 80)
    logger.info("Daily Review Function Test")
    logger.info("=" * 80)
    logger.info("")

    try:
        # AIAnalyzerインポート
        from src.ai_analysis.ai_analyzer import AIAnalyzer

        # AIAnalyzer初期化
        logger.info("Initializing AIAnalyzer...")
        analyzer = AIAnalyzer(
            symbol='USDJPY',
            model='flash',
            backtest_start_date='2024-09-01',
            backtest_end_date='2024-09-30'
        )
        logger.info("AIAnalyzer initialized successfully")
        logger.info("")

        # サンプルデータ: 前日のトレード結果
        logger.info("Preparing sample trade data...")
        previous_trades = [
            {
                'entry_time': '2024-09-20 10:30:00',
                'exit_time': '2024-09-20 14:15:00',
                'direction': 'BUY',
                'entry_price': 149.60,
                'exit_price': 149.75,
                'pips': 15,
                'profit_loss': 7500,
                'exit_reason': 'take_profit_level_2'
            },
            {
                'entry_time': '2024-09-20 16:00:00',
                'exit_time': '2024-09-20 18:30:00',
                'direction': 'SELL',
                'entry_price': 149.80,
                'exit_price': 149.85,
                'pips': -5,
                'profit_loss': -2500,
                'exit_reason': 'stop_loss'
            }
        ]

        # サンプルデータ: 前日の予測
        prediction = {
            'daily_bias': 'BUY',
            'confidence': 0.75,
            'reasoning': 'H1足でEMA20>EMA50の強気配列が継続。RSI 45と中立圏。'
        }

        # サンプルデータ: 実際の市場動向
        actual_market = {
            'high': 149.85,
            'low': 149.45,
            'close': 149.72,
            'direction': '上昇',
            'volatility': '中程度'
        }

        # サンプルデータ: 統計情報
        statistics = {
            'total_pips': 10,
            'win_rate': '50%',
            'max_drawdown': '-5pips',
            'total_trades': 2,
            'win_trades': 1,
            'loss_trades': 1
        }

        logger.info(f"Sample data prepared: {len(previous_trades)} trades")
        logger.info("")

        # 振り返り実行
        logger.info("Executing daily review with Gemini Pro...")
        logger.info("This may take 5-10 seconds...")
        logger.info("")

        review_result = analyzer.daily_review(
            previous_day_trades=previous_trades,
            prediction=prediction,
            actual_market=actual_market,
            statistics=statistics
        )

        logger.info("")
        logger.info("=" * 80)
        logger.info("Review Result")
        logger.info("=" * 80)
        logger.info("")

        # 結果表示
        logger.info(f"Total Score: {review_result.get('score', {}).get('total', 'N/A')}")
        logger.info(f"Comment: {review_result.get('score', {}).get('comment', 'N/A')}")
        logger.info("")

        # スコア詳細
        score_breakdown = review_result.get('score', {})
        logger.info("Score Breakdown:")
        logger.info(f"  Direction: {score_breakdown.get('direction', 'N/A')}")
        logger.info(f"  Entry Timing: {score_breakdown.get('entry_timing', 'N/A')}")
        logger.info(f"  Exit Timing: {score_breakdown.get('exit_timing', 'N/A')}")
        logger.info(f"  Risk Management: {score_breakdown.get('risk_management', 'N/A')}")
        logger.info("")

        # 分析結果
        analysis = review_result.get('analysis', {})
        logger.info("What Worked:")
        for item in analysis.get('what_worked', []):
            logger.info(f"  ✓ {item}")
        logger.info("")

        logger.info("What Failed:")
        for item in analysis.get('what_failed', []):
            logger.info(f"  ✗ {item}")
        logger.info("")

        logger.info("Missed Signals:")
        for item in analysis.get('missed_signals', []):
            logger.info(f"  ! {item}")
        logger.info("")

        # 今日への教訓
        logger.info("Lessons for Today:")
        for i, lesson in enumerate(review_result.get('lessons_for_today', []), 1):
            logger.info(f"  {i}. {lesson}")
        logger.info("")

        # パターン認識
        patterns = review_result.get('pattern_recognition', {})
        logger.info("Success Patterns:")
        for pattern in patterns.get('success_patterns', []):
            logger.info(f"  ✓ {pattern}")
        logger.info("")

        logger.info("Failure Patterns:")
        for pattern in patterns.get('failure_patterns', []):
            logger.info(f"  ✗ {pattern}")
        logger.info("")

        # エラーチェック
        if 'error' in review_result:
            logger.error(f"Review completed with error: {review_result['error']}")
            logger.info("")
            return 1

        logger.info("=" * 80)
        logger.info("Test completed successfully!")
        logger.info("=" * 80)
        logger.info("")
        logger.info("Check the database for saved results:")
        logger.info("  SELECT * FROM backtest_daily_reviews ORDER BY created_at DESC LIMIT 1;")
        logger.info("")

        return 0

    except KeyboardInterrupt:
        logger.info("")
        logger.info("Test interrupted by user")
        return 130

    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
