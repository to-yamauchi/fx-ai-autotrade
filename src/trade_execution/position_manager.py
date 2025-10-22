"""
========================================
ポジション管理モジュール
========================================

ファイル名: position_manager.py
パス: src/trade_execution/position_manager.py

【概要】
AI判断、ルールエンジン、MT5実行を統合管理するポジションマネージャーです。
トレードの実行から決済まで、全体のフローを制御します。

【主な機能】
1. AI判断の受理とルール検証
2. トレードの実行
3. ポジションの監視
4. ポジションの決済

【処理フロー】
AI判断 → ルール検証 → リスク計算 → MT5実行 → ポジション記録

【使用例】
```python
from src.trade_execution import PositionManager

manager = PositionManager()
result = manager.process_ai_judgment(ai_judgment)
```

【作成日】2025-10-22
"""

from typing import Dict, Optional, List
import logging
from datetime import datetime
import psycopg2
from psycopg2.extras import Json
import os

from src.rule_engine.trading_rules import TradingRules
from src.trade_execution.mt5_executor import MT5Executor


class PositionManager:
    """
    ポジション管理クラス

    AI判断からトレード実行、ポジション管理までを統合的に制御します。
    """

    def __init__(self,
                 symbol: str = 'USDJPY',
                 risk_percent: float = 1.0,
                 use_mt5: bool = True):
        """
        PositionManagerの初期化

        Args:
            symbol: 通貨ペア
            risk_percent: リスク許容率（%）
            use_mt5: MT5を使用するか（Falseの場合はデモモード）
        """
        self.symbol = symbol
        self.risk_percent = risk_percent
        self.use_mt5 = use_mt5
        self.logger = logging.getLogger(__name__)

        # ルールエンジンの初期化
        self.rules = TradingRules()

        # MT5実行エンジンの初期化
        if self.use_mt5:
            try:
                self.executor = MT5Executor(auto_login=True)
            except Exception as e:
                self.logger.error(f"MT5 initialization failed: {e}")
                self.executor = None
                self.use_mt5 = False
        else:
            self.executor = None

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
            f"PositionManager initialized: "
            f"symbol={symbol}, risk={risk_percent}%, mt5={use_mt5}"
        )

    def process_ai_judgment(self, ai_judgment: Dict) -> Dict:
        """
        AI判断を処理してトレードを実行

        【処理フロー】
        1. ルール検証
        2. スプレッド取得
        3. ポジション数確認
        4. ポジションサイズ計算
        5. トレード実行
        6. DB記録

        Args:
            ai_judgment: AI判断結果
                {
                    'action': 'BUY' | 'SELL' | 'HOLD',
                    'confidence': 0-100,
                    'reasoning': '判断理由',
                    'entry_price': エントリー価格,
                    'stop_loss': SL価格,
                    'take_profit': TP価格
                }

        Returns:
            実行結果
                {
                    'success': True/False,
                    'ticket': ticket番号 or None,
                    'message': メッセージ,
                    'validation': ルール検証結果
                }
        """
        self.logger.info(
            f"Processing AI judgment: {ai_judgment.get('action')} "
            f"(confidence: {ai_judgment.get('confidence')}%)"
        )

        # 1. 現在のポジション数を取得
        current_positions = self._get_current_positions_count()

        # 2. スプレッドを取得
        spread = self._get_spread()
        if spread is None:
            spread = 2.0  # デフォルト値

        # 3. ルール検証
        is_valid, validation_message = self.rules.validate_trade(
            ai_judgment=ai_judgment,
            current_positions=current_positions,
            spread=spread
        )

        result = {
            'success': False,
            'ticket': None,
            'message': validation_message,
            'validation': {
                'passed': is_valid,
                'reason': validation_message,
                'current_positions': current_positions,
                'spread': spread
            }
        }

        # ルール検証失敗
        if not is_valid:
            self.logger.warning(f"Trade validation failed: {validation_message}")
            self._save_trade_record(ai_judgment, result)
            return result

        # 4. ポジションサイズを計算
        position_size = self._calculate_position_size(ai_judgment)

        # 5. トレード実行
        if self.use_mt5 and self.executor:
            ticket = self._execute_trade(ai_judgment, position_size)
            if ticket:
                result['success'] = True
                result['ticket'] = ticket
                result['message'] = f"Trade executed successfully: ticket={ticket}"
                self.logger.info(result['message'])
            else:
                result['message'] = "Trade execution failed"
                self.logger.error(result['message'])
        else:
            # デモモード
            result['success'] = True
            result['ticket'] = 'DEMO'
            result['message'] = f"Demo mode: Would execute {ai_judgment['action']} {position_size} lots"
            self.logger.info(result['message'])

        # 6. DB記録
        self._save_trade_record(ai_judgment, result)

        return result

    def _get_current_positions_count(self) -> int:
        """現在のポジション数を取得"""
        if self.use_mt5 and self.executor:
            positions = self.executor.get_positions(symbol=self.symbol)
            # Magic Numberでフィルタ
            ai_positions = [p for p in positions if p['magic'] == MT5Executor.MAGIC_NUMBER]
            return len(ai_positions)
        else:
            # デモモード：DBから取得
            try:
                conn = psycopg2.connect(**self.db_config)
                # エンコーディングを明示的に設定
                conn.set_client_encoding('UTF8')
                cursor = conn.cursor()

                query = """
                    SELECT COUNT(*)
                    FROM positions
                    WHERE symbol = %s AND status = 'OPEN'
                """
                cursor.execute(query, (self.symbol,))
                count = cursor.fetchone()[0]

                cursor.close()
                conn.close()

                return count
            except Exception as e:
                # エラーメッセージの安全なデコード
                error_msg = str(e)
                try:
                    if isinstance(e.args[0] if e.args else '', bytes):
                        error_msg = e.args[0].decode('utf-8', errors='replace')
                except:
                    error_msg = repr(e)
                self.logger.error(f"Failed to get positions count: {error_msg}")
                return 0

    def _get_spread(self) -> Optional[float]:
        """現在のスプレッドを取得（pips）"""
        if self.use_mt5 and self.executor:
            return self.executor.get_spread(self.symbol)
        return None

    def _calculate_position_size(self, ai_judgment: Dict) -> float:
        """
        ポジションサイズを計算

        リスク管理に基づいて適切なロットサイズを算出
        """
        # SL価格を取得
        entry_price = ai_judgment.get('entry_price', 0)
        stop_loss = ai_judgment.get('stop_loss', 0)

        if entry_price == 0 or stop_loss == 0:
            # デフォルト：最小ロット
            return 0.01

        # SLまでのpips数を計算
        stop_loss_pips = abs(entry_price - stop_loss) * 100  # USDJPY想定

        # 口座残高を取得
        if self.use_mt5 and self.executor:
            account_info = self.executor.get_account_info()
            if account_info:
                balance = account_info['balance']
            else:
                balance = 100000  # デフォルト
        else:
            balance = 100000  # デモモード

        # ポジションサイズを計算
        position_size = self.rules.calculate_position_size(
            account_balance=balance,
            risk_percent=self.risk_percent,
            stop_loss_pips=stop_loss_pips,
            pip_value=1000.0  # USDJPY 0.01ロット = 1000円
        )

        return position_size

    def _execute_trade(self, ai_judgment: Dict, volume: float) -> Optional[int]:
        """
        MT5でトレードを実行

        Args:
            ai_judgment: AI判断結果
            volume: ロット数

        Returns:
            ticket番号、失敗時はNone
        """
        if not self.executor:
            return None

        action = ai_judgment['action']
        sl = ai_judgment.get('stop_loss')
        tp = ai_judgment.get('take_profit')

        ticket = self.executor.execute_trade(
            symbol=self.symbol,
            action=action,
            volume=volume,
            sl=sl,
            tp=tp,
            comment=f"AI Trade (Confidence: {ai_judgment.get('confidence')}%)"
        )

        return ticket

    def _save_trade_record(self, ai_judgment: Dict, result: Dict) -> bool:
        """
        トレード記録をDBに保存

        Args:
            ai_judgment: AI判断
            result: 実行結果

        Returns:
            True: 保存成功, False: 保存失敗
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            # エンコーディングを明示的に設定
            conn.set_client_encoding('UTF8')
            cursor = conn.cursor()

            # positionsテーブルに保存
            if result['success'] and result['ticket'] != 'DEMO':
                insert_query = """
                    INSERT INTO positions
                    (ticket, symbol, type, volume, open_price, sl, tp, open_time, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """

                cursor.execute(insert_query, (
                    result['ticket'],
                    self.symbol,
                    ai_judgment['action'],
                    0.01,  # ダミー値（実際はMT5から取得すべき）
                    ai_judgment.get('entry_price', 0),
                    ai_judgment.get('stop_loss'),
                    ai_judgment.get('take_profit'),
                    datetime.now(),
                    'OPEN'
                ))

            conn.commit()
            cursor.close()
            conn.close()

            return True

        except Exception as e:
            # エラーメッセージの安全なデコード
            error_msg = str(e)
            try:
                if isinstance(e.args[0] if e.args else '', bytes):
                    error_msg = e.args[0].decode('utf-8', errors='replace')
            except:
                error_msg = repr(e)
            self.logger.error(f"Failed to save trade record: {error_msg}")
            return False

    def get_open_positions(self) -> List[Dict]:
        """
        オープンポジションを取得

        Returns:
            ポジションリスト
        """
        if self.use_mt5 and self.executor:
            return self.executor.get_positions(symbol=self.symbol)
        else:
            # デモモード：DBから取得
            try:
                conn = psycopg2.connect(**self.db_config)
                # エンコーディングを明示的に設定
                conn.set_client_encoding('UTF8')
                cursor = conn.cursor()

                query = """
                    SELECT ticket, symbol, type, volume, open_price, sl, tp, open_time, profit
                    FROM positions
                    WHERE symbol = %s AND status = 'OPEN'
                    ORDER BY open_time DESC
                """
                cursor.execute(query, (self.symbol,))
                rows = cursor.fetchall()

                positions = []
                for row in rows:
                    # テキストフィールドの安全なデコード
                    try:
                        ticket = row[0] if not isinstance(row[0], bytes) else row[0].decode('utf-8', errors='replace')
                        symbol = row[1] if not isinstance(row[1], bytes) else row[1].decode('utf-8', errors='replace')
                        trade_type = row[2] if not isinstance(row[2], bytes) else row[2].decode('utf-8', errors='replace')
                    except:
                        ticket = str(row[0])
                        symbol = str(row[1])
                        trade_type = str(row[2])

                    positions.append({
                        'ticket': ticket,
                        'symbol': symbol,
                        'type': trade_type,
                        'volume': float(row[3]),
                        'open_price': float(row[4]),
                        'sl': float(row[5]) if row[5] else None,
                        'tp': float(row[6]) if row[6] else None,
                        'open_time': row[7],
                        'profit': float(row[8]) if row[8] else 0.0
                    })

                cursor.close()
                conn.close()

                return positions

            except Exception as e:
                # エラーメッセージの安全なデコード
                error_msg = str(e)
                try:
                    if isinstance(e.args[0] if e.args else '', bytes):
                        error_msg = e.args[0].decode('utf-8', errors='replace')
                except:
                    error_msg = repr(e)
                self.logger.error(f"Failed to get positions: {error_msg}")
                return []

    def close_position(self, ticket: int) -> bool:
        """
        ポジションを決済

        Args:
            ticket: ポジションticket番号

        Returns:
            True: 決済成功, False: 決済失敗
        """
        if self.use_mt5 and self.executor:
            return self.executor.close_position(ticket)
        else:
            self.logger.warning("Demo mode: Cannot close position")
            return False


# モジュールのエクスポート
__all__ = ['PositionManager']
