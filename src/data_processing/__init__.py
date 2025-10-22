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
- timeframe_converter.py: ティックデータを時間足（D1/H4/H1/M15）に変換
- technical_indicators.py: テクニカル指標（EMA/RSI/MACD/ATR/BB）の計算
- data_standardizer.py: AI用にデータを標準化・JSON変換

【使用例】
>>> from src.data_processing import TickDataLoader, TimeframeConverter
>>> from src.data_processing import TechnicalIndicators, DataStandardizer
>>>
>>> # ティックデータ読み込み
>>> loader = TickDataLoader()
>>> tick_data = loader.load_from_zip("USDJPY", 2024, 9)
>>>
>>> # 時間足変換
>>> converter = TimeframeConverter()
>>> ohlcv_h1 = converter.convert(tick_data, "H1")
>>>
>>> # テクニカル指標計算
>>> ti = TechnicalIndicators()
>>> indicators = ti.calculate_all(ohlcv_h1)
>>>
>>> # データ標準化
>>> standardizer = DataStandardizer()
>>> standardized = standardizer.standardize_for_ai({'H1': ohlcv_h1}, indicators)
"""

from .tick_loader import TickDataLoader
from .timeframe_converter import TimeframeConverter
from .technical_indicators import TechnicalIndicators
from .data_standardizer import DataStandardizer

__all__ = [
    'TickDataLoader',
    'TimeframeConverter',
    'TechnicalIndicators',
    'DataStandardizer'
]
