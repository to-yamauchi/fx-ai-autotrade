"""
========================================
テストパッケージ
========================================

パッケージ名: tests
パス: tests/

【概要】
FX自動トレードシステムの全モジュールに対するユニットテストと
統合テストを含むパッケージです。

【テストファイル構成】
- test_tick_loader.py: ティックデータローダーのテスト
- test_timeframe_converter.py: 時間足変換のテスト（今後実装）
- test_technical_indicators.py: テクニカル指標計算のテスト（今後実装）
- test_ai_analyzer.py: AI分析のテスト（今後実装）
- test_trading_rules.py: トレードルールのテスト（今後実装）

【テスト実行方法】
全テスト実行:
    pytest tests/ -v

特定のテスト実行:
    pytest tests/test_tick_loader.py -v

カバレッジ付き実行:
    pytest tests/ --cov=src --cov-report=html
"""

__all__ = []
