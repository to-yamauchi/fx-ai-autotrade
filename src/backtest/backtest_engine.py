"""
========================================
バックテストエンジン
========================================

ファイル名: backtest_engine.py
パス: src/backtest/backtest_engine.py

【概要】
過去データを使用してAI判断とトレード戦略をバックテストするエンジン。
指定期間のデータで時系列にAI分析を実行し、パフォーマンスを評価します。

【主な機能】
1. 過去データの時系列処理
2. AI判断の実行
3. 仮想トレードのシミュレーション
4. パフォーマンス統計の計算
5. 結果のデータベース保存

【使用例】
```python
from src.backtest.backtest_engine import BacktestEngine

engine = BacktestEngine(
    symbol='USDJPY',
    start_date='2024-01-01',
    end_date='2024-12-31'
)
results = engine.run()
print(f"Win rate: {results['win_rate']:.2f}%")
```

【作成日】2025-10-23
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta, date
import logging
import pandas as pd
import psycopg2
from psycopg2.extras import Json
import os

from src.backtest.trade_simulator import TradeSimulator
from src.backtest.csv_tick_loader import CSVTickLoader
from src.ai_analysis.ai_analyzer import AIAnalyzer
from src.data_processing.mt5_data_loader import MT5DataLoader
from src.rule_engine.trading_rules import TradingRules


class BacktestEngine:
    """
    バックテストエンジンクラス

    過去データでAI判断とトレード戦略をバックテストします。
    """

    def __init__(
        self,
        symbol: str = 'USDJPY',
        start_date: str = '2024-01-01',
        end_date: str = '2024-12-31',
        initial_balance: float = 100000.0,
        ai_model: str = 'flash',
        sampling_interval_hours: int = 24,  # サンプリング間隔（時間）
        risk_percent: float = 1.0,
        csv_path: Optional[str] = None  # CSVファイルパス（指定時はCSVを使用）
    ):
        """
        バックテストエンジンの初期化

        Args:
            symbol: 通貨ペア
            start_date: 開始日（YYYY-MM-DD）
            end_date: 終了日（YYYY-MM-DD）
            initial_balance: 初期残高
            ai_model: AIモデル（flash/pro/flash-8b）
            sampling_interval_hours: AI分析のサンプリング間隔（時間）
            risk_percent: リスク許容率（%）
            csv_path: CSVファイルパス（指定時はCSVからデータ読み込み、未指定時はMT5）
        """
        self.symbol = symbol
        self.start_date = datetime.strptime(start_date, '%Y-%m-%d')
        self.end_date = datetime.strptime(end_date, '%Y-%m-%d')
        self.initial_balance = initial_balance
        self.ai_model = ai_model
        self.sampling_interval = timedelta(hours=sampling_interval_hours)
        self.risk_percent = risk_percent
        self.csv_path = csv_path
        self.logger = logging.getLogger(__name__)

        # コンポーネント初期化
        self.simulator = TradeSimulator(initial_balance=initial_balance, symbol=symbol)

        # データローダー：CSVまたはMT5
        if csv_path:
            self.data_loader = CSVTickLoader(csv_path=csv_path, symbol=symbol)
            self.use_csv = True
        else:
            self.data_loader = MT5DataLoader(symbol=symbol)
            self.use_csv = False

        self.rules = TradingRules()

        # バックテスト実行状態
        self.current_time: Optional[datetime] = None
        self.trade_history: List[Dict] = []

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
            f"BacktestEngine initialized: "
            f"{start_date} to {end_date}, "
            f"model={ai_model}, "
            f"sampling={sampling_interval_hours}h"
        )

    def run(self) -> Dict:
        """
        バックテストを実行

        Returns:
            バックテスト結果の統計情報
        """
        self.logger.info("=" * 80)
        self.logger.info("Starting Backtest")
        self.logger.info("=" * 80)
        self.logger.info(f"Period: {self.start_date.date()} to {self.end_date.date()}")
        self.logger.info(f"Initial Balance: {self.initial_balance:,.0f} JPY")
        self.logger.info(f"AI Model: {self.ai_model}")
        self.logger.info(f"Sampling Interval: {self.sampling_interval}")
        self.logger.info("")

        # 1. 全期間のデータを取得
        self.logger.info("Loading historical data...")

        if self.use_csv:
            # CSVファイルから読み込み（AI分析用に30日のバッファを含む）
            self.logger.info(f"Using CSV file: {self.csv_path}")
            tick_df = self.data_loader.load_ticks(
                start_date=self.start_date.strftime('%Y-%m-%d'),
                end_date=self.end_date.strftime('%Y-%m-%d'),
                history_days=30  # AI分析に必要な過去データ
            )
        else:
            # MT5から読み込み
            self.logger.info("Using MT5 data")
            days = (self.end_date - self.start_date).days
            tick_df = self.data_loader.load_recent_ticks(days=days + 30)

        if tick_df is None or tick_df.empty:
            self.logger.error("Failed to load historical data")
            return {}

        # DataFrameをリストに変換
        tick_data = []
        for idx, row in tick_df.iterrows():
            tick_data.append({
                'time': row['timestamp'],  # カラム名は'timestamp'
                'bid': row['bid'],
                'ask': row['ask']
            })

        self.logger.info(f"Loaded {len(tick_data)} ticks")
        self.logger.info("")

        # 2. 日ごとのループでバックテスト実行
        self.logger.info("Running daily backtest with reviews...")

        current_date = self.start_date.date()
        end_date = self.end_date.date()
        day_count = 0
        review_result = None  # 前日の振り返り結果
        strategy_result = None  # 本日の戦略

        while current_date <= end_date:
            self.logger.info("")
            self.logger.info("-" * 80)
            self.logger.info(f"Date: {current_date}")
            self.logger.info("-" * 80)

            # === 06:00 前日振り返り（初日以外） ===
            if day_count > 0:
                self.logger.info("06:00 - Running daily review...")
                previous_day_trades = self._get_trades_for_date(current_date - timedelta(days=1))

                if previous_day_trades:
                    review_result = self._run_daily_review(
                        previous_day_trades,
                        current_date - timedelta(days=1)
                    )

                    if review_result:
                        self.logger.info(
                            f"Review completed. Score: {review_result.get('score', {}).get('total', 'N/A')}"
                        )
                else:
                    self.logger.info("No trades on previous day, skipping review")

            # === 08:00 朝の詳細分析（Gemini Pro） ===
            self.logger.info("08:00 - Running morning detailed analysis...")
            strategy_result = self._run_morning_analysis(
                current_date=current_date,
                review_result=review_result
            )

            if strategy_result:
                self.logger.info(
                    f"Morning analysis completed. "
                    f"Bias: {strategy_result.get('daily_bias', 'N/A')}, "
                    f"Confidence: {strategy_result.get('confidence', 0):.2f}, "
                    f"Should trade: {strategy_result.get('entry_conditions', {}).get('should_trade', False)}"
                )

            # 朝の戦略に基づいてトレード判断
            current_time = datetime.combine(current_date, datetime.min.time())
            if strategy_result and strategy_result.get('entry_conditions', {}).get('should_trade', False):
                self._execute_trade_from_strategy(strategy_result, current_time)
            else:
                self.logger.info("No trade signal from morning analysis")

            # === 12:00 定期更新（Gemini Flash） ===
            self.logger.info("12:00 - Running periodic update...")
            strategy_result = self._run_periodic_update(
                current_date=current_date,
                update_time="12:00",
                morning_strategy=strategy_result
            )

            # === 16:00 定期更新（Gemini Flash） ===
            self.logger.info("16:00 - Running periodic update...")
            strategy_result = self._run_periodic_update(
                current_date=current_date,
                update_time="16:00",
                morning_strategy=strategy_result
            )

            # === 21:30 定期更新（Gemini Flash） ===
            self.logger.info("21:30 - Running periodic update...")
            strategy_result = self._run_periodic_update(
                current_date=current_date,
                update_time="21:30",
                morning_strategy=strategy_result
            )

            # 市場価格を更新（既存ポジションのSL/TPチェック）
            # 当日の全ティックをチェック
            next_date = current_date + timedelta(days=1)
            for tick in tick_data:
                tick_time = tick['time']
                if current_date <= tick_time.date() < next_date:
                    self.simulator.update_market_price(
                        bid=tick['bid'],
                        ask=tick['ask'],
                        timestamp=tick_time
                    )

            # 進捗表示
            if day_count % 5 == 0:
                self.logger.info(
                    f"Progress: {current_date}, "
                    f"Balance: {self.simulator.balance:,.0f}, "
                    f"Open Positions: {len(self.simulator.open_positions)}"
                )

            # 次の日へ
            current_date += timedelta(days=1)
            day_count += 1

        # 3. すべてのポジションをクローズ
        self.logger.info("")
        self.logger.info("Closing all remaining positions...")
        self.simulator.close_all_positions(reason='Backtest end')

        # 4. 統計を取得
        stats = self.simulator.get_statistics()

        # 5. 結果をログ出力
        self._print_results(stats)

        # 6. データベースに保存
        self._save_results(stats)

        self.logger.info("")
        self.logger.info("=" * 80)
        self.logger.info("Backtest Completed")
        self.logger.info("=" * 80)
        self.logger.info("")

        return stats

    def _analyze_at_time(self, timestamp: datetime) -> Optional[Dict]:
        """
        指定時刻でAI分析を実行

        Args:
            timestamp: 分析時刻

        Returns:
            AI分析結果
        """
        try:
            # この時点までのデータでAI分析を実行
            # 注: 実際には、timestampより前のデータのみを使用すべき（未来データを使わない）
            analyzer = AIAnalyzer(
                symbol=self.symbol,
                model=self.ai_model,
                backtest_start_date=self.start_date.strftime('%Y-%m-%d'),
                backtest_end_date=self.end_date.strftime('%Y-%m-%d')
            )

            # 簡略化: 直近30日のデータを使用
            ai_result = analyzer.analyze_market()

            return ai_result

        except Exception as e:
            self.logger.error(f"AI analysis failed at {timestamp}: {e}")
            return None

    def _execute_trade(self, ai_result: Dict, timestamp: datetime):
        """
        AI判断に基づいてトレードを実行

        Args:
            ai_result: AI分析結果
            timestamp: 実行時刻
        """
        action = ai_result.get('action')
        confidence = ai_result.get('confidence', 0)

        # ルール検証
        spread = 2.0  # 固定スプレッド（実際はデータから取得すべき）
        current_positions = len(self.simulator.open_positions)

        is_valid, message = self.rules.validate_trade(
            ai_judgment=ai_result,
            current_positions=current_positions,
            spread=spread
        )

        if not is_valid:
            self.logger.debug(f"Trade rejected: {message}")
            return

        # ポジションサイズを計算
        entry_price = ai_result.get('entry_price', self.simulator.current_ask)
        sl = ai_result.get('stop_loss')
        tp = ai_result.get('take_profit')

        if sl:
            stop_loss_pips = abs(entry_price - sl) * 100
            volume = self.rules.calculate_position_size(
                account_balance=self.simulator.balance,
                risk_percent=self.risk_percent,
                stop_loss_pips=stop_loss_pips,
                pip_value=1000.0
            )
        else:
            volume = 0.01  # デフォルト最小ロット

        # トレード実行
        ticket = self.simulator.open_position(
            action=action,
            price=entry_price,
            volume=volume,
            sl=sl,
            tp=tp,
            comment=f"AI: {confidence}%"
        )

        self.logger.info(
            f"Trade executed: {action} {volume} lots @ {entry_price}, "
            f"SL={sl}, TP={tp}, confidence={confidence}%"
        )

        # 履歴に記録
        self.trade_history.append({
            'timestamp': timestamp,
            'ticket': ticket,
            'action': action,
            'entry_price': entry_price,
            'volume': volume,
            'sl': sl,
            'tp': tp,
            'confidence': confidence
        })

    def _update_market_price(self, timestamp: datetime, tick_data: List[Dict]):
        """
        市場価格を更新

        Args:
            timestamp: 現在時刻
            tick_data: ティックデータ
        """
        # 指定時刻に最も近いティックを探す
        closest_tick = None
        min_diff = timedelta.max

        for tick in tick_data:
            tick_time = tick['time']
            diff = abs(tick_time - timestamp)
            if diff < min_diff:
                min_diff = diff
                closest_tick = tick

        if closest_tick:
            self.simulator.update_market_price(
                bid=closest_tick['bid'],
                ask=closest_tick['ask']
            )

    def _print_results(self, stats: Dict):
        """
        結果を出力

        Args:
            stats: 統計情報
        """
        self.logger.info("")
        self.logger.info("=" * 80)
        self.logger.info("Backtest Results")
        self.logger.info("=" * 80)
        self.logger.info("")
        self.logger.info(f"Period: {self.start_date.date()} to {self.end_date.date()}")
        self.logger.info(f"Duration: {(self.end_date - self.start_date).days} days")
        self.logger.info("")
        self.logger.info(f"Initial Balance: {stats['initial_balance']:,.0f} JPY")
        self.logger.info(f"Final Balance:   {stats['final_balance']:,.0f} JPY")
        self.logger.info(f"Net Profit:      {stats['net_profit']:,.0f} JPY")
        self.logger.info(f"Return:          {stats['return_pct']:.2f}%")
        self.logger.info("")
        self.logger.info(f"Total Trades:    {stats['total_trades']}")
        self.logger.info(f"Winning Trades:  {stats['winning_trades']}")
        self.logger.info(f"Losing Trades:   {stats['losing_trades']}")
        self.logger.info(f"Win Rate:        {stats['win_rate']:.2f}%")
        self.logger.info("")
        self.logger.info(f"Total Profit:    {stats['total_profit']:,.0f} JPY")
        self.logger.info(f"Total Loss:      {stats['total_loss']:,.0f} JPY")
        self.logger.info(f"Avg Profit:      {stats['avg_profit']:,.0f} JPY")
        self.logger.info(f"Avg Loss:        {stats['avg_loss']:,.0f} JPY")
        self.logger.info(f"Profit Factor:   {stats['profit_factor']:.2f}")
        self.logger.info("")
        self.logger.info(f"Max Drawdown:    {stats['max_drawdown']:,.0f} JPY ({stats['max_drawdown_pct']:.2f}%)")
        self.logger.info("")

    def _save_results(self, stats: Dict):
        """
        結果をデータベースに保存

        Args:
            stats: 統計情報
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            conn.set_client_encoding('UTF8')
            cursor = conn.cursor()

            # backtest_resultsテーブルに保存
            insert_query = """
                INSERT INTO backtest_results
                (symbol, start_date, end_date, ai_model,
                 initial_balance, final_balance, net_profit, return_pct,
                 total_trades, winning_trades, losing_trades, win_rate,
                 total_profit, total_loss, profit_factor,
                 max_drawdown, max_drawdown_pct,
                 statistics, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            cursor.execute(insert_query, (
                self.symbol,
                self.start_date.date(),
                self.end_date.date(),
                self.ai_model,
                stats['initial_balance'],
                stats['final_balance'],
                stats['net_profit'],
                stats['return_pct'],
                stats['total_trades'],
                stats['winning_trades'],
                stats['losing_trades'],
                stats['win_rate'],
                stats['total_profit'],
                stats['total_loss'],
                stats['profit_factor'],
                stats['max_drawdown'],
                stats['max_drawdown_pct'],
                Json(stats),
                datetime.now()
            ))

            conn.commit()
            cursor.close()
            conn.close()

            self.logger.info("Backtest results saved to database (backtest_results)")

        except Exception as e:
            self.logger.error(f"Failed to save backtest results: {e}")

    def _get_trades_for_date(self, target_date: date) -> List[Dict]:
        """
        特定日のトレード履歴を取得

        Args:
            target_date: 対象日

        Returns:
            トレードリスト
        """
        trades = []

        for trade in self.simulator.closed_positions:
            entry_time = trade.get('entry_time')
            if entry_time and entry_time.date() == target_date:
                trades.append({
                    'entry_time': entry_time.isoformat(),
                    'exit_time': trade.get('exit_time').isoformat() if trade.get('exit_time') else None,
                    'direction': trade.get('action'),
                    'entry_price': trade.get('entry_price'),
                    'exit_price': trade.get('exit_price'),
                    'pips': trade.get('profit_pips', 0),
                    'profit_loss': trade.get('profit', 0),
                    'exit_reason': trade.get('exit_reason', 'unknown')
                })

        return trades

    def _run_daily_review(
        self,
        previous_day_trades: List[Dict],
        review_date: date
    ) -> Optional[Dict]:
        """
        前日振り返りを実行

        Args:
            previous_day_trades: 前日のトレード履歴
            review_date: 振り返り対象日

        Returns:
            振り返り結果、失敗時はNone
        """
        try:
            from src.ai_analysis.ai_analyzer import AIAnalyzer

            # AIAnalyzer初期化
            analyzer = AIAnalyzer(
                symbol=self.symbol,
                model='pro',  # 振り返りはGemini Pro使用
                backtest_start_date=self.start_date.strftime('%Y-%m-%d'),
                backtest_end_date=self.end_date.strftime('%Y-%m-%d')
            )

            # 統計情報を生成
            total_pips = sum(t.get('pips', 0) for t in previous_day_trades)
            win_count = sum(1 for t in previous_day_trades if t.get('profit_loss', 0) > 0)
            total_count = len(previous_day_trades)
            win_rate = f"{(win_count / total_count * 100):.1f}%" if total_count > 0 else "0%"

            statistics = {
                'total_pips': total_pips,
                'win_rate': win_rate,
                'total_trades': total_count,
                'win_trades': win_count,
                'loss_trades': total_count - win_count
            }

            # 振り返り実行
            review_result = analyzer.daily_review(
                previous_day_trades=previous_day_trades,
                prediction=None,  # TODO: 前日の予測を保存して使用
                actual_market=None,  # TODO: 実際の市場動向を計算
                statistics=statistics
            )

            return review_result

        except Exception as e:
            self.logger.error(f"Daily review failed: {e}")
            return None

    def _run_morning_analysis(
        self,
        current_date: date,
        review_result: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        朝の詳細分析を実行（08:00、Gemini Pro）

        Args:
            current_date: 分析対象日
            review_result: 前日の振り返り結果（06:00で取得）

        Returns:
            戦略結果、失敗時はNone
        """
        try:
            from src.ai_analysis.ai_analyzer import AIAnalyzer

            # AIAnalyzer初期化
            analyzer = AIAnalyzer(
                symbol=self.symbol,
                model='pro',  # 朝の分析はGemini Pro使用
                backtest_start_date=self.start_date.strftime('%Y-%m-%d'),
                backtest_end_date=self.end_date.strftime('%Y-%m-%d')
            )

            # 市場データを取得（標準化済みデータ）
            market_analysis = analyzer.analyze_market()

            # analyze_marketから標準化データを抽出するため、
            # 一時的に直接データパイプラインを実行
            # TODO: より効率的な方法に改善（データを2重取得している）
            tick_data = analyzer._load_tick_data()
            if not tick_data:
                self.logger.error("Failed to load tick data for morning analysis")
                return None

            timeframe_data = analyzer._convert_timeframes(tick_data)
            if not timeframe_data:
                self.logger.error("Failed to convert timeframes for morning analysis")
                return None

            indicators = analyzer._calculate_indicators(timeframe_data)
            if not indicators:
                self.logger.error("Failed to calculate indicators for morning analysis")
                return None

            market_data = analyzer.data_standardizer.standardize_for_ai(
                timeframe_data=timeframe_data,
                indicators=indicators
            )
            market_data['symbol'] = self.symbol

            # 過去5日の統計を計算
            past_statistics = self._calculate_past_statistics(current_date, days=5)

            # 朝の詳細分析を実行
            strategy_result = analyzer.morning_analysis(
                market_data=market_data,
                review_result=review_result,
                past_statistics=past_statistics
            )

            return strategy_result

        except Exception as e:
            self.logger.error(f"Morning analysis failed: {e}", exc_info=True)
            return None

    def _run_periodic_update(
        self,
        current_date: date,
        update_time: str,  # "12:00", "16:00", "21:30"
        morning_strategy: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        定期更新を実行（12:00/16:00/21:30、Gemini Flash）

        Args:
            current_date: 更新対象日
            update_time: 更新時刻（"12:00", "16:00", "21:30"）
            morning_strategy: 朝の戦略（または前回の更新結果）

        Returns:
            更新後の戦略、失敗時は元の戦略を返す
        """
        try:
            from src.ai_analysis.ai_analyzer import AIAnalyzer

            if not morning_strategy:
                self.logger.warning(f"No morning strategy available for {update_time} update")
                return None

            # AIAnalyzer初期化（Gemini Flash使用）
            analyzer = AIAnalyzer(
                symbol=self.symbol,
                model='flash',  # 定期更新はGemini Flash使用（コスト削減）
                backtest_start_date=self.start_date.strftime('%Y-%m-%d'),
                backtest_end_date=self.end_date.strftime('%Y-%m-%d')
            )

            # 現在の市場データを取得
            tick_data = analyzer._load_tick_data()
            if not tick_data:
                self.logger.warning(f"Failed to load tick data for {update_time} update")
                return morning_strategy

            timeframe_data = analyzer._convert_timeframes(tick_data)
            if not timeframe_data:
                self.logger.warning(f"Failed to convert timeframes for {update_time} update")
                return morning_strategy

            indicators = analyzer._calculate_indicators(timeframe_data)
            if not indicators:
                self.logger.warning(f"Failed to calculate indicators for {update_time} update")
                return morning_strategy

            current_market_data = analyzer.data_standardizer.standardize_for_ai(
                timeframe_data=timeframe_data,
                indicators=indicators
            )
            current_market_data['symbol'] = self.symbol

            # 本日のトレード履歴を取得
            today_trades = self._get_trades_for_date(current_date)

            # 現在のポジション状況を取得
            current_positions = []
            for pos in self.simulator.open_positions:
                current_positions.append({
                    'direction': pos.get('action'),
                    'entry_price': pos.get('entry_price'),
                    'entry_time': pos.get('entry_time').isoformat() if pos.get('entry_time') else None,
                    'current_profit_pips': pos.get('unrealized_pips', 0),
                    'stop_loss': pos.get('stop_loss'),
                    'take_profit': pos.get('take_profit')
                })

            # 定期更新を実行
            update_result = analyzer.periodic_update(
                morning_strategy=morning_strategy,
                current_market_data=current_market_data,
                today_trades=today_trades,
                current_positions=current_positions,
                update_time=update_time
            )

            if update_result:
                self.logger.info(
                    f"{update_time} update completed. "
                    f"Type: {update_result.get('update_type', 'N/A')}, "
                    f"Summary: {update_result.get('summary', 'N/A')[:50]}..."
                )

                # 推奨変更を適用して戦略を更新
                updated_strategy = self._apply_periodic_changes(
                    morning_strategy,
                    update_result,
                    current_date,
                    update_time
                )

                return updated_strategy

            return morning_strategy

        except Exception as e:
            self.logger.error(f"Periodic update failed at {update_time}: {e}", exc_info=True)
            return morning_strategy

    def _apply_periodic_changes(
        self,
        current_strategy: Dict,
        update_result: Dict,
        current_date: date,
        update_time: str
    ) -> Dict:
        """
        定期更新の推奨変更を現在の戦略に適用

        Args:
            current_strategy: 現在の戦略
            update_result: 定期更新結果
            current_date: 更新日
            update_time: 更新時刻

        Returns:
            更新後の戦略
        """
        updated_strategy = current_strategy.copy()
        recommended_changes = update_result.get('recommended_changes', {})

        # バイアス変更の適用
        bias_change = recommended_changes.get('bias', {})
        if bias_change.get('apply', False):
            old_bias = updated_strategy.get('daily_bias', 'NEUTRAL')
            new_bias = bias_change.get('to', old_bias)
            updated_strategy['daily_bias'] = new_bias
            self.logger.info(f"{update_time}: Bias changed from {old_bias} to {new_bias}")

        # リスク管理の調整
        risk_changes = recommended_changes.get('risk_management', {})
        if 'position_size_multiplier' in risk_changes:
            multiplier = risk_changes['position_size_multiplier']
            if multiplier.get('apply', False):
                old_value = updated_strategy.get('risk_management', {}).get('position_size_multiplier', 1.0)
                new_value = multiplier.get('to', old_value)
                if 'risk_management' not in updated_strategy:
                    updated_strategy['risk_management'] = {}
                updated_strategy['risk_management']['position_size_multiplier'] = new_value
                self.logger.info(
                    f"{update_time}: Position size multiplier changed from {old_value} to {new_value}"
                )

        # 決済戦略の調整
        exit_changes = recommended_changes.get('exit_strategy', {})
        if exit_changes.get('stop_loss', {}).get('apply', False):
            sl_action = exit_changes['stop_loss'].get('action')
            self.logger.info(f"{update_time}: Stop loss adjustment: {sl_action}")

        # 既存ポジションのアクション
        positions_action = update_result.get('current_positions_action', {})
        if not positions_action.get('keep_open', True):
            close_reason = positions_action.get('close_reason', '定期更新による決済')
            self.logger.info(f"{update_time}: Closing all positions - {close_reason}")
            self.simulator.close_all_positions(reason=close_reason)

        # 新規エントリー推奨
        entry_rec = update_result.get('new_entry_recommendation', {})
        if entry_rec.get('should_enter_now', False):
            direction = entry_rec.get('direction')
            if direction and direction != 'NEUTRAL':
                self.logger.info(
                    f"{update_time}: New entry recommended - {direction} - {entry_rec.get('reason', '')}"
                )
                # 新規エントリー用に戦略を更新
                if 'entry_conditions' not in updated_strategy:
                    updated_strategy['entry_conditions'] = {}
                updated_strategy['entry_conditions']['should_trade'] = True
                updated_strategy['entry_conditions']['direction'] = direction

                # エントリー実行
                current_time = datetime.combine(current_date, datetime.min.time())
                self._execute_trade_from_strategy(updated_strategy, current_time)

        return updated_strategy

    def _calculate_past_statistics(self, current_date: date, days: int = 5) -> Dict:
        """
        過去N日の統計を計算

        Args:
            current_date: 基準日
            days: 過去何日分

        Returns:
            統計情報の辞書
        """
        try:
            # 過去N日のトレードを収集
            past_trades = []
            for i in range(1, days + 1):
                target_date = current_date - timedelta(days=i)
                trades = self._get_trades_for_date(target_date)
                past_trades.extend(trades)

            if not past_trades:
                return {
                    'last_5_days': {
                        'total_pips': 0,
                        'win_rate': '0%',
                        'avg_holding_time': '0分',
                        'total_trades': 0
                    }
                }

            # 統計計算
            total_pips = sum(t.get('pips', 0) for t in past_trades)
            win_count = sum(1 for t in past_trades if t.get('profit_loss', 0) > 0)
            total_count = len(past_trades)
            win_rate = f"{(win_count / total_count * 100):.1f}%" if total_count > 0 else "0%"

            # 平均保有時間計算（分）
            holding_times = []
            for t in past_trades:
                if t.get('entry_time') and t.get('exit_time'):
                    from datetime import datetime
                    entry = datetime.fromisoformat(t['entry_time'])
                    exit_time = datetime.fromisoformat(t['exit_time'])
                    holding_minutes = (exit_time - entry).total_seconds() / 60
                    holding_times.append(holding_minutes)

            avg_holding_time = sum(holding_times) / len(holding_times) if holding_times else 0

            return {
                'last_5_days': {
                    'total_pips': total_pips,
                    'win_rate': win_rate,
                    'avg_holding_time': f'{avg_holding_time:.0f}分',
                    'total_trades': total_count,
                    'win_trades': win_count,
                    'loss_trades': total_count - win_count
                }
            }

        except Exception as e:
            self.logger.error(f"Failed to calculate past statistics: {e}")
            return {'last_5_days': {}}

    def _execute_trade_from_strategy(self, strategy: Dict, timestamp: datetime):
        """
        朝の戦略に基づいてトレードを実行

        Args:
            strategy: 朝の分析で生成された戦略
            timestamp: 実行時刻
        """
        try:
            entry_conditions = strategy.get('entry_conditions', {})

            if not entry_conditions.get('should_trade', False):
                return

            # 戦略から必要な情報を抽出
            direction = entry_conditions.get('direction', 'NEUTRAL')
            if direction == 'NEUTRAL':
                return

            # エントリー条件をAI判断形式に変換
            ai_result = {
                'action': direction,  # BUY or SELL
                'confidence': int(strategy.get('confidence', 0.5) * 100),  # 0.75 -> 75
                'reasoning': strategy.get('reasoning', '朝の戦略に基づくエントリー'),
                'symbol': self.symbol,
                'timestamp': timestamp.isoformat(),
                'model': 'pro',
                'entry_conditions': entry_conditions,
                'exit_strategy': strategy.get('exit_strategy', {}),
                'risk_management': strategy.get('risk_management', {})
            }

            # 既存のトレード実行メソッドを利用
            self._execute_trade(ai_result, timestamp)

        except Exception as e:
            self.logger.error(f"Failed to execute trade from strategy: {e}")


# モジュールのエクスポート
__all__ = ['BacktestEngine']
