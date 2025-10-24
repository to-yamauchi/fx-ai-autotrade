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
                 model: str = 'periodic_update',
                 backtest_start_date: Optional[str] = None,
                 backtest_end_date: Optional[str] = None):
        """
        AIAnalyzerの初期化

        Args:
            symbol: 通貨ペア（デフォルト: USDJPY）
            data_dir: ティックデータディレクトリ
            model: Phase名（'daily_analysis', 'periodic_update', 'position_monitor', 'emergency_evaluation'）
                   または完全なモデル名（例: gemini-2.5-flash）
                   注: 各Phaseメソッド呼び出し時に適切なモデルが自動選択されるため、
                       このパラメータは主に後方互換性のために残されています
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

        # マルチプロバイダー対応: Phase別にLLMクライアントを生成
        from src.ai_analysis.llm_client_factory import create_phase_clients
        try:
            self.phase_clients = create_phase_clients()
            self.logger.info("Multi-provider LLM clients initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize phase clients: {e}")
            self.logger.warning("Falling back to GeminiClient for all phases")
            self.phase_clients = {}

        # 後方互換性のため、gemini_clientも保持（deprecated）
        # 注: 新しいコードではself.phase_clients['phase_name']を使用してください
        from src.ai_analysis.gemini_client import GeminiClient
        self.gemini_client = GeminiClient()  # deprecated

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

            # 5. AI分析実行（マルチプロバイダー対応）
            # analyze_marketは通常Phase 3の定期更新で使用される
            client = self.phase_clients.get('periodic_update', self.gemini_client)
            ai_result = client.analyze_market(
                market_data=standardized_data,
                model='periodic_update'  # Phase名を渡してclient内で適切なモデルを選択
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

    def daily_review(
        self,
        previous_day_trades: List[Dict],
        prediction: Optional[Dict] = None,
        actual_market: Optional[Dict] = None,
        statistics: Optional[Dict] = None
    ) -> Dict:
        """
        前日のトレード結果を振り返り、分析結果を生成

        Args:
            previous_day_trades: 前日のトレード結果リスト
            prediction: 前日の予測内容
            actual_market: 実際の市場動向
            statistics: 統計情報

        Returns:
            振り返り結果の辞書
            {
                'score': {...},
                'analysis': {...},
                'lessons_for_today': [...],
                'pattern_recognition': {...}
            }
        """
        try:
            self.logger.info("Starting daily review...")

            # デフォルト値の設定
            if prediction is None:
                prediction = {'daily_bias': 'NEUTRAL', 'confidence': 0.5}
            if actual_market is None:
                actual_market = {'direction': '不明', 'volatility': '中程度'}
            if statistics is None:
                statistics = {'total_pips': 0, 'win_rate': '0%', 'max_drawdown': '0pips'}

            # プロンプトテンプレートの読み込み
            prompt_path = os.path.join(
                os.path.dirname(__file__),
                'prompts',
                'daily_review.txt'
            )

            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompt_template = f.read()

            # データを埋め込む
            import json
            prompt = prompt_template.format(
                trades_json=json.dumps(previous_day_trades, ensure_ascii=False, indent=2),
                prediction_json=json.dumps(prediction, ensure_ascii=False, indent=2),
                actual_market_json=json.dumps(actual_market, ensure_ascii=False, indent=2),
                statistics_json=json.dumps(statistics, ensure_ascii=False, indent=2)
            )

            self.logger.info("Calling LLM for daily review...")

            # Phase 1: デイリーレビュー用モデル（.envのMODEL_DAILY_ANALYSISから取得）
            # マルチプロバイダー対応: phase_clientsから適切なクライアントを使用
            client = self.phase_clients.get('daily_analysis', self.gemini_client)
            response = client.generate_response(
                prompt=prompt,
                model='daily_analysis',
                phase='Phase 1 (Daily Review)'
            )

            # JSONパース
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response

            review_result = json.loads(json_str)

            self.logger.info(f"Daily review completed. Total score: {review_result.get('score', {}).get('total', 'N/A')}")

            # データベースに保存
            self._save_review_to_database(review_result, previous_day_trades)

            return review_result

        except Exception as e:
            self.logger.error(f"Daily review failed: {e}", exc_info=True)
            return {
                'score': {'total': '0/100点', 'comment': 'エラーにより評価不可'},
                'analysis': {
                    'what_worked': [],
                    'what_failed': [],
                    'missed_signals': []
                },
                'lessons_for_today': [],
                'pattern_recognition': {
                    'success_patterns': [],
                    'failure_patterns': []
                },
                'error': str(e)
            }

    def _save_review_to_database(self, review_result: Dict, trades: List[Dict]) -> bool:
        """
        振り返り結果をデータベースに保存

        Args:
            review_result: 振り返り結果
            trades: トレードリスト

        Returns:
            成功時True
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()

            # バックテストモードの場合のテーブル名
            table_name = self.table_names.get('reviews', 'backtest_daily_reviews')

            # daily_reviewsテーブルに保存
            insert_query = f"""
                INSERT INTO {table_name}
                (review_date, symbol, total_score, score_breakdown, analysis,
                 lessons, patterns, trades_count, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            review_date = datetime.now().date()

            cursor.execute(insert_query, (
                review_date,
                self.symbol,
                review_result.get('score', {}).get('total', '0/100点'),
                Json(review_result.get('score', {})),
                Json(review_result.get('analysis', {})),
                Json(review_result.get('lessons_for_today', [])),
                Json(review_result.get('pattern_recognition', {})),
                len(trades),
                datetime.now()
            ))

            conn.commit()
            cursor.close()
            conn.close()

            self.logger.info(f"Daily review saved to database ({table_name})")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save review to database: {e}")
            return False

    def morning_analysis(
        self,
        market_data: Dict,
        review_result: Optional[Dict] = None,
        past_statistics: Optional[Dict] = None
    ) -> Dict:
        """
        朝の詳細分析を実行（08:00、Gemini Pro）

        Args:
            market_data: 標準化された市場データ（from data_standardizer）
            review_result: 前日の振り返り結果（from daily_review）
            past_statistics: 過去5日の統計データ

        Returns:
            本日のトレード戦略の辞書
            {
                'daily_bias': 'BUY' | 'SELL' | 'NEUTRAL',
                'confidence': 0.0-1.0,
                'reasoning': '判断理由',
                'market_environment': {...},
                'entry_conditions': {...},
                'exit_strategy': {...},
                'risk_management': {...},
                'key_levels': {...},
                'scenario_planning': {...},
                'lessons_applied': [...]
            }
        """
        try:
            self.logger.info("Starting morning detailed analysis...")

            # デフォルト値の設定
            if review_result is None:
                review_result = {
                    'lessons_for_today': ['前日データなし'],
                    'pattern_recognition': {
                        'success_patterns': [],
                        'failure_patterns': []
                    }
                }
            if past_statistics is None:
                past_statistics = {
                    'last_5_days': {
                        'total_pips': 0,
                        'win_rate': '0%',
                        'avg_holding_time': '0分'
                    }
                }

            # プロンプトテンプレートの読み込み
            prompt_path = os.path.join(
                os.path.dirname(__file__),
                'prompts',
                'morning_analysis.txt'
            )

            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompt_template = f.read()

            # データを埋め込む（replace を使って {} の問題を回避）
            import json
            prompt = prompt_template.replace(
                '{market_data_json}', json.dumps(market_data, ensure_ascii=False, indent=2)
            ).replace(
                '{review_json}', json.dumps(review_result, ensure_ascii=False, indent=2)
            ).replace(
                '{past_statistics_json}', json.dumps(past_statistics, ensure_ascii=False, indent=2)
            )

            self.logger.info("Calling LLM for morning analysis...")

            # Phase 2: 朝の詳細分析用モデル（.envのMODEL_DAILY_ANALYSISから取得）
            # マルチプロバイダー対応: phase_clientsから適切なクライアントを使用
            client = self.phase_clients.get('daily_analysis', self.gemini_client)
            response = client.generate_response(
                prompt=prompt,
                model='daily_analysis',
                phase='Phase 2 (Morning Analysis)'
            )

            # JSONパース
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response

            strategy_result = json.loads(json_str)

            self.logger.info(
                f"Morning analysis completed. Bias: {strategy_result.get('daily_bias', 'N/A')}, "
                f"Confidence: {strategy_result.get('confidence', 0):.2f}"
            )

            # データベースに保存
            self._save_morning_analysis_to_database(strategy_result, market_data)

            return strategy_result

        except Exception as e:
            self.logger.error(f"Morning analysis failed: {e}", exc_info=True)
            # フォールバック：保守的な戦略を返す
            return {
                'daily_bias': 'NEUTRAL',
                'confidence': 0.0,
                'reasoning': f'分析エラーにより保守的判断: {str(e)}',
                'market_environment': {
                    'trend': '不明',
                    'strength': '不明',
                    'phase': '不明'
                },
                'entry_conditions': {
                    'should_trade': False,
                    'direction': 'NEUTRAL',
                    'price_zone': {'min': 0, 'max': 0},
                    'required_signals': [],
                    'avoid_if': ['分析エラーのため取引見送り']
                },
                'exit_strategy': {
                    'take_profit': [],
                    'stop_loss': {'initial': 'account_2_percent'},
                    'indicator_exits': [],
                    'time_exits': {}
                },
                'risk_management': {
                    'position_size_multiplier': 0.0,
                    'max_positions': 0,
                    'reason': '分析エラーのため取引停止'
                },
                'key_levels': {},
                'scenario_planning': {},
                'lessons_applied': [],
                'error': str(e)
            }

    def _save_morning_analysis_to_database(self, strategy_result: Dict, market_data: Dict) -> bool:
        """
        朝の分析結果（戦略）をデータベースに保存

        Args:
            strategy_result: 戦略結果
            market_data: 市場データ

        Returns:
            成功時True
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()

            # テーブル名取得（モード別）
            table_name = self.table_names.get('strategies', 'backtest_daily_strategies')

            # バックテストモードの場合は追加カラムを含める
            if self.mode_config.is_backtest():
                if not self.backtest_start_date or not self.backtest_end_date:
                    self.logger.warning(
                        "Backtest mode but backtest dates not provided. Skipping database save."
                    )
                    return False

                insert_query = f"""
                    INSERT INTO {table_name}
                    (strategy_date, symbol, daily_bias, confidence, reasoning,
                     market_environment, entry_conditions, exit_strategy, risk_management,
                     key_levels, scenario_planning, lessons_applied, market_data,
                     backtest_start_date, backtest_end_date, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (strategy_date, symbol, backtest_start_date, backtest_end_date)
                    DO UPDATE SET
                        daily_bias = EXCLUDED.daily_bias,
                        confidence = EXCLUDED.confidence,
                        reasoning = EXCLUDED.reasoning,
                        market_environment = EXCLUDED.market_environment,
                        entry_conditions = EXCLUDED.entry_conditions,
                        exit_strategy = EXCLUDED.exit_strategy,
                        risk_management = EXCLUDED.risk_management,
                        key_levels = EXCLUDED.key_levels,
                        scenario_planning = EXCLUDED.scenario_planning,
                        lessons_applied = EXCLUDED.lessons_applied,
                        market_data = EXCLUDED.market_data,
                        created_at = EXCLUDED.created_at
                """

                cursor.execute(insert_query, (
                    datetime.now().date(),
                    self.symbol,
                    strategy_result.get('daily_bias', 'NEUTRAL'),
                    strategy_result.get('confidence', 0.0),
                    strategy_result.get('reasoning', ''),
                    Json(strategy_result.get('market_environment', {})),
                    Json(strategy_result.get('entry_conditions', {})),
                    Json(strategy_result.get('exit_strategy', {})),
                    Json(strategy_result.get('risk_management', {})),
                    Json(strategy_result.get('key_levels', {})),
                    Json(strategy_result.get('scenario_planning', {})),
                    Json(strategy_result.get('lessons_applied', [])),
                    Json(market_data),
                    self.backtest_start_date,
                    self.backtest_end_date,
                    datetime.now()
                ))
            else:
                # DEMOモード/本番モード
                insert_query = f"""
                    INSERT INTO {table_name}
                    (strategy_date, symbol, daily_bias, confidence, reasoning,
                     market_environment, entry_conditions, exit_strategy, risk_management,
                     key_levels, scenario_planning, lessons_applied, market_data, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (strategy_date, symbol)
                    DO UPDATE SET
                        daily_bias = EXCLUDED.daily_bias,
                        confidence = EXCLUDED.confidence,
                        reasoning = EXCLUDED.reasoning,
                        market_environment = EXCLUDED.market_environment,
                        entry_conditions = EXCLUDED.entry_conditions,
                        exit_strategy = EXCLUDED.exit_strategy,
                        risk_management = EXCLUDED.risk_management,
                        key_levels = EXCLUDED.key_levels,
                        scenario_planning = EXCLUDED.scenario_planning,
                        lessons_applied = EXCLUDED.lessons_applied,
                        market_data = EXCLUDED.market_data,
                        created_at = EXCLUDED.created_at
                """

                cursor.execute(insert_query, (
                    datetime.now().date(),
                    self.symbol,
                    strategy_result.get('daily_bias', 'NEUTRAL'),
                    strategy_result.get('confidence', 0.0),
                    strategy_result.get('reasoning', ''),
                    Json(strategy_result.get('market_environment', {})),
                    Json(strategy_result.get('entry_conditions', {})),
                    Json(strategy_result.get('exit_strategy', {})),
                    Json(strategy_result.get('risk_management', {})),
                    Json(strategy_result.get('key_levels', {})),
                    Json(strategy_result.get('scenario_planning', {})),
                    Json(strategy_result.get('lessons_applied', [])),
                    Json(market_data),
                    datetime.now()
                ))

            conn.commit()
            cursor.close()
            conn.close()

            self.logger.info(f"Morning analysis saved to database ({table_name})")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save morning analysis to database: {e}")
            return False

    def periodic_update(
        self,
        morning_strategy: Dict,
        current_market_data: Dict,
        today_trades: List[Dict],
        current_positions: List[Dict],
        update_time: str  # "12:00", "16:00", "21:30"
    ) -> Dict:
        """
        定期更新を実行（12:00/16:00/21:30、Gemini Flash）

        Args:
            morning_strategy: 朝の詳細分析で生成された戦略
            current_market_data: 現在の市場データ（標準化済み）
            today_trades: 本日のトレード実績
            current_positions: 現在のポジション状況
            update_time: 更新時刻（"12:00", "16:00", "21:30"）

        Returns:
            更新結果の辞書
            {
                'update_type': 'no_change' | 'bias_change' | 'risk_adjustment' | ...,
                'market_assessment': {...},
                'strategy_validity': {...},
                'recommended_changes': {...},
                'current_positions_action': {...},
                'new_entry_recommendation': {...}
            }
        """
        try:
            self.logger.info(f"Starting periodic update at {update_time}...")

            # デフォルト値の設定
            if not morning_strategy:
                morning_strategy = {
                    'daily_bias': 'NEUTRAL',
                    'confidence': 0.5,
                    'entry_conditions': {},
                    'exit_strategy': {},
                    'risk_management': {}
                }

            # プロンプトテンプレートの読み込み
            prompt_path = os.path.join(
                os.path.dirname(__file__),
                'prompts',
                'periodic_update.txt'
            )

            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompt_template = f.read()

            # データを埋め込む
            import json
            prompt = prompt_template.format(
                morning_strategy_json=json.dumps(morning_strategy, ensure_ascii=False, indent=2),
                current_market_json=json.dumps(current_market_data, ensure_ascii=False, indent=2),
                today_trades_json=json.dumps(today_trades, ensure_ascii=False, indent=2),
                current_positions_json=json.dumps(current_positions, ensure_ascii=False, indent=2),
                update_time=update_time
            )

            self.logger.info(f"Calling LLM for periodic update ({update_time})...")

            # Phase 3: 定期更新用モデル（.envのMODEL_PERIODIC_UPDATEから取得）
            # マルチプロバイダー対応: phase_clientsから適切なクライアントを使用
            client = self.phase_clients.get('periodic_update', self.gemini_client)
            response = client.generate_response(
                prompt=prompt,
                model='periodic_update',
                phase='Phase 3 (Periodic Update)'
            )

            # JSONパース
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response

            update_result = json.loads(json_str)

            self.logger.info(
                f"Periodic update completed at {update_time}. "
                f"Type: {update_result.get('update_type', 'N/A')}"
            )

            # データベースに保存
            self._save_periodic_update_to_database(update_result, update_time, current_market_data)

            return update_result

        except Exception as e:
            self.logger.error(f"Periodic update failed at {update_time}: {e}", exc_info=True)
            # フォールバック：変更なし
            return {
                'update_type': 'no_change',
                'market_assessment': {
                    'trend_change': '不明',
                    'volatility_change': '不明',
                    'key_events': []
                },
                'strategy_validity': {
                    'morning_bias_valid': True,
                    'confidence_change': 0.0,
                    'reasoning': f'分析エラーのため朝の戦略を継続: {str(e)}'
                },
                'recommended_changes': {
                    'bias': {'apply': False},
                    'risk_management': {},
                    'exit_strategy': {}
                },
                'current_positions_action': {
                    'keep_open': True,
                    'close_reason': '',
                    'adjust_sl': {'apply': False}
                },
                'new_entry_recommendation': {
                    'should_enter_now': False,
                    'direction': None,
                    'reason': '分析エラー'
                },
                'summary': '分析エラーのため変更なし',
                'error': str(e)
            }

    def generate_structured_rule(
        self,
        market_data: Dict,
        review_result: Optional[Dict] = None,
        past_statistics: Optional[Dict] = None
    ) -> Dict:
        """
        構造化トレードルールを生成（v2プロンプト使用）

        morning_analysis_v2.txtを使用して、プログラムが直接解釈可能な
        構造化されたトレードルールを生成します。

        Args:
            market_data: 標準化された市場データ
            review_result: 前日の振り返り結果（optional）
            past_statistics: 過去5日の統計データ（optional）

        Returns:
            構造化トレードルールの辞書
            {
                'version': '2.0',
                'generated_at': '2025-01-15T08:00:00Z',
                'valid_until': '2025-01-15T09:00:00Z',
                'daily_bias': 'BUY' | 'SELL' | 'NEUTRAL',
                'confidence': 0.0-1.0,
                'entry_conditions': {...},
                'exit_strategy': {...},
                'risk_management': {...},
                'hourly_predictions': {...},
                ...
            }
        """
        try:
            self.logger.info("Generating structured trading rule (v2)...")

            # デフォルト値の設定
            if review_result is None:
                review_result = {
                    'lessons_for_today': ['前日データなし'],
                    'pattern_recognition': {
                        'success_patterns': [],
                        'failure_patterns': []
                    }
                }
            if past_statistics is None:
                past_statistics = {
                    'last_5_days': {
                        'total_pips': 0,
                        'win_rate': '0%',
                        'avg_holding_time': '0分'
                    }
                }

            # プロンプトテンプレートの読み込み（v2）
            prompt_path = os.path.join(
                os.path.dirname(__file__),
                'prompts',
                'morning_analysis_v2.txt'
            )

            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompt_template = f.read()

            # データを埋め込む
            import json
            prompt = prompt_template.replace(
                '{market_data_json}', json.dumps(market_data, ensure_ascii=False, indent=2)
            ).replace(
                '{review_json}', json.dumps(review_result, ensure_ascii=False, indent=2)
            ).replace(
                '{past_statistics_json}', json.dumps(past_statistics, ensure_ascii=False, indent=2)
            )

            self.logger.info("Calling LLM for structured rule generation...")

            # Phase 2: 朝の詳細分析用モデル（構造化ルール生成）
            client = self.phase_clients.get('daily_analysis', self.gemini_client)
            response = client.generate_response(
                prompt=prompt,
                model='daily_analysis',
                phase='Phase 2 (Structured Rule Generation)'
            )

            # JSONパース
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response

            structured_rule = json.loads(json_str)

            # タイムスタンプの設定（もし含まれていなければ）
            if 'generated_at' not in structured_rule:
                structured_rule['generated_at'] = datetime.now().isoformat()
            if 'valid_until' not in structured_rule:
                # デフォルトで1時間後に期限切れ
                structured_rule['valid_until'] = (datetime.now() + timedelta(hours=1)).isoformat()

            self.logger.info(
                f"Structured rule generated. Bias: {structured_rule.get('daily_bias', 'N/A')}, "
                f"Confidence: {structured_rule.get('confidence', 0):.2f}"
            )

            return structured_rule

        except Exception as e:
            self.logger.error(f"Structured rule generation failed: {e}", exc_info=True)
            # フォールバック：安全な構造化ルールを返す
            return {
                'version': '2.0',
                'generated_at': datetime.now().isoformat(),
                'valid_until': (datetime.now() + timedelta(hours=1)).isoformat(),
                'daily_bias': 'NEUTRAL',
                'confidence': 0.0,
                'reasoning': f'ルール生成エラーのため保守的判断: {str(e)}',
                'market_environment': {
                    'trend': '不明',
                    'strength': '不明',
                    'phase': '不明'
                },
                'entry_conditions': {
                    'should_trade': False,
                    'direction': 'NEUTRAL',
                    'price_zone': {'min': 0, 'max': 0},
                    'indicators': {},
                    'spread': {'max_pips': 10},
                    'time_filter': {'avoid_times': []}
                },
                'exit_strategy': {
                    'take_profit': [],
                    'stop_loss': {
                        'initial_pips': 15,
                        'price_level': 0,
                        'trailing': {}
                    },
                    'indicator_exits': [],
                    'time_exits': {}
                },
                'risk_management': {
                    'position_size_multiplier': 0.0,
                    'max_positions': 0,
                    'max_risk_per_trade_percent': 2.0,
                    'max_total_exposure_percent': 4.0
                },
                'key_levels': {},
                'hourly_predictions': {},
                'error': str(e)
            }

    def _save_periodic_update_to_database(
        self,
        update_result: Dict,
        update_time: str,
        market_data: Dict
    ) -> bool:
        """
        定期更新結果をデータベースに保存

        Args:
            update_result: 更新結果
            update_time: 更新時刻（"12:00", "16:00", "21:30"）
            market_data: 市場データ

        Returns:
            成功時True
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()

            # テーブル名取得（モード別）
            table_name = self.table_names.get('periodic_updates', 'backtest_periodic_updates')

            # バックテストモードの場合は追加カラムを含める
            if self.mode_config.is_backtest():
                if not self.backtest_start_date or not self.backtest_end_date:
                    self.logger.warning(
                        "Backtest mode but backtest dates not provided. Skipping database save."
                    )
                    return False

                insert_query = f"""
                    INSERT INTO {table_name}
                    (update_date, update_time, symbol, update_type,
                     market_assessment, strategy_validity, recommended_changes,
                     positions_action, entry_recommendation, summary, market_data,
                     backtest_start_date, backtest_end_date, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (update_date, update_time, symbol, backtest_start_date, backtest_end_date)
                    DO UPDATE SET
                        update_type = EXCLUDED.update_type,
                        market_assessment = EXCLUDED.market_assessment,
                        strategy_validity = EXCLUDED.strategy_validity,
                        recommended_changes = EXCLUDED.recommended_changes,
                        positions_action = EXCLUDED.positions_action,
                        entry_recommendation = EXCLUDED.entry_recommendation,
                        summary = EXCLUDED.summary,
                        market_data = EXCLUDED.market_data,
                        created_at = EXCLUDED.created_at
                """

                cursor.execute(insert_query, (
                    datetime.now().date(),
                    update_time,
                    self.symbol,
                    update_result.get('update_type', 'no_change'),
                    Json(update_result.get('market_assessment', {})),
                    Json(update_result.get('strategy_validity', {})),
                    Json(update_result.get('recommended_changes', {})),
                    Json(update_result.get('current_positions_action', {})),
                    Json(update_result.get('new_entry_recommendation', {})),
                    update_result.get('summary', ''),
                    Json(market_data),
                    self.backtest_start_date,
                    self.backtest_end_date,
                    datetime.now()
                ))
            else:
                # DEMOモード/本番モード
                insert_query = f"""
                    INSERT INTO {table_name}
                    (update_date, update_time, symbol, update_type,
                     market_assessment, strategy_validity, recommended_changes,
                     positions_action, entry_recommendation, summary, market_data, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (update_date, update_time, symbol)
                    DO UPDATE SET
                        update_type = EXCLUDED.update_type,
                        market_assessment = EXCLUDED.market_assessment,
                        strategy_validity = EXCLUDED.strategy_validity,
                        recommended_changes = EXCLUDED.recommended_changes,
                        positions_action = EXCLUDED.positions_action,
                        entry_recommendation = EXCLUDED.entry_recommendation,
                        summary = EXCLUDED.summary,
                        market_data = EXCLUDED.market_data,
                        created_at = EXCLUDED.created_at
                """

                cursor.execute(insert_query, (
                    datetime.now().date(),
                    update_time,
                    self.symbol,
                    update_result.get('update_type', 'no_change'),
                    Json(update_result.get('market_assessment', {})),
                    Json(update_result.get('strategy_validity', {})),
                    Json(update_result.get('recommended_changes', {})),
                    Json(update_result.get('current_positions_action', {})),
                    Json(update_result.get('new_entry_recommendation', {})),
                    update_result.get('summary', ''),
                    Json(market_data),
                    datetime.now()
                ))

            conn.commit()
            cursor.close()
            conn.close()

            self.logger.info(f"Periodic update saved to database ({table_name})")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save periodic update to database: {e}")
            return False

    def layer3a_monitor(
        self,
        position: Dict,
        current_market_data: Dict,
        daily_strategy: Dict
    ) -> Dict:
        """
        Layer 3a 監視を実行（15分ごと、Flash-Lite）

        Args:
            position: 監視対象のポジション情報
            current_market_data: 現在の市場データ（簡易版）
            daily_strategy: 本日の戦略

        Returns:
            監視結果の辞書
            {
                'action': 'HOLD' | 'CLOSE_NOW' | 'ADJUST_SL' | 'PARTIAL_CLOSE',
                'urgency': 'normal' | 'high',
                'reason': '判断理由',
                'details': {...},
                'recommended_action': {...}
            }
        """
        try:
            self.logger.debug("Starting Layer 3a monitoring...")

            # プロンプトテンプレートの読み込み
            prompt_path = os.path.join(
                os.path.dirname(__file__),
                'prompts',
                'layer3a_monitoring.txt'
            )

            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompt_template = f.read()

            # データを埋め込む
            import json
            prompt = prompt_template.format(
                position_json=json.dumps(position, ensure_ascii=False, indent=2),
                current_market_json=json.dumps(current_market_data, ensure_ascii=False, indent=2),
                daily_strategy_json=json.dumps(daily_strategy, ensure_ascii=False, indent=2)
            )

            self.logger.debug("Calling LLM for Layer 3a monitoring...")

            # Phase 4: Layer 3a監視用モデル（.envのMODEL_POSITION_MONITORから取得）
            # マルチプロバイダー対応: phase_clientsから適切なクライアントを使用
            client = self.phase_clients.get('position_monitor', self.gemini_client)
            response = client.generate_response(
                prompt=prompt,
                model='position_monitor',
                phase='Phase 4 (Layer 3a Monitor)'
            )

            # JSONパース
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response

            monitor_result = json.loads(json_str)

            self.logger.debug(
                f"Layer 3a monitoring completed. "
                f"Action: {monitor_result.get('action', 'N/A')}"
            )

            # データベースに保存（頻度が高いので保存は任意）
            # バックテストモードでのみ保存
            if self.mode_config.is_backtest():
                self._save_layer3a_monitoring_to_database(monitor_result, position, current_market_data)

            return monitor_result

        except Exception as e:
            self.logger.error(f"Layer 3a monitoring failed: {e}", exc_info=True)
            # フォールバック：HOLD
            return {
                'action': 'HOLD',
                'urgency': 'normal',
                'reason': f'監視エラーのため保留: {str(e)}',
                'details': {
                    'profit_status': 'unknown',
                    'risk_level': 'unknown',
                    'signals': []
                },
                'recommended_action': {
                    'close_percent': 0,
                    'new_sl': None,
                    'reason': '監視エラー'
                },
                'error': str(e)
            }

    def _save_layer3a_monitoring_to_database(
        self,
        monitor_result: Dict,
        position: Dict,
        market_data: Dict
    ) -> bool:
        """
        Layer 3a監視結果をデータベースに保存

        Args:
            monitor_result: 監視結果
            position: ポジション情報
            market_data: 市場データ

        Returns:
            成功時True
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()

            # テーブル名取得（モード別）
            table_name = self.table_names.get('layer3a_monitoring', 'backtest_layer3a_monitoring')

            # バックテストモードの場合は追加カラムを含める
            if self.mode_config.is_backtest():
                if not self.backtest_start_date or not self.backtest_end_date:
                    self.logger.warning(
                        "Backtest mode but backtest dates not provided. Skipping database save."
                    )
                    return False

                insert_query = f"""
                    INSERT INTO {table_name}
                    (check_timestamp, symbol, action, urgency, reason,
                     details, recommended_action, position_info, market_data,
                     backtest_start_date, backtest_end_date, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """

                cursor.execute(insert_query, (
                    datetime.now(),
                    self.symbol,
                    monitor_result.get('action', 'HOLD'),
                    monitor_result.get('urgency', 'normal'),
                    monitor_result.get('reason', ''),
                    Json(monitor_result.get('details', {})),
                    Json(monitor_result.get('recommended_action', {})),
                    Json(position),
                    Json(market_data),
                    self.backtest_start_date,
                    self.backtest_end_date,
                    datetime.now()
                ))
            else:
                # DEMOモード/本番モード
                insert_query = f"""
                    INSERT INTO {table_name}
                    (check_timestamp, symbol, action, urgency, reason,
                     details, recommended_action, position_info, market_data, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """

                cursor.execute(insert_query, (
                    datetime.now(),
                    self.symbol,
                    monitor_result.get('action', 'HOLD'),
                    monitor_result.get('urgency', 'normal'),
                    monitor_result.get('reason', ''),
                    Json(monitor_result.get('details', {})),
                    Json(monitor_result.get('recommended_action', {})),
                    Json(position),
                    Json(market_data),
                    datetime.now()
                ))

            conn.commit()
            cursor.close()
            conn.close()

            self.logger.debug(f"Layer 3a monitoring saved to database ({table_name})")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save Layer 3a monitoring to database: {e}")
            return False

    def layer3b_emergency(
        self,
        anomaly_info: Dict,
        current_positions: List[Dict],
        current_market_data: Dict,
        daily_strategy: Dict
    ) -> Dict:
        """
        Layer 3b 緊急評価を実行（異常検知時、Gemini Pro）

        Args:
            anomaly_info: 異常検知情報（Layer 2から）
            current_positions: 現在のポジション一覧
            current_market_data: 現在の市場データ
            daily_strategy: 本日の戦略

        Returns:
            緊急評価結果の辞書
            {
                'severity': 'low' | 'medium' | 'high' | 'critical',
                'action': 'CONTINUE' | 'CLOSE_ALL' | 'CLOSE_PARTIAL' | 'REVERSE',
                'reasoning': '判断理由',
                'immediate_actions': [...],
                'risk_assessment': {...}
            }
        """
        try:
            self.logger.warning("Starting Layer 3b emergency evaluation...")

            # プロンプトテンプレートの読み込み
            prompt_path = os.path.join(
                os.path.dirname(__file__),
                'prompts',
                'layer3b_emergency.txt'
            )

            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompt_template = f.read()

            # データを埋め込む
            import json
            prompt = prompt_template.format(
                anomaly_json=json.dumps(anomaly_info, ensure_ascii=False, indent=2),
                positions_json=json.dumps(current_positions, ensure_ascii=False, indent=2),
                market_json=json.dumps(current_market_data, ensure_ascii=False, indent=2),
                strategy_json=json.dumps(daily_strategy, ensure_ascii=False, indent=2)
            )

            self.logger.warning("Calling LLM for Layer 3b emergency evaluation...")

            # Phase 5: Layer 3b緊急評価用モデル（.envのMODEL_EMERGENCY_EVALUATIONから取得）
            # マルチプロバイダー対応: phase_clientsから適切なクライアントを使用
            client = self.phase_clients.get('emergency_evaluation', self.gemini_client)
            response = client.generate_response(
                prompt=prompt,
                model='emergency_evaluation',
                phase='Phase 5 (Layer 3b Emergency)'
            )

            # JSONパース
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response

            emergency_result = json.loads(json_str)

            self.logger.warning(
                f"Layer 3b emergency evaluation completed. "
                f"Severity: {emergency_result.get('severity', 'N/A')}, "
                f"Action: {emergency_result.get('action', 'N/A')}"
            )

            # データベースに保存
            self._save_layer3b_emergency_to_database(emergency_result, anomaly_info, current_market_data)

            return emergency_result

        except Exception as e:
            self.logger.error(f"Layer 3b emergency evaluation failed: {e}", exc_info=True)
            # フォールバック：保守的判断（全決済）
            return {
                'severity': 'critical',
                'action': 'CLOSE_ALL',
                'reasoning': f'緊急評価エラーのため全ポジションクローズを推奨: {str(e)}',
                'immediate_actions': [
                    '全ポジションを即座にクローズ',
                    '新規エントリーを停止',
                    'システムログを確認'
                ],
                'risk_assessment': {
                    'current_risk': 'unknown',
                    'potential_loss': 'unknown',
                    'recommendation': '安全のため全決済'
                },
                'error': str(e)
            }

    def _save_layer3b_emergency_to_database(
        self,
        emergency_result: Dict,
        anomaly_info: Dict,
        market_data: Dict
    ) -> bool:
        """
        Layer 3b緊急評価結果をデータベースに保存

        Args:
            emergency_result: 緊急評価結果
            anomaly_info: 異常検知情報
            market_data: 市場データ

        Returns:
            成功時True
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()

            # テーブル名取得（モード別）
            table_name = self.table_names.get('layer3b_emergency', 'backtest_layer3b_emergency')

            # バックテストモードの場合は追加カラムを含める
            if self.mode_config.is_backtest():
                if not self.backtest_start_date or not self.backtest_end_date:
                    self.logger.warning(
                        "Backtest mode but backtest dates not provided. Skipping database save."
                    )
                    return False

                insert_query = f"""
                    INSERT INTO {table_name}
                    (event_timestamp, symbol, severity, action, reasoning,
                     immediate_actions, risk_assessment, anomaly_info, market_data,
                     backtest_start_date, backtest_end_date, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """

                cursor.execute(insert_query, (
                    datetime.now(),
                    self.symbol,
                    emergency_result.get('severity', 'medium'),
                    emergency_result.get('action', 'CONTINUE'),
                    emergency_result.get('reasoning', ''),
                    Json(emergency_result.get('immediate_actions', [])),
                    Json(emergency_result.get('risk_assessment', {})),
                    Json(anomaly_info),
                    Json(market_data),
                    self.backtest_start_date,
                    self.backtest_end_date,
                    datetime.now()
                ))
            else:
                # DEMOモード/本番モード
                insert_query = f"""
                    INSERT INTO {table_name}
                    (event_timestamp, symbol, severity, action, reasoning,
                     immediate_actions, risk_assessment, anomaly_info, market_data, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """

                cursor.execute(insert_query, (
                    datetime.now(),
                    self.symbol,
                    emergency_result.get('severity', 'medium'),
                    emergency_result.get('action', 'CONTINUE'),
                    emergency_result.get('reasoning', ''),
                    Json(emergency_result.get('immediate_actions', [])),
                    Json(emergency_result.get('risk_assessment', {})),
                    Json(anomaly_info),
                    Json(market_data),
                    datetime.now()
                ))

            conn.commit()
            cursor.close()
            conn.close()

            self.logger.warning(f"Layer 3b emergency evaluation saved to database ({table_name})")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save Layer 3b emergency evaluation to database: {e}")
            return False


# モジュールのエクスポート
__all__ = ['AIAnalyzer']
