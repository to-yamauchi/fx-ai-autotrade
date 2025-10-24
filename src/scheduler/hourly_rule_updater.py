"""
========================================
1時間毎ルール更新スケジューラー
========================================

ファイル名: hourly_rule_updater.py
パス: src/scheduler/hourly_rule_updater.py

【概要】
1時間毎に最新の市場データからトレードルールを生成し、DBに保存します。
トレード実行エンジンは常に最新のルールを参照して機械的に判断します。

【主な機能】
1. 1時間毎のトリガー（毎時00分）
2. 最新市場データの取得
3. AI分析によるルール生成
4. DBへのルール保存

【フロー】
毎時00分 → 市場データ取得 → AI分析 → 構造化ルール生成 → DB保存

【使用例】
```python
from src.scheduler import HourlyRuleUpdater

updater = HourlyRuleUpdater()
updater.start()  # バックグラウンドで1時間毎に実行
```

【作成日】2025-01-15
"""

from typing import Dict, Optional
from datetime import datetime, timedelta
import logging
import schedule
import time
import threading
import json
import psycopg2
from psycopg2.extras import Json
import os

from src.ai_analysis.ai_analyzer import AIAnalyzer
from src.data_processing.mt5_data_loader import MT5DataLoader


class HourlyRuleUpdater:
    """
    1時間毎にトレードルールを更新するスケジューラー

    AIが市場を分析し、構造化されたトレードルールを生成します。
    トレード実行エンジンは常にこのルールを参照して機械的に判断します。
    """

    def __init__(
        self,
        symbol: str = 'USDJPY',
        ai_model: str = 'gemini-2.0-flash-exp'
    ):
        """
        HourlyRuleUpdaterの初期化

        Args:
            symbol: 通貨ペア
            ai_model: 使用するAIモデル
        """
        self.symbol = symbol
        self.ai_model = ai_model
        self.logger = logging.getLogger(__name__)

        # コンポーネント初期化
        self.ai_analyzer = AIAnalyzer(default_model=ai_model)
        self.data_loader = MT5DataLoader()

        # DB接続情報
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'database': os.getenv('DB_NAME', 'fx_autotrade'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', ''),
            'client_encoding': 'UTF8'
        }

        # スケジューラー制御
        self.is_running = False
        self.scheduler_thread = None

        self.logger.info(
            f"HourlyRuleUpdater initialized: "
            f"symbol={symbol}, model={ai_model}"
        )

    def update_rule_now(self) -> bool:
        """
        今すぐルールを更新（手動実行用）

        Returns:
            成功したらTrue
        """
        try:
            self.logger.info("=== Hourly Rule Update Started ===")

            # 1. 最新市場データを取得
            market_data = self._get_latest_market_data()
            if not market_data:
                self.logger.error("Failed to get market data")
                return False

            # 2. AI分析でルール生成
            self.logger.info("Generating trading rule with AI...")
            rule = self._generate_rule(market_data)
            if not rule:
                self.logger.error("Failed to generate rule")
                return False

            # 3. ルールをDBに保存
            self.logger.info("Saving rule to database...")
            if not self._save_rule_to_db(rule):
                self.logger.error("Failed to save rule")
                return False

            self.logger.info(
                f"=== Rule Updated Successfully ===\n"
                f"  Bias: {rule.get('daily_bias')}\n"
                f"  Confidence: {rule.get('confidence')}\n"
                f"  Valid until: {rule.get('valid_until')}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Rule update failed: {e}", exc_info=True)
            return False

    def _get_latest_market_data(self) -> Optional[Dict]:
        """
        最新の市場データを取得

        Returns:
            市場データ辞書（複数時間足）
        """
        try:
            now = datetime.now()

            # 各時間足のデータを取得
            market_data = {
                'symbol': self.symbol,
                'timestamp': now.isoformat(),
            }

            # M15, H1, H4, D1のOHLC + インジケーターを取得
            timeframes = {
                'M15': 15,
                'H1': 60,
                'H4': 240,
                'D1': 1440
            }

            for tf_name, tf_minutes in timeframes.items():
                df = self.data_loader.load_ohlc(
                    symbol=self.symbol,
                    timeframe=tf_minutes,
                    num_candles=100  # 十分な履歴
                )

                if df is None or df.empty:
                    self.logger.warning(f"No data for {tf_name}")
                    continue

                # 最新のデータを取得
                latest = df.iloc[-1]

                market_data[tf_name] = {
                    'open': latest.get('open'),
                    'high': latest.get('high'),
                    'low': latest.get('low'),
                    'close': latest.get('close'),
                    'rsi': latest.get('rsi'),
                    'ema_20': latest.get('ema_20'),
                    'ema_50': latest.get('ema_50'),
                    'macd_line': latest.get('macd'),
                    'macd_signal': latest.get('macd_signal'),
                    'macd_histogram': latest.get('macd_hist'),
                }

                # 前の足のデータも追加（クロス判定用）
                if len(df) >= 2:
                    prev = df.iloc[-2]
                    market_data[tf_name]['prev_close'] = prev.get('close')
                    market_data[tf_name]['prev_macd_line'] = prev.get('macd')
                    market_data[tf_name]['prev_macd_signal'] = prev.get('macd_signal')

            # 現在価格
            market_data['current_price'] = market_data.get('M15', {}).get('close')

            # スプレッド（MT5から取得、または固定値）
            market_data['spread'] = 2.0  # TODO: MT5から実際のスプレッドを取得

            # 現在時刻
            market_data['current_time'] = now.strftime('%H:%M')

            return market_data

        except Exception as e:
            self.logger.error(f"Failed to get market data: {e}", exc_info=True)
            return None

    def _generate_rule(self, market_data: Dict) -> Optional[Dict]:
        """
        AI分析でトレードルールを生成

        Args:
            market_data: 市場データ

        Returns:
            構造化トレードルール
        """
        try:
            # TODO: ai_analyzer に新しいプロンプト（v2）を使用する処理を実装
            # 現時点では仮のルールを返す

            now = datetime.now()
            valid_until = now + timedelta(hours=1)

            # 仮の構造化ルール
            rule = {
                "version": "2.0",
                "generated_at": now.isoformat(),
                "valid_until": valid_until.isoformat(),
                "daily_bias": "BUY",
                "confidence": 0.70,
                "reasoning": "AI analysis based on current market conditions",
                "market_environment": {
                    "trend": "Ranging with slight upward bias",
                    "strength": "Medium",
                    "phase": "Consolidation"
                },
                "entry_conditions": {
                    "should_trade": True,
                    "direction": "BUY",
                    "price_zone": {
                        "min": market_data.get('current_price', 149.50) - 0.10,
                        "max": market_data.get('current_price', 149.50) + 0.10
                    },
                    "indicators": {
                        "rsi": {
                            "timeframe": "M15",
                            "min": 50,
                            "max": 70
                        },
                        "ema": {
                            "timeframe": "M15",
                            "condition": "price_above",
                            "period": 20
                        },
                        "macd": {
                            "timeframe": "M15",
                            "condition": "histogram_positive"
                        }
                    },
                    "spread": {
                        "max_pips": 10
                    },
                    "time_filter": {
                        "avoid_times": [
                            {"start": "09:50", "end": "10:00", "reason": "Tokyo fixing"}
                        ]
                    }
                },
                "exit_strategy": {
                    "take_profit": [
                        {"pips": 10, "close_percent": 30},
                        {"pips": 20, "close_percent": 40},
                        {"pips": 30, "close_percent": 100}
                    ],
                    "stop_loss": {
                        "initial_pips": 15,
                        "price_level": market_data.get('current_price', 149.50) - 0.15,
                        "trailing": {
                            "activate_at_pips": 15,
                            "trail_distance_pips": 10
                        }
                    },
                    "indicator_exits": [
                        {
                            "type": "macd_cross",
                            "timeframe": "M15",
                            "direction": "bearish",
                            "action": "close_50"
                        }
                    ],
                    "time_exits": {
                        "max_hold_minutes": 240,
                        "force_close_time": "23:00"
                    }
                },
                "risk_management": {
                    "position_size_multiplier": 0.8,
                    "max_positions": 1,
                    "max_risk_per_trade_percent": 2.0,
                    "max_total_exposure_percent": 4.0
                }
            }

            return rule

        except Exception as e:
            self.logger.error(f"Failed to generate rule: {e}", exc_info=True)
            return None

    def _save_rule_to_db(self, rule: Dict) -> bool:
        """
        ルールをDBに保存

        Args:
            rule: 構造化トレードルール

        Returns:
            成功したらTrue
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()

            # trade_rulesテーブルに保存
            insert_query = """
                INSERT INTO trade_rules (
                    symbol,
                    generated_at,
                    valid_until,
                    daily_bias,
                    confidence,
                    rule_json
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """

            cursor.execute(insert_query, (
                self.symbol,
                rule.get('generated_at'),
                rule.get('valid_until'),
                rule.get('daily_bias'),
                rule.get('confidence'),
                Json(rule)
            ))

            conn.commit()
            cursor.close()
            conn.close()

            self.logger.info(f"Rule saved to DB: {rule.get('generated_at')}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save rule to DB: {e}", exc_info=True)
            return False

    def start(self):
        """スケジューラーを開始（バックグラウンドスレッド）"""
        if self.is_running:
            self.logger.warning("Scheduler is already running")
            return

        self.is_running = True

        # 毎時00分に実行
        schedule.every().hour.at(":00").do(self.update_rule_now)

        # バックグラウンドスレッドで実行
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()

        self.logger.info("Hourly rule updater started (runs every hour at :00)")

    def _run_scheduler(self):
        """スケジューラーのメインループ"""
        while self.is_running:
            schedule.run_pending()
            time.sleep(60)  # 1分毎にチェック

    def stop(self):
        """スケジューラーを停止"""
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        self.logger.info("Hourly rule updater stopped")


# ユーティリティ関数
def get_latest_rule_from_db(symbol: str = 'USDJPY') -> Optional[Dict]:
    """
    DBから最新の有効なルールを取得

    Args:
        symbol: 通貨ペア

    Returns:
        最新のルール、または None
    """
    try:
        db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'database': os.getenv('DB_NAME', 'fx_autotrade'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', ''),
            'client_encoding': 'UTF8'
        }

        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        query = """
            SELECT rule_json
            FROM trade_rules
            WHERE symbol = %s
              AND valid_until > NOW()
            ORDER BY generated_at DESC
            LIMIT 1
        """

        cursor.execute(query, (symbol,))
        result = cursor.fetchone()

        cursor.close()
        conn.close()

        if result:
            return result[0]  # JSONB型なので直接辞書として返る
        return None

    except Exception as e:
        logging.error(f"Failed to get latest rule from DB: {e}")
        return None


# モジュールのエクスポート
__all__ = ['HourlyRuleUpdater', 'get_latest_rule_from_db']
