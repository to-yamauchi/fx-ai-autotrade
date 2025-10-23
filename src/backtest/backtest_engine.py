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
        symbol: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        initial_balance: Optional[float] = None,
        ai_model: str = 'flash',
        sampling_interval_hours: int = 24,  # サンプリング間隔（時間）
        risk_percent: Optional[float] = None,
        csv_path: Optional[str] = None,  # CSVファイルパス（指定時はCSVを使用）
        skip_api_check: bool = False  # API接続チェックをスキップ（リセット専用時など）
    ):
        """
        バックテストエンジンの初期化

        Args:
            symbol: 通貨ペア（Noneの場合は.envから取得）
            start_date: 開始日（YYYY-MM-DD、Noneの場合は.envから取得）
            end_date: 終了日（YYYY-MM-DD、Noneの場合は.envから取得）
            initial_balance: 初期残高（Noneの場合は.envから取得）
            ai_model: AIモデル（flash/pro/flash-8b）
            sampling_interval_hours: AI分析のサンプリング間隔（時間）
            risk_percent: リスク許容率（%、Noneの場合は.envから取得）
            csv_path: CSVファイルパス（指定時はCSVからデータ読み込み、未指定時はMT5または.envから取得）
            skip_api_check: API接続チェックをスキップ（リセット専用時など、デフォルト: False）
        """
        from src.utils.config import get_config

        # 設定を読み込み
        config = get_config()

        # パラメータのデフォルト値を.envから取得
        self.symbol = symbol if symbol is not None else config.backtest_symbol
        self.start_date = datetime.strptime(
            start_date if start_date is not None else config.backtest_start_date,
            '%Y-%m-%d'
        )
        self.end_date = datetime.strptime(
            end_date if end_date is not None else config.backtest_end_date,
            '%Y-%m-%d'
        )
        self.initial_balance = initial_balance if initial_balance is not None else config.backtest_initial_balance
        self.ai_model = ai_model
        self.sampling_interval = timedelta(hours=sampling_interval_hours)
        self.risk_percent = risk_percent if risk_percent is not None else config.risk_per_trade
        self.csv_path = csv_path if csv_path is not None else config.backtest_csv_path
        self.logger = logging.getLogger(__name__)

        # コンポーネント初期化
        self.simulator = TradeSimulator(initial_balance=self.initial_balance, symbol=self.symbol)

        # データローダー：CSVまたはMT5
        if self.csv_path:
            self.data_loader = CSVTickLoader(csv_path=self.csv_path, symbol=self.symbol)
            self.use_csv = True
        else:
            self.data_loader = MT5DataLoader(symbol=self.symbol)
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

        # Gemini API接続チェック（skip_api_check=Trueの場合はスキップ）
        if not skip_api_check:
            try:
                from src.ai_analysis import GeminiClient
                self.gemini_client = GeminiClient()

                # .envで指定されたモデルを使用して接続テスト
                if not self.gemini_client.test_connection(verbose=True):
                    print("")
                    print("Gemini APIへの接続に失敗しました。")
                    print("以下を確認してください：")
                    print("  1. .envファイルにGEMINI_API_KEYが設定されているか")
                    print("  2. Geminiモデル名が正しいか")
                    print("  3. インターネット接続が正常か")
                    print("")
                    raise ConnectionError("Gemini API connection failed")

                # 使用するGeminiモデルを表示
                print("")
                print("🤖 使用AIモデル:")
                print(f"   Phase 1&2 (デイリーレビュー・朝の分析): {self.gemini_client.config.gemini_model_pro}")
                print(f"   Phase 3   (定期更新 12:00/16:00/21:30): {self.gemini_client.config.gemini_model_flash}")
                print(f"   Phase 4   (Layer 3a監視 15分ごと):      {self.gemini_client.config.gemini_model_flash_8b}")

            except Exception as e:
                if "ConnectionError" not in str(type(e).__name__):
                    print(f" ❌ エラー: {e}")
                raise
        else:
            # API接続スキップ時はGeminiClientを初期化しない
            self.gemini_client = None

        self.logger.debug(
            f"BacktestEngine initialized: "
            f"{start_date} to {end_date}, "
            f"model={ai_model}, "
            f"sampling={sampling_interval_hours}h"
        )

    def reset_backtest_tables(self, confirm: bool = True) -> bool:
        """
        バックテスト用テーブルのデータをリセット（削除）

        指定されたバックテスト期間のデータのみを削除します。
        安全のため、デフォルトでは確認プロンプトを表示します。

        Args:
            confirm: 確認プロンプトを表示するか（デフォルト: True）

        Returns:
            成功時True、キャンセルまたは失敗時False
        """
        # 確認プロンプト
        if confirm:
            print("")
            print("⚠️  バックテストデータのリセット")
            print("=" * 60)
            print(f"期間: {self.start_date.date()} ～ {self.end_date.date()}")
            print(f"通貨ペア: {self.symbol}")
            print("")
            print("以下のテーブルから該当期間のデータを削除します：")
            print("  - backtest_daily_strategies")
            print("  - backtest_periodic_updates")
            print("  - backtest_layer3a_monitoring")
            print("  - backtest_layer3b_emergency")
            print("  - backtest_results")
            print("")
            response = input("削除を実行しますか？ (yes/no): ").strip().lower()
            if response not in ['yes', 'y']:
                print("キャンセルされました。")
                return False

        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()

            deleted_counts = {}

            # 各テーブルから該当期間のデータを削除
            tables = [
                'backtest_daily_strategies',
                'backtest_periodic_updates',
                'backtest_layer3a_monitoring',
                'backtest_layer3b_emergency',
                'backtest_results'
            ]

            print("")
            print("🗑️  データ削除中...")

            for table in tables:
                try:
                    delete_query = f"""
                        DELETE FROM {table}
                        WHERE symbol = %s
                        AND backtest_start_date = %s
                        AND backtest_end_date = %s
                    """
                    cursor.execute(delete_query, (
                        self.symbol,
                        self.start_date.date(),
                        self.end_date.date()
                    ))
                    deleted_counts[table] = cursor.rowcount
                except Exception as e:
                    # テーブルが存在しない、またはカラム構成が異なる場合
                    self.logger.warning(f"Table {table} skip: {e}")
                    deleted_counts[table] = 0

            conn.commit()
            cursor.close()
            conn.close()

            # 結果表示
            print("")
            print("✓ 削除完了")
            print("-" * 60)
            total_deleted = 0
            for table, count in deleted_counts.items():
                if count > 0:
                    print(f"  {table:<35} {count:>5}件")
                    total_deleted += count

            if total_deleted == 0:
                print("  削除対象のデータはありませんでした。")
            else:
                print("-" * 60)
                print(f"  合計: {total_deleted}件")
            print("")

            self.logger.info(
                f"Backtest tables reset: {self.symbol} "
                f"{self.start_date.date()} to {self.end_date.date()}, "
                f"deleted {total_deleted} records"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to reset backtest tables: {e}")
            print(f"❌ エラー: {e}")
            return False

    def reset_all_backtest_tables(self, confirm: bool = True, symbol: Optional[str] = None) -> bool:
        """
        backtest_で始まる全テーブルのデータをリセット（全削除）

        全てのバックテスト実行結果を削除します。
        オプションで特定の通貨ペアのみ削除可能（symbolカラムがあるテーブルのみ）。

        Args:
            confirm: 確認プロンプトを表示するか（デフォルト: True）
            symbol: 特定の通貨ペアのみ削除（Noneの場合は全通貨ペア）

        Returns:
            成功時True、キャンセルまたは失敗時False
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()

            # backtest_で始まる全テーブルを取得
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name LIKE 'backtest_%'
                ORDER BY table_name
            """)

            tables = [row[0] for row in cursor.fetchall()]

            if not tables:
                print("backtest_テーブルが見つかりませんでした。")
                return False

            # 確認プロンプト
            if confirm:
                print("")
                print("⚠️  ⚠️  ⚠️  全バックテストデータの削除  ⚠️  ⚠️  ⚠️")
                print("=" * 60)
                if symbol:
                    print(f"通貨ペア: {symbol} のみ")
                else:
                    print("対象: 全通貨ペア、全期間")
                print("")
                print("以下のテーブルから全データを削除します：")
                for table in tables:
                    print(f"  - {table}")
                print("")
                print("⚠️  この操作は取り消せません！")
                print("")
                response = input("本当に削除しますか？ (yes/no): ").strip().lower()
                if response not in ['yes', 'y']:
                    print("キャンセルされました。")
                    return False

            deleted_counts = {}
            print("")
            print("🗑️  データ削除中...")

            for table in tables:
                try:
                    # テーブルにsymbolカラムがあるか確認
                    cursor.execute(f"""
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_name = '{table}'
                        AND column_name = 'symbol'
                    """)
                    has_symbol = cursor.fetchone() is not None

                    # 削除クエリを構築
                    if symbol and has_symbol:
                        delete_query = f"DELETE FROM {table} WHERE symbol = %s"
                        cursor.execute(delete_query, (symbol,))
                    else:
                        # symbolカラムがない、またはsymbol指定なしの場合は全削除
                        delete_query = f"TRUNCATE TABLE {table} CASCADE"
                        cursor.execute(delete_query)

                    deleted_counts[table] = cursor.rowcount
                except Exception as e:
                    self.logger.warning(f"Table {table} deletion failed: {e}")
                    deleted_counts[table] = 0

            conn.commit()
            cursor.close()
            conn.close()

            # 結果表示
            print("")
            print("✓ 削除完了")
            print("-" * 60)
            total_deleted = 0
            for table, count in deleted_counts.items():
                # TRUNCATEの場合rowcountは0になるため、その場合は「全削除」と表示
                if count == 0 and deleted_counts[table] == 0:
                    print(f"  {table:<35} 全削除")
                elif count > 0:
                    print(f"  {table:<35} {count:>5}件")
                    total_deleted += count

            if total_deleted == 0:
                print("  削除対象のデータはありませんでした。")
            else:
                print("-" * 60)
                print(f"  合計: {total_deleted}件")
            print("")

            symbol_msg = f" (symbol={symbol})" if symbol else " (all symbols)"
            self.logger.info(f"All backtest tables reset{symbol_msg}, deleted {total_deleted} records")
            return True

        except Exception as e:
            self.logger.error(f"Failed to reset all backtest tables: {e}")
            print(f"❌ エラー: {e}")
            return False

    def run(self) -> Dict:
        """
        バックテストを実行

        Returns:
            バックテスト結果の統計情報
        """
        print("=" * 80)
        print("バックテスト開始")
        print("=" * 80)
        print(f"期間: {self.start_date.date()} ～ {self.end_date.date()}")
        print(f"初期残高: {self.initial_balance:,.0f}円")
        print(f"AIモデル: {self.ai_model}")
        print("")

        # 1. 全期間のデータを取得
        print("📊 データ読み込み中...")

        if self.use_csv:
            # CSVファイルから読み込み（AI分析用に30日のバッファを含む）
            tick_df = self.data_loader.load_ticks(
                start_date=self.start_date.strftime('%Y-%m-%d'),
                end_date=self.end_date.strftime('%Y-%m-%d'),
                history_days=30  # AI分析に必要な過去データ
            )
        else:
            # MT5から読み込み
            days = (self.end_date - self.start_date).days
            tick_df = self.data_loader.load_recent_ticks(days=days + 30)

        if tick_df is None or tick_df.empty:
            self.logger.error("❌ データ読み込み失敗")
            return {}

        # DataFrameをリストに変換
        tick_data = []
        for idx, row in tick_df.iterrows():
            tick_data.append({
                'time': row['timestamp'],  # カラム名は'timestamp'
                'bid': row['bid'],
                'ask': row['ask']
            })

        print(f"✓ {len(tick_data):,}ティック読み込み完了")
        print("")

        # 2. 日ごとのループでバックテスト実行
        print("🔄 バックテスト実行中...")
        print("=" * 80)

        current_date = self.start_date.date()
        end_date = self.end_date.date()
        day_count = 0
        review_result = None  # 前日の振り返り結果
        strategy_result = None  # 本日の戦略

        while current_date <= end_date:
            # トレード前のポジション数と残高を記録
            positions_before = len(self.simulator.open_positions)
            balance_before = self.simulator.balance

            # === 06:00 前日振り返り（初日以外） ===
            if day_count > 0:
                previous_day_trades = self._get_trades_for_date(current_date - timedelta(days=1))
                if previous_day_trades:
                    review_result = self._run_daily_review(
                        previous_day_trades,
                        current_date - timedelta(days=1)
                    )

            # === 08:00 朝の詳細分析（Gemini Pro） ===
            strategy_result = self._run_morning_analysis(
                current_date=current_date,
                review_result=review_result
            )

            # 戦略情報を記録
            bias = 'N/A'
            should_trade = False
            if strategy_result:
                bias = strategy_result.get('daily_bias', 'N/A')
                should_trade = strategy_result.get('entry_conditions', {}).get('should_trade', False)

            # 朝の戦略に基づいてトレード判断
            current_time = datetime.combine(current_date, datetime.min.time())
            if strategy_result and should_trade:
                self._execute_trade_from_strategy(strategy_result, current_time)

            # === 12:00/16:00/21:30 定期更新（Gemini Flash） ===
            strategy_result = self._run_periodic_update(
                current_date=current_date,
                update_time="12:00",
                morning_strategy=strategy_result
            )

            strategy_result = self._run_periodic_update(
                current_date=current_date,
                update_time="16:00",
                morning_strategy=strategy_result
            )

            strategy_result = self._run_periodic_update(
                current_date=current_date,
                update_time="21:30",
                morning_strategy=strategy_result
            )

            # === 市場価格を更新 + Layer 3監視 ===
            # 当日の全ティックをチェック、15分ごとにLayer 3a監視実行
            next_date = current_date + timedelta(days=1)
            last_monitor_time = None
            monitor_interval = timedelta(minutes=15)
            layer3a_count = 0
            layer3b_count = 0

            for tick in tick_data:
                tick_time = tick['time']
                if current_date <= tick_time.date() < next_date:
                    # 市場価格を更新
                    self.simulator.update_market_price(
                        bid=tick['bid'],
                        ask=tick['ask']
                    )

                    # === Phase 4: Layer 3a監視（15分ごと、ポジション保有時） ===
                    if self.simulator.open_positions:
                        if last_monitor_time is None or (tick_time - last_monitor_time) >= monitor_interval:
                            self._run_layer3a_monitoring(
                                tick_time=tick_time,
                                current_price={'bid': tick['bid'], 'ask': tick['ask']},
                                daily_strategy=strategy_result
                            )
                            last_monitor_time = tick_time
                            layer3a_count += 1

                    # === Phase 5: Layer 3b緊急評価（異常検知時） ===
                    anomaly = self._detect_anomaly(
                        tick_time=tick_time,
                        current_price={'bid': tick['bid'], 'ask': tick['ask']}
                    )
                    if anomaly:
                        self._run_layer3b_emergency(
                            anomaly_info=anomaly,
                            tick_time=tick_time,
                            current_price={'bid': tick['bid'], 'ask': tick['ask']},
                            daily_strategy=strategy_result
                        )
                        layer3b_count += 1

            # トレード後のポジション数と残高を確認
            positions_after = len(self.simulator.open_positions)
            balance_after = self.simulator.balance
            new_entries = max(0, positions_after - positions_before)
            new_exits = max(0, positions_before - positions_after)
            balance_change = balance_after - balance_before

            # 1行サマリー出力
            summary_parts = [
                f"📅 {current_date.strftime('%Y-%m-%d')}",
                f"バイアス:{bias}",
            ]

            # トレードがあった場合のみ詳細を追加
            if new_entries > 0 or new_exits > 0:
                summary_parts.append(f"新規:{new_entries}件")
                summary_parts.append(f"決済:{new_exits}件")
                if balance_change != 0:
                    change_sign = '+' if balance_change > 0 else ''
                    summary_parts.append(f"損益:{change_sign}{balance_change:,.0f}円")

            summary_parts.append(f"残高:{balance_after:,.0f}円")
            summary_parts.append(f"ポジション:{positions_after}個")

            # 緊急対応があった場合は警告表示
            if layer3b_count > 0:
                summary_parts.append(f"⚠️緊急:{layer3b_count}回")

            print(" | ".join(summary_parts))

            # 次の日へ
            current_date += timedelta(days=1)
            day_count += 1

        # 3. すべてのポジションをクローズ
        print("")
        print("=" * 80)
        print("バックテスト完了")
        print("=" * 80)
        print("")

        self.simulator.close_all_positions(reason='Backtest end')

        # 4. 統計を取得
        stats = self.simulator.get_statistics()

        # 5. 結果をログ出力
        self._print_results(stats)

        # 6. データベースに保存
        self._save_results(stats)

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
            error_msg = f"❌ AI分析エラー ({timestamp}): {e}"
            self.logger.error(error_msg, exc_info=True)
            print(error_msg)
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
        print("")
        print("=" * 80)
        print("📊 バックテスト結果")
        print("=" * 80)
        print("")
        print(f"期間: {self.start_date.date()} ～ {self.end_date.date()} ({(self.end_date - self.start_date).days}日間)")
        print("")
        print(f"初期残高:     {stats['initial_balance']:>12,.0f}円")
        print(f"最終残高:     {stats['final_balance']:>12,.0f}円")
        print(f"損益:         {stats['net_profit']:>12,.0f}円")
        print(f"リターン:     {stats['return_pct']:>11.2f}%")
        print("")
        print(f"総トレード数: {stats['total_trades']:>12,}回")
        print(f"勝ちトレード: {stats['winning_trades']:>12,}回")
        print(f"負けトレード: {stats['losing_trades']:>12,}回")
        print(f"勝率:         {stats['win_rate']:>11.2f}%")
        print("")
        print(f"総利益:       {stats['total_profit']:>12,.0f}円")
        print(f"総損失:       {stats['total_loss']:>12,.0f}円")
        print(f"平均利益:     {stats['avg_profit']:>12,.0f}円")
        print(f"平均損失:     {stats['avg_loss']:>12,.0f}円")
        print(f"プロフィット" f"ファクター: {stats['profit_factor']:>8.2f}")
        print("")
        print(f"最大ドロー" f"ダウン:   {stats['max_drawdown']:>12,.0f}円 ({stats['max_drawdown_pct']:.2f}%)")
        print("")

        # ログファイルにも記録
        self.logger.info(f"Backtest completed: Period={self.start_date.date()} to {self.end_date.date()}, "
                        f"Return={stats['return_pct']:.2f}%, Win Rate={stats['win_rate']:.2f}%")

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
            error_msg = f"❌ Phase 1エラー（デイリーレビュー失敗）: {e}"
            self.logger.error(error_msg, exc_info=True)
            print(error_msg)
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
                error_msg = "❌ Phase 2エラー（ティックデータ読み込み失敗）"
                self.logger.error(error_msg)
                print(error_msg)
                return None

            timeframe_data = analyzer._convert_timeframes(tick_data)
            if not timeframe_data:
                error_msg = "❌ Phase 2エラー（時間足変換失敗）"
                self.logger.error(error_msg)
                print(error_msg)
                return None

            indicators = analyzer._calculate_indicators(timeframe_data)
            if not indicators:
                error_msg = "❌ Phase 2エラー（テクニカル指標計算失敗）"
                self.logger.error(error_msg)
                print(error_msg)
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
            error_msg = f"❌ Phase 2エラー（朝の詳細分析失敗）: {e}"
            self.logger.error(error_msg, exc_info=True)
            print(error_msg)
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
            for ticket, pos in self.simulator.open_positions.items():
                current_positions.append({
                    'ticket': ticket,
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
            error_msg = f"❌ Phase 3エラー（定期更新失敗 {update_time}）: {e}"
            self.logger.error(error_msg, exc_info=True)
            print(error_msg)
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

    def _run_layer3a_monitoring(
        self,
        tick_time: datetime,
        current_price: Dict,
        daily_strategy: Optional[Dict] = None
    ):
        """
        Layer 3a監視を実行（15分ごと、ポジション保有時）

        Args:
            tick_time: 現在時刻
            current_price: 現在価格 {'bid': float, 'ask': float}
            daily_strategy: 本日の戦略
        """
        try:
            from src.ai_analysis.ai_analyzer import AIAnalyzer

            if not self.simulator.open_positions:
                return

            analyzer = AIAnalyzer(
                symbol=self.symbol,
                model='flash-8b',  # Flash-8B使用
                backtest_start_date=self.start_date.strftime('%Y-%m-%d'),
                backtest_end_date=self.end_date.strftime('%Y-%m-%d')
            )

            # 各ポジションを監視
            for ticket, position in self.simulator.open_positions.items():
                # ポジション情報を構築
                position_info = {
                    'ticket': ticket,
                    'direction': position.get('action'),
                    'entry_price': position.get('entry_price'),
                    'entry_time': position.get('entry_time').isoformat() if position.get('entry_time') else None,
                    'current_price': current_price.get('bid') if position.get('action') == 'BUY' else current_price.get('ask'),
                    'unrealized_pips': position.get('unrealized_pips', 0),
                    'stop_loss': position.get('stop_loss'),
                    'take_profit': position.get('take_profit')
                }

                # 簡易市場データ
                current_market = {
                    'price': current_price,
                    'timestamp': tick_time.isoformat()
                }

                # Layer 3a監視実行
                monitor_result = analyzer.layer3a_monitor(
                    position=position_info,
                    current_market_data=current_market,
                    daily_strategy=daily_strategy or {}
                )

                action = monitor_result.get('action', 'HOLD')

                if action == 'CLOSE_NOW':
                    self.logger.warning(
                        f"Layer 3a: CLOSE_NOW - {monitor_result.get('reason', 'No reason')}"
                    )
                    self.simulator.close_position(ticket, reason=f"Layer3a: {monitor_result.get('reason')}")

                elif action == 'PARTIAL_CLOSE':
                    close_percent = monitor_result.get('recommended_action', {}).get('close_percent', 50)
                    self.logger.info(
                        f"Layer 3a: PARTIAL_CLOSE {close_percent}% - {monitor_result.get('reason', 'No reason')}"
                    )
                    # TODO: 部分決済の実装（現在は全決済として扱う）
                    if close_percent >= 100:
                        self.simulator.close_position(ticket, reason=f"Layer3a partial: {monitor_result.get('reason')}")

                elif action == 'ADJUST_SL':
                    new_sl = monitor_result.get('recommended_action', {}).get('new_sl')
                    if new_sl:
                        self.logger.info(
                            f"Layer 3a: ADJUST_SL to {new_sl} - {monitor_result.get('reason', 'No reason')}"
                        )
                        position['stop_loss'] = new_sl

        except Exception as e:
            error_msg = f"❌ Phase 4エラー（Layer 3a監視失敗）: {e}"
            self.logger.error(error_msg, exc_info=True)
            print(error_msg)

    def _detect_anomaly(
        self,
        tick_time: datetime,
        current_price: Dict
    ) -> Optional[Dict]:
        """
        簡易的な異常検知（Layer 2の簡易版）

        Args:
            tick_time: 現在時刻
            current_price: 現在価格 {'bid': float, 'ask': float}

        Returns:
            異常検知情報、異常がなければNone
        """
        try:
            # 簡易的な異常検知ロジック
            # 実際のLayer 2実装では、より高度な検知を行う

            # 価格の急変動をチェック（前回の価格との比較）
            if not hasattr(self, '_last_price') or not hasattr(self, '_last_check_time'):
                self._last_price = current_price
                self._last_check_time = tick_time
                return None

            time_diff = (tick_time - self._last_check_time).total_seconds()
            if time_diff < 60:  # 1分未満はスキップ
                return None

            # 価格変動を計算（pips）
            price_change = abs(current_price['bid'] - self._last_price['bid'])
            price_change_pips = price_change * 100  # USDJPYの場合

            # 急激な変動を検知（1分で5pips以上の変動）
            if price_change_pips > 5:
                anomaly = {
                    'type': 'rapid_price_movement',
                    'severity': 'high' if price_change_pips > 10 else 'medium',
                    'details': {
                        'price_change_pips': price_change_pips,
                        'time_window': f'{time_diff:.0f}秒',
                        'from_price': self._last_price['bid'],
                        'to_price': current_price['bid']
                    },
                    'timestamp': tick_time.isoformat()
                }

                self._last_price = current_price
                self._last_check_time = tick_time

                return anomaly

            self._last_price = current_price
            self._last_check_time = tick_time
            return None

        except Exception as e:
            error_msg = f"❌ 異常検知エラー: {e}"
            self.logger.error(error_msg, exc_info=True)
            print(error_msg)
            return None

    def _run_layer3b_emergency(
        self,
        anomaly_info: Dict,
        tick_time: datetime,
        current_price: Dict,
        daily_strategy: Optional[Dict] = None
    ):
        """
        Layer 3b緊急評価を実行（異常検知時）

        Args:
            anomaly_info: 異常検知情報
            tick_time: 現在時刻
            current_price: 現在価格
            daily_strategy: 本日の戦略
        """
        try:
            from src.ai_analysis.ai_analyzer import AIAnalyzer

            self.logger.warning(
                f"ANOMALY DETECTED: {anomaly_info.get('type')} "
                f"(severity: {anomaly_info.get('severity')})"
            )

            analyzer = AIAnalyzer(
                symbol=self.symbol,
                model='pro',  # 緊急時はGemini Pro使用
                backtest_start_date=self.start_date.strftime('%Y-%m-%d'),
                backtest_end_date=self.end_date.strftime('%Y-%m-%d')
            )

            # 現在のポジション一覧
            current_positions = []
            for ticket, pos in self.simulator.open_positions.items():
                current_positions.append({
                    'ticket': ticket,
                    'direction': pos.get('action'),
                    'entry_price': pos.get('entry_price'),
                    'entry_time': pos.get('entry_time').isoformat() if pos.get('entry_time') else None,
                    'unrealized_pips': pos.get('unrealized_pips', 0),
                    'stop_loss': pos.get('stop_loss'),
                    'take_profit': pos.get('take_profit')
                })

            # 簡易市場データ
            current_market = {
                'price': current_price,
                'timestamp': tick_time.isoformat(),
                'anomaly_detected': True
            }

            # Layer 3b緊急評価実行
            emergency_result = analyzer.layer3b_emergency(
                anomaly_info=anomaly_info,
                current_positions=current_positions,
                current_market_data=current_market,
                daily_strategy=daily_strategy or {}
            )

            severity = emergency_result.get('severity', 'medium')
            action = emergency_result.get('action', 'CONTINUE')

            self.logger.warning(
                f"Layer 3b: Severity={severity}, Action={action} - "
                f"{emergency_result.get('reasoning', 'No reason')}"
            )

            # アクション実行
            if action == 'CLOSE_ALL':
                self.logger.warning("Layer 3b: Closing ALL positions!")
                self.simulator.close_all_positions(reason=f"Layer3b emergency: {emergency_result.get('reasoning')}")

            elif action == 'CLOSE_PARTIAL':
                # 50%決済（簡易実装：最初のポジションをクローズ）
                if self.simulator.open_positions:
                    self.logger.warning("Layer 3b: Closing PARTIAL positions (50%)")
                    positions_to_close = self.simulator.open_positions[:len(self.simulator.open_positions)//2 or 1]
                    for pos in positions_to_close:
                        self.simulator.close_position(pos, reason=f"Layer3b partial: {emergency_result.get('reasoning')}")

        except Exception as e:
            error_msg = f"❌ Phase 5エラー（Layer 3b緊急評価失敗）: {e}"
            self.logger.error(error_msg, exc_info=True)
            print(error_msg)
            # エラー時は安全のため全決済
            if self.simulator.open_positions:
                self.logger.error("Emergency: Closing all positions due to evaluation error")
                self.simulator.close_all_positions(reason="Layer3b evaluation error - safety close")

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
            error_msg = f"❌ トレード実行エラー: {e}"
            self.logger.error(error_msg, exc_info=True)
            print(error_msg)


# モジュールのエクスポート
__all__ = ['BacktestEngine']
