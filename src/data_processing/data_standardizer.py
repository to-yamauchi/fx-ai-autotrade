"""
========================================
データ標準化モジュール
========================================

ファイル名: data_standardizer.py
モジュールパス: src/data_processing/data_standardizer.py

【概要】
マーケットデータとテクニカル指標をAI（Gemini API）が分析しやすい
JSON形式に標準化するモジュールです。

【主な機能】
1. 時間足データの標準化
2. テクニカル指標の標準化
3. マーケット状況の分類・ラベリング
4. JSON形式への変換

【使用例】
>>> from src.data_processing.data_standardizer import DataStandardizer
>>> standardizer = DataStandardizer()
>>> json_data = standardizer.standardize_for_ai(timeframe_data, indicators)

【依存関係】
- pandas: データフレーム操作
- json: JSON変換
- datetime: タイムスタンプ処理

【作成日】2025-10-22
【更新日】2025-10-22
"""

import json
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from datetime import datetime
import logging


class DataStandardizer:
    """
    AIが判断しやすい形式にデータを標準化するクラス

    このクラスは、時間足データとテクニカル指標を受け取り、
    AI（Gemini API）が分析しやすいJSON形式に変換します。

    Methods:
        standardize_for_ai: マーケットデータをAI用に標準化
        to_json: 標準化データをJSON文字列に変換
    """

    def __init__(self):
        """
        DataStandardizerの初期化
        """
        self.logger = logging.getLogger(__name__)

        # ログレベルの設定
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def standardize_for_ai(
        self,
        timeframe_data: Dict[str, pd.DataFrame],
        indicators: Dict[str, Any],
        symbol: str = "USDJPY"
    ) -> Dict:
        """
        マーケットデータをAI用に標準化

        【出力データ構造】
        {
            'timestamp': '現在時刻',
            'symbol': '通貨ペア',
            'timeframes': {
                'D1': {...},
                'H4': {...},
                'H1': {...},
                'M15': {...}
            },
            'technical_indicators': {
                'ema': {...},
                'rsi': {...},
                'macd': {...},
                'bollinger': {...},
                'atr': {...}
            },
            'market_conditions': {
                'volatility': 'high/normal/low',
                'trend_strength': 'strong/weak',
                'support_resistance': {...}
            }
        }

        Args:
            timeframe_data (Dict[str, pd.DataFrame]): 各時間足のOHLCVデータ
                キー: 時間足名（'D1', 'H4', 'H1', 'M15'）
                値: OHLCVデータフレーム
            indicators (Dict[str, Any]): テクニカル指標
            symbol (str): 通貨ペア（デフォルト: "USDJPY"）

        Returns:
            Dict: 標準化されたマーケットデータ

        Example:
            >>> standardizer = DataStandardizer()
            >>> standardized = standardizer.standardize_for_ai(
            ...     timeframe_data={'H1': ohlcv_h1, 'H4': ohlcv_h4},
            ...     indicators=indicators
            ... )
            >>> print(json.dumps(standardized, indent=2, ensure_ascii=False))
        """
        self.logger.info(f"データ標準化開始: {symbol}")

        standardized = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'timeframes': {},
            'technical_indicators': {},
            'market_conditions': {}
        }

        # 時間足データを標準化
        for tf_name, df in timeframe_data.items():
            if df is None or len(df) == 0:
                self.logger.warning(f"{tf_name}のデータが空です")
                continue

            standardized['timeframes'][tf_name] = self._standardize_timeframe(
                df, tf_name
            )

        # テクニカル指標を標準化
        standardized['technical_indicators'] = self._standardize_indicators(
            indicators, timeframe_data
        )

        # マーケット状況を分析
        standardized['market_conditions'] = self._analyze_market_conditions(
            indicators, timeframe_data
        )

        self.logger.info("データ標準化完了")

        return standardized

    def _standardize_timeframe(
        self,
        df: pd.DataFrame,
        timeframe: str
    ) -> Dict:
        """
        時間足データを標準化

        Args:
            df (pd.DataFrame): OHLCVデータフレーム
            timeframe (str): 時間足名

        Returns:
            Dict: 標準化された時間足データ
        """
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest

        # 変化率を計算
        change_pct = ((latest['close'] - prev['close']) / prev['close']) * 100

        return {
            'current': {
                'open': float(latest['open']),
                'high': float(latest['high']),
                'low': float(latest['low']),
                'close': float(latest['close']),
                'volume': int(latest['volume'])
            },
            'previous': {
                'open': float(prev['open']),
                'high': float(prev['high']),
                'low': float(prev['low']),
                'close': float(prev['close']),
                'volume': int(prev['volume'])
            },
            'change_pct': float(change_pct),
            'direction': 'up' if change_pct > 0 else 'down' if change_pct < 0 else 'flat',
            'range': float(latest['high'] - latest['low']),
            'body_size': float(abs(latest['close'] - latest['open']))
        }

    def _standardize_indicators(
        self,
        indicators: Dict[str, Any],
        timeframe_data: Dict[str, pd.DataFrame]
    ) -> Dict:
        """
        テクニカル指標を標準化

        Args:
            indicators (Dict[str, Any]): テクニカル指標
            timeframe_data (Dict[str, pd.DataFrame]): 時間足データ

        Returns:
            Dict: 標準化されたテクニカル指標
        """
        standardized_indicators = {}

        # EMA
        if 'ema_short' in indicators and 'ema_long' in indicators:
            ema_short_val = float(indicators['ema_short'].iloc[-1])
            ema_long_val = float(indicators['ema_long'].iloc[-1])

            standardized_indicators['ema'] = {
                'short': ema_short_val,
                'long': ema_long_val,
                'trend': 'up' if ema_short_val > ema_long_val else 'down',
                'cross_distance': float(ema_short_val - ema_long_val)
            }

        # RSI
        if 'rsi' in indicators:
            rsi_val = float(indicators['rsi'].iloc[-1])
            standardized_indicators['rsi'] = {
                'value': rsi_val,
                'condition': self._classify_rsi(rsi_val),
                'momentum': self._calculate_rsi_momentum(indicators['rsi'])
            }

        # MACD
        if 'macd' in indicators:
            macd_data = indicators['macd']
            macd_val = float(macd_data['macd'].iloc[-1])
            signal_val = float(macd_data['signal'].iloc[-1])
            histogram_val = float(macd_data['histogram'].iloc[-1])

            standardized_indicators['macd'] = {
                'macd': macd_val,
                'signal': signal_val,
                'histogram': histogram_val,
                'trend': 'bullish' if histogram_val > 0 else 'bearish',
                'divergence': self._detect_macd_divergence(macd_data)
            }

        # ボリンジャーバンド
        if 'bollinger' in indicators:
            bb = indicators['bollinger']
            # 最新の終値を取得
            current_price = None
            for tf_data in timeframe_data.values():
                if tf_data is not None and len(tf_data) > 0:
                    current_price = float(tf_data.iloc[-1]['close'])
                    break

            if current_price is not None:
                standardized_indicators['bollinger'] = {
                    'upper': float(bb['upper'].iloc[-1]),
                    'middle': float(bb['middle'].iloc[-1]),
                    'lower': float(bb['lower'].iloc[-1]),
                    'position': self._classify_bb_position(
                        current_price, bb
                    ),
                    'bandwidth': self._calculate_bb_bandwidth(bb)
                }

        # ATR
        if 'atr' in indicators:
            atr_val = float(indicators['atr'].iloc[-1])
            standardized_indicators['atr'] = {
                'value': atr_val,
                'volatility': self._classify_volatility(indicators['atr'])
            }

        return standardized_indicators

    def _analyze_market_conditions(
        self,
        indicators: Dict[str, Any],
        timeframe_data: Dict[str, pd.DataFrame]
    ) -> Dict:
        """
        マーケット状況を分析

        Args:
            indicators (Dict[str, Any]): テクニカル指標
            timeframe_data (Dict[str, pd.DataFrame]): 時間足データ

        Returns:
            Dict: マーケット状況の分析結果
        """
        conditions = {}

        # ボラティリティ
        if 'atr' in indicators:
            conditions['volatility'] = self._classify_volatility(
                indicators['atr']
            )

        # トレンド強度
        conditions['trend_strength'] = self._calculate_trend_strength(
            indicators
        )

        # サポート・レジスタンス
        if 'support_resistance' in indicators:
            conditions['support_resistance'] = indicators['support_resistance']

        # 総合的なマーケット状態
        conditions['overall_condition'] = self._determine_overall_condition(
            indicators
        )

        return conditions

    def _classify_rsi(self, rsi_value: float) -> str:
        """
        RSI値を分類

        Args:
            rsi_value (float): RSI値

        Returns:
            str: 'overbought' / 'oversold' / 'neutral'
        """
        if rsi_value >= 70:
            return 'overbought'  # 買われすぎ
        elif rsi_value <= 30:
            return 'oversold'    # 売られすぎ
        else:
            return 'neutral'     # 中立

    def _calculate_rsi_momentum(self, rsi_series: pd.Series) -> str:
        """
        RSIのモメンタムを計算

        Args:
            rsi_series (pd.Series): RSI値のシリーズ

        Returns:
            str: 'increasing' / 'decreasing' / 'stable'
        """
        if len(rsi_series) < 2:
            return 'stable'

        recent_change = rsi_series.iloc[-1] - rsi_series.iloc[-5:-1].mean()

        if recent_change > 5:
            return 'increasing'
        elif recent_change < -5:
            return 'decreasing'
        else:
            return 'stable'

    def _detect_macd_divergence(self, macd_data: Dict) -> str:
        """
        MACDのダイバージェンスを検出（簡易版）

        Args:
            macd_data (Dict): MACDデータ

        Returns:
            str: 'none' / 'bullish' / 'bearish'
        """
        # 簡易実装: 実際にはより高度な分析が必要
        histogram = macd_data['histogram']

        if len(histogram) < 5:
            return 'none'

        # ヒストグラムの傾向をチェック
        recent_trend = histogram.iloc[-3:].mean() - histogram.iloc[-6:-3].mean()

        if recent_trend > 0:
            return 'bullish'
        elif recent_trend < 0:
            return 'bearish'
        else:
            return 'none'

    def _classify_bb_position(
        self,
        price: float,
        bb: Dict[str, pd.Series]
    ) -> str:
        """
        ボリンジャーバンド内の価格位置を分類

        Args:
            price (float): 現在価格
            bb (Dict[str, pd.Series]): ボリンジャーバンドデータ

        Returns:
            str: 'above_upper' / 'upper_half' / 'lower_half' / 'below_lower'
        """
        upper = bb['upper'].iloc[-1]
        middle = bb['middle'].iloc[-1]
        lower = bb['lower'].iloc[-1]

        if price >= upper:
            return 'above_upper'     # 上限超え
        elif price >= middle:
            return 'upper_half'      # 上半分
        elif price >= lower:
            return 'lower_half'      # 下半分
        else:
            return 'below_lower'     # 下限超え

    def _calculate_bb_bandwidth(self, bb: Dict[str, pd.Series]) -> float:
        """
        ボリンジャーバンドの幅を計算

        Args:
            bb (Dict[str, pd.Series]): ボリンジャーバンドデータ

        Returns:
            float: バンド幅（%）
        """
        upper = bb['upper'].iloc[-1]
        lower = bb['lower'].iloc[-1]
        middle = bb['middle'].iloc[-1]

        bandwidth = ((upper - lower) / middle) * 100

        return float(bandwidth)

    def _classify_volatility(self, atr: pd.Series) -> str:
        """
        ボラティリティを分類

        Args:
            atr (pd.Series): ATR値のシリーズ

        Returns:
            str: 'high' / 'normal' / 'low'
        """
        current_atr = atr.iloc[-1]
        avg_atr = atr.mean()

        if current_atr > avg_atr * 1.5:
            return 'high'       # 高ボラティリティ
        elif current_atr < avg_atr * 0.5:
            return 'low'        # 低ボラティリティ
        else:
            return 'normal'     # 通常

    def _calculate_trend_strength(self, indicators: Dict[str, Any]) -> str:
        """
        トレンド強度を計算

        Args:
            indicators (Dict[str, Any]): テクニカル指標

        Returns:
            str: 'strong' / 'weak' / 'neutral'
        """
        # EMAとMACDから総合判断
        signals = []

        # EMA判断
        if 'ema_short' in indicators and 'ema_long' in indicators:
            ema_short = indicators['ema_short'].iloc[-1]
            ema_long = indicators['ema_long'].iloc[-1]
            ema_signal = 1 if ema_short > ema_long else -1
            signals.append(ema_signal)

        # MACD判断
        if 'macd' in indicators:
            histogram = indicators['macd']['histogram'].iloc[-1]
            macd_signal = 1 if histogram > 0 else -1
            signals.append(macd_signal)

        if not signals:
            return 'neutral'

        # シグナルの一致度を確認
        if all(s == signals[0] for s in signals):
            return 'strong'     # 全シグナル一致
        else:
            return 'weak'       # シグナル不一致

    def _determine_overall_condition(self, indicators: Dict[str, Any]) -> str:
        """
        総合的なマーケット状態を判定

        Args:
            indicators (Dict[str, Any]): テクニカル指標

        Returns:
            str: 'strong_uptrend' / 'uptrend' / 'ranging' / 'downtrend' / 'strong_downtrend'
        """
        # 簡易実装: 複数の指標から総合判断
        bullish_count = 0
        bearish_count = 0

        # EMA判断
        if 'ema_short' in indicators and 'ema_long' in indicators:
            if indicators['ema_short'].iloc[-1] > indicators['ema_long'].iloc[-1]:
                bullish_count += 1
            else:
                bearish_count += 1

        # MACD判断
        if 'macd' in indicators:
            if indicators['macd']['histogram'].iloc[-1] > 0:
                bullish_count += 1
            else:
                bearish_count += 1

        # RSI判断
        if 'rsi' in indicators:
            rsi_val = indicators['rsi'].iloc[-1]
            if rsi_val > 50:
                bullish_count += 1
            elif rsi_val < 50:
                bearish_count += 1

        # 総合判定
        total = bullish_count + bearish_count
        if total == 0:
            return 'ranging'

        bull_ratio = bullish_count / total

        if bull_ratio >= 0.8:
            return 'strong_uptrend'
        elif bull_ratio >= 0.6:
            return 'uptrend'
        elif bull_ratio >= 0.4:
            return 'ranging'
        elif bull_ratio >= 0.2:
            return 'downtrend'
        else:
            return 'strong_downtrend'

    def to_json(
        self,
        standardized_data: Dict,
        ensure_ascii: bool = False,
        indent: int = 2
    ) -> str:
        """
        標準化データをJSON文字列に変換

        Args:
            standardized_data (Dict): 標準化されたデータ
            ensure_ascii (bool): ASCII文字のみを使用するか
            indent (int): インデント幅

        Returns:
            str: JSON文字列
        """
        return json.dumps(
            standardized_data,
            ensure_ascii=ensure_ascii,
            indent=indent
        )


# モジュールテスト用のメイン関数
if __name__ == "__main__":
    """
    モジュールの動作確認用コード

    実行方法:
        python -m src.data_processing.data_standardizer
    """
    import sys
    sys.path.insert(0, '/home/user/fx-ai-autotrade')

    from src.data_processing.tick_loader import TickDataLoader
    from src.data_processing.timeframe_converter import TimeframeConverter
    from src.data_processing.technical_indicators import TechnicalIndicators

    # ロギング設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    try:
        # ティックデータを読み込み
        loader = TickDataLoader(data_dir="data/tick_data")
        tick_data = loader.load_from_zip("USDJPY", 2024, 9)

        # 時間足に変換
        converter = TimeframeConverter()
        ohlcv_h1 = converter.convert(tick_data, "H1")

        # テクニカル指標を計算
        ti = TechnicalIndicators()
        indicators = ti.calculate_all(ohlcv_h1)

        # データを標準化
        standardizer = DataStandardizer()
        standardized = standardizer.standardize_for_ai(
            timeframe_data={'H1': ohlcv_h1},
            indicators=indicators
        )

        # JSON出力
        print("\n=== 標準化されたマーケットデータ（JSON） ===")
        json_str = standardizer.to_json(standardized)
        print(json_str[:1000])  # 最初の1000文字のみ表示
        print("...")

    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
