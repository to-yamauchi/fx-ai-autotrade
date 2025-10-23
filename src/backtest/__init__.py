"""
========================================
バックテストパッケージ
========================================

パッケージ名: backtest
パス: src/backtest/

【概要】
AI判断とトレード戦略を過去データで検証するバックテストシステム。

【含まれるモジュール】
- trade_simulator.py: 仮想トレードシミュレーター
- backtest_engine.py: バックテストエンジン本体

【主な機能】
1. 過去データでのAI判断シミュレーション
2. 仮想トレード実行と損益計算
3. パフォーマンス統計の算出
4. 勝率・利益率・最大DDの分析
5. 結果のデータベース保存

【使用例】
```python
from src.backtest import BacktestEngine

# バックテスト実行
engine = BacktestEngine(
    symbol='USDJPY',
    start_date='2024-01-01',
    end_date='2024-12-31',
    ai_model='flash'
)

results = engine.run()

print(f"Win Rate: {results['win_rate']:.2f}%")
print(f"Profit Factor: {results['profit_factor']:.2f}")
print(f"Return: {results['return_pct']:.2f}%")
```

【作成日】2025-10-23
"""

from src.backtest.trade_simulator import TradeSimulator
from src.backtest.backtest_engine import BacktestEngine

__all__ = [
    'TradeSimulator',
    'BacktestEngine',
]
