"""
========================================
トレード実行パッケージ
========================================

パッケージ名: trade_execution
パス: src/trade_execution/

【概要】
MetaTrader5と連携し、実際のトレード実行を担当するパッケージです。
フェーズ4で実装完了。

【含まれるモジュール】
- mt5_executor.py: MT5でのトレード実行
- position_manager.py: ポジション管理とトレード統合制御

【主な機能】
1. MT5への接続・ログイン
2. 成行注文の実行（BUY/SELL）
3. ポジションの管理・決済
4. ストップロス・テイクプロフィットの設定
5. AI判断→ルール検証→実行の統合フロー

【使用例】
```python
from src.trade_execution import PositionManager

manager = PositionManager(symbol='USDJPY', use_mt5=False)  # Demo mode
result = manager.process_ai_judgment(ai_judgment)

if result['success']:
    print(f"Trade executed: {result['ticket']}")
```
"""

from src.trade_execution.mt5_executor import MT5Executor
from src.trade_execution.position_manager import PositionManager

__all__ = ['MT5Executor', 'PositionManager']
