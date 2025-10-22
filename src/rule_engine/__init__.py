"""
========================================
ルールエンジンパッケージ
========================================

パッケージ名: rule_engine
パス: src/rule_engine/

【概要】
AI判断に基づいてトレードルールを適用し、実行可否を判定する
パッケージです。フェーズ4で実装完了。

【含まれるモジュール】
- trading_rules.py: トレードルールの管理と検証

【主なルール】
1. 最小信頼度チェック（60%以上）
2. スプレッドチェック（3.0pips以下）
3. 最大ポジション数チェック（3ポジション以下）
4. トレーディング時間チェック（金曜22時以降・週末は禁止）
5. ボラティリティチェック

【使用例】
```python
from src.rule_engine import TradingRules

rules = TradingRules()
ai_judgment = {'action': 'BUY', 'confidence': 75}
is_valid, message = rules.validate_trade(
    ai_judgment=ai_judgment,
    current_positions=2,
    spread=2.0
)
```
"""

from src.rule_engine.trading_rules import TradingRules

__all__ = ['TradingRules']
