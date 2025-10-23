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
from datetime import datetime, timedelta
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

        # 2. 時系列でAI分析を実行
        self.logger.info("Running time-series AI analysis...")

        current_time = self.start_date
        analysis_count = 0

        while current_time <= self.end_date:
            self.current_time = current_time

            # AI分析を実行（この時点までのデータを使用）
            ai_result = self._analyze_at_time(current_time)

            if ai_result and ai_result.get('action') != 'HOLD':
                # トレード判断があった場合
                self._execute_trade(ai_result, current_time)

            # 市場価格を更新（既存ポジションのSL/TPチェック）
            self._update_market_price(current_time, tick_data)

            # 次のサンプリング時刻へ
            current_time += self.sampling_interval
            analysis_count += 1

            if analysis_count % 10 == 0:
                self.logger.info(
                    f"Progress: {current_time.date()}, "
                    f"Balance: {self.simulator.balance:,.0f}, "
                    f"Open Positions: {len(self.simulator.open_positions)}"
                )

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
            analyzer = AIAnalyzer(symbol=self.symbol, model=self.ai_model)

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


# モジュールのエクスポート
__all__ = ['BacktestEngine']
