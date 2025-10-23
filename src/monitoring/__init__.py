"""
========================================
モニタリングパッケージ
========================================

パッケージ名: monitoring
パス: src/monitoring/

【概要】
3層モニタリングシステムを実装し、ポジションの監視と自動決済を
行うパッケージです。

【含まれるモジュール】
- layer1_emergency.py: Layer 1 緊急停止モニター ✅実装済み
- layer2_anomaly.py: Layer 2 異常検知モニター ✅実装済み
- layer3_ai_review.py: Layer 3 AI再評価モニター ✅実装済み
- monitor_orchestrator.py: 統合オーケストレーター ✅実装済み

【モニタリング階層】
- Layer 1: 緊急停止（100ms、50pips、口座2%損失）✅実装済み
- Layer 2: 異常検知（5分、DD10%、逆行8pips、スプレッド5pips）✅実装済み
- Layer 3: AI再評価（30分、判断反転、信頼度60%）✅実装済み

【主な機能】
1. リアルタイムポジション監視（100ms）
2. ハードストップロス監視（50pips）
3. 口座損失監視（2%）
4. ドローダウン・逆行・スプレッド監視（5分）
5. AI判断再評価・自動決済（30分）
6. アラート通知システム
7. 統合オーケストレーション

【使用例】
```python
from src.monitoring import MonitorOrchestrator

# 全モニターを統合管理
orchestrator = MonitorOrchestrator(symbol='USDJPY')
orchestrator.start_all()

# ポジションエントリー時
orchestrator.register_position_entry(
    ticket=12345,
    action='BUY',
    confidence=85.0,
    reasoning='Strong uptrend'
)

# ステータス確認
orchestrator.print_status()

# 全モニター停止
orchestrator.stop_all()
```

【作成日】2025-10-22
【更新日】2025-10-23
"""

from src.monitoring.layer1_emergency import Layer1EmergencyMonitor
from src.monitoring.layer2_anomaly import Layer2AnomalyMonitor
from src.monitoring.layer3_ai_review import Layer3AIReviewMonitor
from src.monitoring.monitor_orchestrator import MonitorOrchestrator

__all__ = [
    'Layer1EmergencyMonitor',
    'Layer2AnomalyMonitor',
    'Layer3AIReviewMonitor',
    'MonitorOrchestrator',
]
