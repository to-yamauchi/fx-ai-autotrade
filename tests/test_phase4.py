"""
Phase 4テストモジュール
"""
import pytest
from unittest.mock import Mock, patch
from src.rule_engine import TradingRules
from src.trade_execution import PositionManager

class TestTradingRules:
    """TradingRulesのテスト"""

    def test_validate_trade_success(self):
        rules = TradingRules()
        ai_judgment = {'action': 'BUY', 'confidence': 75}
        is_valid, msg = rules.validate_trade(ai_judgment, current_positions=1, spread=2.0)
        assert is_valid is True

    def test_validate_trade_low_confidence(self):
        rules = TradingRules()
        ai_judgment = {'action': 'BUY', 'confidence': 50}
        is_valid, msg = rules.validate_trade(ai_judgment, current_positions=1, spread=2.0)
        assert is_valid is False
        assert '信頼度不足' in msg

class TestPositionManager:
    """PositionManagerのテスト"""

    @patch('src.trade_execution.position_manager.psycopg2.connect')
    def test_position_manager_init(self, mock_connect):
        manager = PositionManager(use_mt5=False)
        assert manager.symbol == 'USDJPY'
        assert manager.use_mt5 is False

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
