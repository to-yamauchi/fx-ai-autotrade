"""
========================================
AI分析オーケストレーターモジュール
========================================

ファイル名: ai_analyzer.py
パス: src/ai_analysis/ai_analyzer.py

【概要】
AI分析の全体フローを管理するオーケストレーターモジュールです。
データ読み込み、変換、テクニカル指標計算、AI分析、結果保存までの
一連の処理を統合管理します。

【主な機能】
1. 分析フロー全体の統合管理
2. データパイプライン実行
3. AI判断結果のDB保存
4. エラーハンドリングとログ記録

【処理フロー】
1. ティックデータの読み込み
2. 時間足変換（D1/H4/H1/M15）
3. テクニカル指標計算（EMA/RSI/MACD/ATR/BB/SR）
4. データ標準化（JSON形式）
5. Gemini API呼び出し
6. 判断結果のDB保存

【使用例】
```python
analyzer = AIAnalyzer(symbol='USDJPY')
result = analyzer.analyze_market()
print(f"Action: {result['action']}, Confidence: {result['confidence']}%")
```

【作成日】2025-10-22
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import Json
import os

from src.data_processing.tick_loader import TickDataLoader
from src.data_processing.mt5_data_loader import MT5DataLoader
from src.data_processing.timeframe_converter import TimeframeConverter
from src.data_processing.technical_indicators import TechnicalIndicators
from src.data_processing.data_standardizer import DataStandardizer
from src.ai_analysis.gemini_client import GeminiClient
from src.utils.trade_mode import get_trade_mode_config


class AIAnalyzer:
    """
    AI分析オーケストレータークラス

    マーケット分析の全フローを統合管理し、AI判断を実行します。
    """

    def __init__(self,
                 symbol: str = 'USDJPY',
                 data_dir: str = 'data/tick_data',
                 model: str = 'flash',
                 backtest_start_date: Optional[str] = None,
                 backtest_end_date: Optional[str] = None):
        """
        AIAnalyzerの初期化

        Args:
            symbol: 通貨ペア（デフォルト: USDJPY）
            data_dir: ティックデータディレクトリ
            model: 使用するGeminiモデル ('pro'/'flash'/'flash-lite')
            backtest_start_date: バックテスト開始日 (YYYY-MM-DD), バックテストモード時のみ
            backtest_end_date: バックテスト終了日 (YYYY-MM-DD), バックテストモード時のみ
        """
        self.symbol = symbol
        self.data_dir = data_dir
        self.model = model
        self.backtest_start_date = backtest_start_date
        self.backtest_end_date = backtest_end_date
        self.logger = logging.getLogger(__name__)

        # トレードモード設定の取得
        self.mode_config = get_trade_mode_config()
        self.table_names = self.mode_config.get_table_names()

        # 各コンポーネントの初期化
        self.tick_loader = TickDataLoader(data_dir=data_dir)
        self.mt5_loader = MT5DataLoader(symbol=symbol)
        self.timeframe_converter = TimeframeConverter()
        self.technical_indicators = TechnicalIndicators()
        self.data_standardizer = DataStandardizer()
        self.gemini_client = GeminiClient()

        # DB接続情報
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'database': os.getenv('DB_NAME', 'fx_autotrade'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', ''),
            'client_encoding': 'UTF8'
        }

        self.logger.info(
            f"AIAnalyzer initialized for {symbol} with {model} model "
            f"(mode: {self.mode_config.get_mode().value})"
        )

    def analyze_market(self,
                      year: Optional[int] = None,
                      month: Optional[int] = None,
                      lookback_days: int = 60) -> Dict:
        """
        マーケットを分析してトレード判断を実行

        Args:
            year: データ年（Noneの場合は現在）
            month: データ月（Noneの場合は現在）
            lookback_days: 分析に使用する過去日数

        Returns:
            AI判断結果の辞書
            {
                'action': 'BUY' | 'SELL' | 'HOLD',
                'confidence': 0-100,
                'reasoning': '判断理由',
                'timestamp': '分析実行時刻',
                'symbol': '通貨ペア',
                ...
            }
        """
        try:
            self.logger.info(f"Starting market analysis for {self.symbol}...")

            # 1. ティックデータの読み込み
            tick_data = self._load_tick_data(year, month)
            if not tick_data:
                return self._create_error_result("Failed to load tick data")

            self.logger.info(f"Loaded {len(tick_data)} ticks")

            # 2. 時間足変換
            timeframe_data = self._convert_timeframes(tick_data)
            if not timeframe_data:
                return self._create_error_result("Failed to convert timeframes")

            self.logger.info("Timeframe conversion completed")

            # 3. テクニカル指標計算
            indicators = self._calculate_indicators(timeframe_data)
            if not indicators:
                return self._create_error_result("Failed to calculate indicators")

            self.logger.info("Technical indicators calculated")

            # 4. データ標準化
            standardized_data = self.data_standardizer.standardize_for_ai(
                timeframe_data=timeframe_data,
                indicators=indicators
            )
            standardized_data['symbol'] = self.symbol

            self.logger.info("Data standardization completed")

            # 5. AI分析実行
            ai_result = self.gemini_client.analyze_market(
                market_data=standardized_data,
                model=self.model
            )

            # 6. 結果にメタデータを追加
            ai_result['timestamp'] = datetime.now().isoformat()
            ai_result['symbol'] = self.symbol
            ai_result['model'] = self.model

            self.logger.info(
                f"AI Analysis completed: {ai_result['action']} "
                f"(confidence: {ai_result.get('confidence', 0)}%)"
            )

            # 7. 結果をDBに保存
            self._save_to_database(ai_result, standardized_data)

            return ai_result

        except Exception as e:
            self.logger.error(f"Market analysis error: {e}", exc_info=True)
            return self._create_error_result(str(e))

    def _load_tick_data(self,
                       year: Optional[int] = None,
                       month: Optional[int] = None) -> List[Dict]:
        """
        ティックデータを読み込む（モード別）

        Args:
            year: データ年（backtestモード時）
            month: データ月（backtestモード時）

        Returns:
            ティックデータのリスト
        """
        try:
            # モード別にデータソースを切り替え
            if self.mode_config.is_backtest():
                # バックテストモード: data/tick_dataから読み込み
                start_date, end_date = self.mode_config.get_backtest_period()

                self.logger.info(
                    f"Loading backtest data: {start_date.date()} to {end_date.date()}"
                )

                tick_data = self.tick_loader.load_date_range(
                    symbol=self.symbol,
                    start_date=start_date,
                    end_date=end_date
                )

                # データ検証
                if not self.tick_loader.validate_data(tick_data):
                    self.logger.error("Tick data validation failed")
                    return []

            else:
                # DEMO/本番モード: MT5からリアルタイムデータを取得
                self.logger.info(
                    f"Loading real-time data from MT5 (last 30 days)"
                )

                # DataFrameを取得
                df = self.mt5_loader.load_recent_ticks(days=30)

                # DataFrameをList[Dict]形式に変換
                tick_data = df.to_dict('records')

                # データ検証
                if not self.mt5_loader.validate_data(df):
                    self.logger.error("MT5 tick data validation failed")
                    return []

            return tick_data

        except Exception as e:
            self.logger.error(f"Failed to load tick data: {e}")
            return []

    def _convert_timeframes(self, tick_data: List[Dict]) -> Dict:
        """
        ティックデータを複数の時間足に変換

        Args:
            tick_data: ティックデータ

        Returns:
            時間足データの辞書 {'D1': df, 'H4': df, 'H1': df, 'M15': df}
        """
        try:
            timeframes = {}

            for tf in ['D1', 'H4', 'H1', 'M15']:
                df = self.timeframe_converter.convert(
                    tick_data=tick_data,
                    timeframe=tf
                )

                if df is not None and not df.empty:
                    timeframes[tf] = df
                    self.logger.debug(f"{tf}: {len(df)} candles generated")
                else:
                    self.logger.warning(f"{tf}: No candles generated")

            return timeframes

        except Exception as e:
            self.logger.error(f"Failed to convert timeframes: {e}")
            return {}

    def _calculate_indicators(self, timeframe_data: Dict) -> Dict:
        """
        テクニカル指標を計算

        Args:
            timeframe_data: 時間足データ

        Returns:
            テクニカル指標の辞書
        """
        try:
            # H1足をベースに指標を計算
            if 'H1' not in timeframe_data:
                self.logger.error("H1 timeframe not available for indicators")
                return {}

            h1_data = timeframe_data['H1']
            close_prices = h1_data['close']
            high_prices = h1_data['high']
            low_prices = h1_data['low']

            # 各指標の計算
            indicators = {}

            # EMA (短期と長期)
            indicators['ema_short'] = self.technical_indicators.calculate_ema(
                data=close_prices,
                period=20
            )
            indicators['ema_long'] = self.technical_indicators.calculate_ema(
                data=close_prices,
                period=50
            )

            # RSI
            indicators['rsi'] = self.technical_indicators.calculate_rsi(
                data=close_prices,
                period=14
            )

            # MACD
            indicators['macd'] = self.technical_indicators.calculate_macd(
                data=close_prices,
                fast=12,
                slow=26,
                signal=9
            )

            # ATR
            indicators['atr'] = self.technical_indicators.calculate_atr(
                high=high_prices,
                low=low_prices,
                close=close_prices,
                period=14
            )

            # Bollinger Bands
            indicators['bollinger'] = self.technical_indicators.calculate_bollinger_bands(
                data=close_prices,
                period=20,
                std_dev=2.0
            )

            # Support & Resistance
            indicators['support_resistance'] = \
                self.technical_indicators.calculate_support_resistance(
                    high=h1_data['high'],
                    low=h1_data['low'],
                    window=20
                )

            return indicators

        except Exception as e:
            self.logger.error(f"Failed to calculate indicators: {e}")
            return {}

    def _save_to_database(self, ai_result: Dict, market_data: Dict) -> bool:
        """
        AI判断結果をデータベースに保存（モード別テーブル）

        Args:
            ai_result: AI判断結果
            market_data: マーケットデータ

        Returns:
            True: 保存成功, False: 保存失敗
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()

            # モード別のテーブル名を取得
            table_name = self.table_names['ai_judgments']

            # バックテストモードの場合は追加カラムを含める
            if self.mode_config.is_backtest():
                if not self.backtest_start_date or not self.backtest_end_date:
                    self.logger.warning(
                        "Backtest mode but backtest dates not provided. Skipping database save."
                    )
                    return False

                insert_query = f"""
                    INSERT INTO {table_name}
                    (symbol, timestamp, timeframe, action, confidence, reasoning,
                     market_data, backtest_start_date, backtest_end_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """

                cursor.execute(insert_query, (
                    ai_result.get('symbol', self.symbol),
                    datetime.now(),
                    'MULTI',  # 複数時間足統合分析
                    ai_result.get('action', 'HOLD'),
                    ai_result.get('confidence', 0),
                    ai_result.get('reasoning', ''),
                    Json(market_data),  # JSONBフィールドに保存
                    self.backtest_start_date,
                    self.backtest_end_date
                ))
            else:
                # DEMOモード/本番モード
                insert_query = f"""
                    INSERT INTO {table_name}
                    (timestamp, symbol, timeframe, action, confidence, reasoning, market_data)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """

                cursor.execute(insert_query, (
                    datetime.now(),
                    ai_result.get('symbol', self.symbol),
                    'MULTI',  # 複数時間足統合分析
                    ai_result.get('action', 'HOLD'),
                    ai_result.get('confidence', 0),
                    ai_result.get('reasoning', ''),
                    Json(market_data)  # JSONBフィールドに保存
                ))

            conn.commit()
            cursor.close()
            conn.close()

            self.logger.info(f"AI judgment saved to database ({table_name})")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save to database: {e}")
            return False

    def _create_error_result(self, error_message: str) -> Dict:
        """
        エラー結果を作成

        Args:
            error_message: エラーメッセージ

        Returns:
            エラー結果の辞書
        """
        return {
            'action': 'HOLD',
            'confidence': 0,
            'reasoning': f'Analysis failed: {error_message}',
            'timestamp': datetime.now().isoformat(),
            'symbol': self.symbol,
            'model': self.model,
            'error': error_message
        }

    def get_recent_judgments(self, limit: int = 10) -> List[Dict]:
        """
        最近のAI判断履歴を取得（モード別テーブル）

        Args:
            limit: 取得件数

        Returns:
            AI判断履歴のリスト
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()

            # モード別のテーブル名を取得
            table_name = self.table_names['ai_judgments']

            query = f"""
                SELECT
                    id,
                    timestamp,
                    symbol,
                    action,
                    confidence,
                    reasoning,
                    created_at
                FROM {table_name}
                WHERE symbol = %s
                ORDER BY created_at DESC
                LIMIT %s
            """

            cursor.execute(query, (self.symbol, limit))
            rows = cursor.fetchall()

            judgments = []
            for row in rows:
                # reasoningフィールドを安全に取得（エンコーディングエラー対策）
                try:
                    reasoning = row[5] if row[5] else ''
                    if isinstance(reasoning, bytes):
                        reasoning = reasoning.decode('utf-8', errors='replace')
                except Exception:
                    reasoning = '[Encoding Error]'

                judgments.append({
                    'id': row[0],
                    'timestamp': row[1].isoformat() if row[1] else None,
                    'symbol': row[2],
                    'action': row[3],
                    'confidence': float(row[4]) if row[4] else 0,
                    'reasoning': reasoning,
                    'created_at': row[6].isoformat() if row[6] else None
                })

            cursor.close()
            conn.close()

            return judgments

        except Exception as e:
            self.logger.error(f"Failed to get recent judgments: {e}")
            return []


# モジュールのエクスポート
__all__ = ['AIAnalyzer']
