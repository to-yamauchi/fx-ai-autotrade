"""
========================================
データ処理パッケージ
========================================

パッケージ名: data_processing
パス: src/data_processing/

【概要】
ティックデータの読み込み、時間足変換、テクニカル指標計算、
データ標準化など、データ処理全般を担当するパッケージです。

【含まれるモジュール】
- tick_loader.py: zipファイルからティックデータを読み込む
- timeframe_converter.py: ティックデータを時間足（D1/H4/H1/M15）に変換（今後実装）
- technical_indicators.py: テクニカル指標（EMA/RSI/MACD/ATR/BB）の計算（今後実装）
- data_standardizer.py: AI用にデータを標準化・JSON変換（今後実装）

【使用例】
>>> from src.data_processing.tick_loader import TickDataLoader
>>> loader = TickDataLoader()
>>> tick_data = loader.load_from_zip("USDJPY", 2024, 9)
"""

from .tick_loader import TickDataLoader

__all__ = ['TickDataLoader']
