"""
========================================
トレードシミュレーター
========================================

ファイル名: trade_simulator.py
パス: src/backtest/trade_simulator.py

【概要】
バックテスト用の仮想トレードシミュレーター。
実際のMT5を使わずに、過去データでトレードをシミュレーションします。

【主な機能】
1. 仮想ポジションのオープン
2. SL/TPの監視と自動決済
3. スプレッドのシミュレーション
4. ポジション履歴の記録
5. 損益計算

【使用例】
```python
from src.backtest.trade_simulator import TradeSimulator

simulator = TradeSimulator(initial_balance=100000)
ticket = simulator.open_position(
    action='BUY',
    price=152.400,
    volume=1.0,
    sl=152.350,
    tp=152.500
)
simulator.update_market_price(152.450)
simulator.close_position(ticket)
```

【作成日】2025-10-23
"""

from typing import Dict, List, Optional
from datetime import datetime
import logging


class TradeSimulator:
    """
    トレードシミュレータークラス

    バックテスト用に仮想トレードをシミュレートします。
    """

    def __init__(
        self,
        initial_balance: float = 100000.0,
        spread_pips: float = 2.0,
        symbol: str = 'USDJPY'
    ):
        """
        シミュレーターの初期化

        Args:
            initial_balance: 初期残高
            spread_pips: スプレッド（pips）
            symbol: 通貨ペア
        """
        self.symbol = symbol
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.equity = initial_balance
        self.spread_pips = spread_pips
        self.logger = logging.getLogger(__name__)

        # ポジション管理
        self.next_ticket = 1
        self.open_positions: Dict[int, Dict] = {}
        self.closed_positions: List[Dict] = []

        # 現在の市場価格
        self.current_bid = 0.0
        self.current_ask = 0.0

        # 統計情報
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = 0.0
        self.total_loss = 0.0
        self.max_drawdown = 0.0
        self.peak_balance = initial_balance

        self.logger.info(
            f"TradeSimulator initialized: "
            f"balance={initial_balance}, spread={spread_pips}pips"
        )

    def update_market_price(self, bid: float, ask: Optional[float] = None):
        """
        市場価格を更新

        Args:
            bid: ビッド価格
            ask: アスク価格（指定しない場合はスプレッドから計算）
        """
        self.current_bid = bid

        if ask is None:
            # スプレッドから計算
            spread_price = self.spread_pips / 100.0  # USDJPY想定
            self.current_ask = bid + spread_price
        else:
            self.current_ask = ask

        # すべてのオープンポジションを更新
        self._update_positions()

    def open_position(
        self,
        action: str,
        price: float,
        volume: float,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        comment: str = ''
    ) -> int:
        """
        ポジションをオープン

        Args:
            action: 'BUY' または 'SELL'
            price: エントリー価格
            volume: ロット数
            sl: ストップロス価格
            tp: テイクプロフィット価格
            comment: コメント

        Returns:
            ticket番号
        """
        ticket = self.next_ticket
        self.next_ticket += 1

        # スプレッドを考慮したエントリー価格
        if action == 'BUY':
            entry_price = self.current_ask
        else:  # SELL
            entry_price = self.current_bid

        position = {
            'ticket': ticket,
            'action': action,
            'volume': volume,
            'entry_price': entry_price,
            'current_price': entry_price,
            'sl': sl,
            'tp': tp,
            'profit': 0.0,
            'open_time': datetime.now(),
            'comment': comment,
            'status': 'OPEN'
        }

        self.open_positions[ticket] = position

        # ログとコンソール出力
        entry_msg = (
            f"📈 エントリー: #{ticket} | {action} {volume}ロット @ {entry_price:.3f} | "
            f"SL: {sl:.3f if sl else 'なし'} | TP: {tp:.3f if tp else 'なし'} | "
            f"残高: {self.balance:,.0f}円"
        )
        self.logger.info(f"Position opened: ticket={ticket}, {action} {volume} lots @ {entry_price}")
        print(entry_msg)

        return ticket

    def close_position(
        self,
        ticket: int,
        reason: str = 'Manual close'
    ) -> Optional[Dict]:
        """
        ポジションをクローズ

        Args:
            ticket: チケット番号
            reason: クローズ理由

        Returns:
            クローズされたポジション情報
        """
        if ticket not in self.open_positions:
            self.logger.warning(f"Position {ticket} not found")
            return None

        position = self.open_positions[ticket]

        # 決済価格を決定
        if position['action'] == 'BUY':
            close_price = self.current_bid
        else:  # SELL
            close_price = self.current_ask

        # 損益計算
        profit = self._calculate_profit(
            position['action'],
            position['entry_price'],
            close_price,
            position['volume']
        )

        # ポジション情報を更新
        position['close_price'] = close_price
        position['close_time'] = datetime.now()
        position['profit'] = profit
        position['status'] = 'CLOSED'
        position['close_reason'] = reason

        # 残高を更新
        self.balance += profit
        self.equity = self.balance

        # 統計を更新
        self._update_statistics(profit)

        # クローズ済みリストに移動
        self.closed_positions.append(position)
        del self.open_positions[ticket]

        # pips計算
        if position['action'] == 'BUY':
            pips = (close_price - position['entry_price']) * 100
        else:  # SELL
            pips = (position['entry_price'] - close_price) * 100

        # ログとコンソール出力
        profit_sign = "+" if profit > 0 else ""
        pips_sign = "+" if pips > 0 else ""

        # 決済理由の絵文字
        if "TP" in reason or "take_profit" in reason.lower():
            emoji = "✅"
            reason_short = "TP"
        elif "SL" in reason or "stop_loss" in reason.lower():
            emoji = "❌"
            reason_short = "SL"
        else:
            emoji = "📉"
            reason_short = reason[:10]

        close_msg = (
            f"{emoji} 決済: #{ticket} | {position['action']} {position['volume']}ロット | "
            f"エントリー: {position['entry_price']:.3f} → 決済: {close_price:.3f} | "
            f"損益: {profit_sign}{profit:,.0f}円 ({pips_sign}{pips:.1f}pips) | "
            f"理由: {reason_short} | 残高: {self.balance:,.0f}円"
        )

        self.logger.info(
            f"Position closed: ticket={ticket}, "
            f"profit={profit:.2f}, pips={pips:.1f}, reason={reason}"
        )
        print(close_msg)

        return position

    def _update_positions(self):
        """
        すべてのオープンポジションを更新（SL/TPチェック含む）
        """
        positions_to_close = []

        for ticket, position in self.open_positions.items():
            # 現在価格を更新
            if position['action'] == 'BUY':
                position['current_price'] = self.current_bid
            else:  # SELL
                position['current_price'] = self.current_ask

            # 含み損益を計算
            position['profit'] = self._calculate_profit(
                position['action'],
                position['entry_price'],
                position['current_price'],
                position['volume']
            )

            # SL/TPチェック
            sl_hit = False
            tp_hit = False

            if position['action'] == 'BUY':
                if position['sl'] and self.current_bid <= position['sl']:
                    sl_hit = True
                if position['tp'] and self.current_bid >= position['tp']:
                    tp_hit = True
            else:  # SELL
                if position['sl'] and self.current_ask >= position['sl']:
                    sl_hit = True
                if position['tp'] and self.current_ask <= position['tp']:
                    tp_hit = True

            if sl_hit:
                positions_to_close.append((ticket, 'SL hit'))
            elif tp_hit:
                positions_to_close.append((ticket, 'TP hit'))

        # SL/TPでクローズ
        for ticket, reason in positions_to_close:
            self.close_position(ticket, reason)

        # Equityを更新
        total_floating_profit = sum(
            pos['profit'] for pos in self.open_positions.values()
        )
        self.equity = self.balance + total_floating_profit

    def _calculate_profit(
        self,
        action: str,
        entry_price: float,
        exit_price: float,
        volume: float
    ) -> float:
        """
        損益を計算

        Args:
            action: 'BUY' または 'SELL'
            entry_price: エントリー価格
            exit_price: 決済価格
            volume: ロット数

        Returns:
            損益（円）
        """
        # USDJPY の場合: 1 lot = 100,000 通貨
        # 1 pip = 0.01円 = 1000円（1 lot）
        pip_value = 1000.0 * volume

        if action == 'BUY':
            pips = (exit_price - entry_price) * 100
        else:  # SELL
            pips = (entry_price - exit_price) * 100

        profit = pips * pip_value

        return profit

    def _update_statistics(self, profit: float):
        """
        統計情報を更新

        Args:
            profit: 損益
        """
        self.total_trades += 1

        if profit > 0:
            self.winning_trades += 1
            self.total_profit += profit
        elif profit < 0:
            self.losing_trades += 1
            self.total_loss += abs(profit)

        # 最大残高を更新
        if self.balance > self.peak_balance:
            self.peak_balance = self.balance

        # ドローダウンを計算
        drawdown = self.peak_balance - self.balance
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown

    def get_statistics(self) -> Dict:
        """
        統計情報を取得

        Returns:
            統計情報の辞書
        """
        win_rate = (
            (self.winning_trades / self.total_trades * 100)
            if self.total_trades > 0 else 0
        )

        avg_profit = (
            self.total_profit / self.winning_trades
            if self.winning_trades > 0 else 0
        )

        avg_loss = (
            self.total_loss / self.losing_trades
            if self.losing_trades > 0 else 0
        )

        profit_factor = (
            self.total_profit / self.total_loss
            if self.total_loss > 0 else 0
        )

        net_profit = self.balance - self.initial_balance
        return_pct = (net_profit / self.initial_balance * 100)

        max_dd_pct = (
            self.max_drawdown / self.peak_balance * 100
            if self.peak_balance > 0 else 0
        )

        return {
            'initial_balance': self.initial_balance,
            'final_balance': self.balance,
            'net_profit': net_profit,
            'return_pct': return_pct,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': win_rate,
            'total_profit': self.total_profit,
            'total_loss': self.total_loss,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': self.max_drawdown,
            'max_drawdown_pct': max_dd_pct,
            'open_positions': len(self.open_positions),
            'closed_positions': len(self.closed_positions)
        }

    def get_open_positions(self) -> List[Dict]:
        """
        オープンポジション一覧を取得

        Returns:
            ポジションリスト
        """
        return list(self.open_positions.values())

    def get_closed_positions(self) -> List[Dict]:
        """
        クローズ済みポジション一覧を取得

        Returns:
            ポジションリスト
        """
        return self.closed_positions

    def close_all_positions(self, reason: str = 'Close all'):
        """
        すべてのポジションをクローズ

        Args:
            reason: クローズ理由
        """
        tickets = list(self.open_positions.keys())
        for ticket in tickets:
            self.close_position(ticket, reason)

        self.logger.info(f"All positions closed: {len(tickets)} positions")


# モジュールのエクスポート
__all__ = ['TradeSimulator']
