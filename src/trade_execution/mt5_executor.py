"""
========================================
MT5トレード実行モジュール
========================================

ファイル名: mt5_executor.py
パス: src/trade_execution/mt5_executor.py

【概要】
MetaTrader5（MT5）を使用してトレードを実行するモジュールです。
注文の送信、ポジション照会、決済などMT5の全機能を提供します。

【主な機能】
1. MT5への接続と認証
2. 成行注文の実行（BUY/SELL）
3. ポジションの照会
4. ポジションの決済
5. スプレッド情報の取得

【使用例】
```python
from src.trade_execution import MT5Executor

executor = MT5Executor()
ticket = executor.execute_trade(
    symbol='USDJPY',
    action='BUY',
    volume=0.1,
    sl=142.50,
    tp=143.50
)
```

【注意事項】
- MT5がインストールされている必要があります
- デモ口座またはライブ口座の認証情報が必要です
- 実際のトレードには十分な注意が必要です

【作成日】2025-10-22
"""

import MetaTrader5 as mt5
from typing import Optional, Dict, List
import os
import logging
from datetime import datetime


class MT5Executor:
    """
    MT5でトレードを実行するクラス

    MetaTrader5 Pythonライブラリを使用して、
    トレードの実行とポジション管理を行います。
    """

    # Magic Number（システム識別用）
    MAGIC_NUMBER = 234000

    # 注文デビエーション（価格のずれ許容範囲、ポイント）
    DEVIATION = 10

    def __init__(self, auto_login: bool = True):
        """
        MT5Executorの初期化

        Args:
            auto_login: 初期化時に自動ログインするか
        """
        self.logger = logging.getLogger(__name__)
        self.is_initialized = False
        self.is_logged_in = False

        if auto_login:
            try:
                self.initialize_mt5()
                self.login()
            except Exception as e:
                self.logger.error(f"Auto login failed: {e}")

    def initialize_mt5(self) -> bool:
        """
        MT5を初期化

        Returns:
            True: 初期化成功
            False: 初期化失敗
        """
        if not mt5.initialize():
            error = mt5.last_error()
            self.logger.error(f"MT5 initialization failed: {error}")
            return False

        self.is_initialized = True
        self.logger.info("MT5 initialized successfully")
        return True

    def login(self) -> bool:
        """
        MT5にログイン

        環境変数からログイン情報を取得してログインします。

        Returns:
            True: ログイン成功
            False: ログイン失敗

        Raises:
            ValueError: 環境変数が設定されていない場合
        """
        if not self.is_initialized:
            self.initialize_mt5()

        # 環境変数から取得
        login_str = os.getenv('MT5_LOGIN')
        password = os.getenv('MT5_PASSWORD')
        server = os.getenv('MT5_SERVER')

        if not all([login_str, password, server]):
            raise ValueError(
                "MT5 credentials not set. "
                "Please set MT5_LOGIN, MT5_PASSWORD, MT5_SERVER in .env file"
            )

        try:
            login = int(login_str)
        except ValueError:
            raise ValueError(f"MT5_LOGIN must be a number, got: {login_str}")

        # ログイン実行
        authorized = mt5.login(login, password, server)

        if not authorized:
            error = mt5.last_error()
            self.logger.error(f"MT5 login failed: {error}")
            return False

        self.is_logged_in = True
        self.logger.info(f"MT5 login successful: account={login}, server={server}")
        return True

    def execute_trade(self,
                     symbol: str,
                     action: str,
                     volume: float,
                     sl: Optional[float] = None,
                     tp: Optional[float] = None,
                     comment: str = "AI Trade") -> Optional[int]:
        """
        成行注文を実行

        Args:
            symbol: 通貨ペア（例: 'USDJPY'）
            action: 'BUY' または 'SELL'
            volume: ロット数（例: 0.1）
            sl: ストップロス価格
            tp: テイクプロフィット価格
            comment: 注文コメント

        Returns:
            成功時: ticket番号（int）
            失敗時: None
        """
        if not self.is_logged_in:
            self.logger.error("Not logged in to MT5")
            return None

        # アクション検証
        if action not in ['BUY', 'SELL']:
            self.logger.error(f"Invalid action: {action}")
            return None

        # シンボル情報を取得
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            self.logger.error(f"Symbol {symbol} not found")
            return None

        # シンボルが表示されていない場合は表示する
        if not symbol_info.visible:
            if not mt5.symbol_select(symbol, True):
                self.logger.error(f"Failed to select {symbol}")
                return None

        # 注文タイプを決定
        order_type = mt5.ORDER_TYPE_BUY if action == 'BUY' else mt5.ORDER_TYPE_SELL

        # 現在価格を取得
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            self.logger.error(f"Failed to get tick for {symbol}")
            return None

        price = tick.ask if action == 'BUY' else tick.bid

        # ボリュームを正規化（シンボルの最小ロット単位に合わせる）
        volume_min = symbol_info.volume_min
        volume_max = symbol_info.volume_max
        volume_step = symbol_info.volume_step

        volume = max(volume_min, min(volume, volume_max))
        volume = round(volume / volume_step) * volume_step

        # ストップレベルのチェックと調整
        stops_level = symbol_info.trade_stops_level
        point = symbol_info.point

        # 最小ストップレベル（ポイント単位）を価格差に変換
        min_stop_distance = stops_level * point

        # SL/TPが指定されている場合、最小距離を確認
        if sl and sl > 0:
            sl_distance = abs(price - sl)
            if min_stop_distance > 0 and sl_distance < min_stop_distance:
                # 最小距離を満たさない場合はSLを調整
                if action == 'BUY':
                    sl = price - min_stop_distance
                else:
                    sl = price + min_stop_distance
                self.logger.warning(
                    f"SL adjusted to meet minimum stop level: {sl:.5f} "
                    f"(min distance: {min_stop_distance:.5f})"
                )

        if tp and tp > 0:
            tp_distance = abs(price - tp)
            if min_stop_distance > 0 and tp_distance < min_stop_distance:
                # 最小距離を満たさない場合はTPを調整
                if action == 'BUY':
                    tp = price + min_stop_distance
                else:
                    tp = price - min_stop_distance
                self.logger.warning(
                    f"TP adjusted to meet minimum stop level: {tp:.5f} "
                    f"(min distance: {min_stop_distance:.5f})"
                )

        # Filling Modeを決定（ブローカーによって対応が異なる）
        print(f"\n[DEBUG] Calling _get_filling_mode for {symbol}...")
        filling_type = self._get_filling_mode(symbol_info)
        print(f"[DEBUG] Selected filling_type: {filling_type}")

        # 注文リクエストを作成
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "sl": sl if sl else 0.0,
            "tp": tp if tp else 0.0,
            "deviation": self.DEVIATION,
            "magic": self.MAGIC_NUMBER,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_type,
        }

        # 注文を送信
        self.logger.info(
            f"Sending order: {action} {volume} {symbol} @ {price} "
            f"(SL={sl}, TP={tp})"
        )

        result = mt5.order_send(request)

        if result is None:
            self.logger.error("order_send returned None")
            return None

        # 結果を確認
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            self.logger.info(
                f"Trade executed successfully: "
                f"ticket={result.order}, {action} {volume} {symbol} @ {result.price}"
            )
            return result.order
        else:
            # エラー詳細をログ
            error_msg = f"Trade failed: retcode={result.retcode}, comment={result.comment}"

            # エラーコード10016（Invalid stops）の場合は詳細情報を追加
            if result.retcode == 10016:
                error_msg += (
                    f"\n  Stop level error details:"
                    f"\n    Current price: {price:.5f}"
                    f"\n    SL: {sl:.5f}" if sl else ""
                    f"\n    TP: {tp:.5f}" if tp else ""
                    f"\n    Min stop distance: {min_stop_distance:.5f}"
                    f"\n    Stops level (points): {stops_level}"
                )

            self.logger.error(error_msg)
            return None

    def close_position(self, ticket: int) -> bool:
        """
        ポジションを決済

        Args:
            ticket: ポジションのticket番号

        Returns:
            True: 決済成功
            False: 決済失敗
        """
        if not self.is_logged_in:
            self.logger.error("Not logged in to MT5")
            return False

        # ポジション情報を取得
        position = mt5.positions_get(ticket=ticket)
        if position is None or len(position) == 0:
            self.logger.error(f"Position {ticket} not found")
            return False

        position = position[0]

        # 反対売買のタイプを決定
        order_type = mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY \
                     else mt5.ORDER_TYPE_BUY

        # 現在価格を取得
        tick = mt5.symbol_info_tick(position.symbol)
        if tick is None:
            self.logger.error(f"Failed to get tick for {position.symbol}")
            return False

        price = tick.bid if position.type == mt5.ORDER_TYPE_BUY else tick.ask

        # 決済リクエストを作成
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": order_type,
            "position": ticket,
            "price": price,
            "deviation": self.DEVIATION,
            "magic": self.MAGIC_NUMBER,
            "comment": "Close by AI",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        # 決済を実行
        self.logger.info(f"Closing position: ticket={ticket}")
        result = mt5.order_send(request)

        if result is None:
            self.logger.error("order_send returned None")
            return False

        if result.retcode == mt5.TRADE_RETCODE_DONE:
            self.logger.info(f"Position closed successfully: ticket={ticket}")
            return True
        else:
            self.logger.error(
                f"Close failed: retcode={result.retcode}, "
                f"comment={result.comment}"
            )
            return False

    def get_positions(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        現在のポジションを取得

        Args:
            symbol: 通貨ペア（Noneの場合は全て）

        Returns:
            ポジションリスト
        """
        if not self.is_logged_in:
            self.logger.error("Not logged in to MT5")
            return []

        if symbol:
            positions = mt5.positions_get(symbol=symbol)
        else:
            positions = mt5.positions_get()

        if positions is None:
            return []

        position_list = []
        for pos in positions:
            position_list.append({
                'ticket': pos.ticket,
                'symbol': pos.symbol,
                'type': 'BUY' if pos.type == mt5.ORDER_TYPE_BUY else 'SELL',
                'volume': pos.volume,
                'open_price': pos.price_open,
                'current_price': pos.price_current,
                'sl': pos.sl,
                'tp': pos.tp,
                'profit': pos.profit,
                'open_time': datetime.fromtimestamp(pos.time),
                'magic': pos.magic
            })

        return position_list

    def get_spread(self, symbol: str) -> Optional[float]:
        """
        現在のスプレッドを取得（pips）

        Args:
            symbol: 通貨ペア

        Returns:
            スプレッド（pips）、エラー時はNone
        """
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return None

        # スプレッド = (Ask - Bid) / Point
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return None

        spread_pips = (tick.ask - tick.bid) / symbol_info.point / 10

        return spread_pips

    def _get_filling_mode(self, symbol_info) -> int:
        """
        シンボルに適したFilling Modeを取得

        Args:
            symbol_info: シンボル情報

        Returns:
            Filling Mode（ORDER_FILLING_XXX）
        """
        # シンボルがサポートするFilling Modeを確認
        filling_mode = symbol_info.filling_mode

        # デバッグ出力（確実に表示）
        print(f"  Filling mode flags: {filling_mode}")
        print(f"    FOK (2) supported: {bool(filling_mode & 2)}")
        print(f"    IOC (1) supported: {bool(filling_mode & 1)}")
        print(f"    RETURN (4) supported: {bool(filling_mode & 4)}")

        # デバッグログ
        self.logger.info(f"Symbol filling_mode flags: {filling_mode}")
        self.logger.info(f"  FOK supported: {bool(filling_mode & 2)}")
        self.logger.info(f"  IOC supported: {bool(filling_mode & 1)}")
        self.logger.info(f"  RETURN supported: {bool(filling_mode & 4)}")

        # 優先順位: RETURN > FOK > IOC
        # RETURN (Return) - 最も一般的、OANDAなどで推奨
        if filling_mode & 4:  # ORDER_FILLING_RETURN
            print(f"  → Selected: ORDER_FILLING_RETURN (value=0)")
            self.logger.info("Selected filling mode: ORDER_FILLING_RETURN")
            return 0  # mt5.ORDER_FILLING_RETURN

        # FOK (Fill or Kill) - 全量約定または全量キャンセル
        if filling_mode & 2:  # ORDER_FILLING_FOK
            print(f"  → Selected: ORDER_FILLING_FOK (value=1)")
            self.logger.info("Selected filling mode: ORDER_FILLING_FOK")
            return 1  # mt5.ORDER_FILLING_FOK

        # IOC (Immediate or Cancel) - 即時約定可能な分だけ約定
        if filling_mode & 1:  # ORDER_FILLING_IOC
            print(f"  → Selected: ORDER_FILLING_IOC (value=2)")
            self.logger.info("Selected filling mode: ORDER_FILLING_IOC")
            return 2  # mt5.ORDER_FILLING_IOC

        # デフォルトはRETURN（最も互換性が高い）
        print(f"  → Selected: ORDER_FILLING_RETURN (default, value=0)")
        self.logger.warning("No filling mode detected, using default: ORDER_FILLING_RETURN")
        return 0  # mt5.ORDER_FILLING_RETURN

    def get_account_info(self) -> Optional[Dict]:
        """
        口座情報を取得

        Returns:
            口座情報の辞書、エラー時はNone
        """
        if not self.is_logged_in:
            return None

        account = mt5.account_info()
        if account is None:
            return None

        return {
            'login': account.login,
            'balance': account.balance,
            'equity': account.equity,
            'margin': account.margin,
            'free_margin': account.margin_free,
            'profit': account.profit,
            'currency': account.currency,
            'leverage': account.leverage
        }

    def shutdown(self):
        """MT5接続をシャットダウン"""
        if self.is_initialized:
            mt5.shutdown()
            self.is_initialized = False
            self.is_logged_in = False
            self.logger.info("MT5 shutdown")

    def __del__(self):
        """デストラクタ：自動シャットダウン"""
        self.shutdown()


# モジュールのエクスポート
__all__ = ['MT5Executor']
