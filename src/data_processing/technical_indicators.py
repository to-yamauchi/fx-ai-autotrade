"""
========================================
テクニカル指標計算モジュール
========================================

ファイル名: technical_indicators.py
モジュールパス: src/data_processing/technical_indicators.py

【概要】
FXトレードで一般的に使用されるテクニカル指標を計算するモジュールです。
EMA、RSI、MACD、ATR、ボリンジャーバンドなどの指標を計算し、
AI分析に使用できる形式で提供します。

【主な機能】
1. EMA（指数移動平均）の計算
2. RSI（相対力指数）の計算
3. MACD（移動平均収束拡散法）の計算
4. ATR（平均真の範囲）の計算
5. ボリンジャーバンド（Bollinger Bands）の計算
6. サポート・レジスタンスレベルの計算

【使用例】
>>> from src.data_processing.technical_indicators import TechnicalIndicators
>>> ti = TechnicalIndicators()
>>> ema = ti.calculate_ema(close_prices, period=20)
>>> rsi = ti.calculate_rsi(close_prices, period=14)

【依存関係】
- pandas: データフレーム操作
- numpy: 数値計算

【作成日】2025-10-22
【更新日】2025-10-22
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
import logging


class TechnicalIndicators:
    """
    テクニカル指標を計算するクラス

    このクラスは、OHLCV（始値、高値、安値、終値、出来高）データから
    各種テクニカル指標を計算します。全てのメソッドはstaticmethodとして
    実装されており、インスタンス化なしでも使用できます。

    Methods:
        calculate_ema: EMA（指数移動平均）を計算
        calculate_rsi: RSI（相対力指数）を計算
        calculate_macd: MACDを計算
        calculate_atr: ATR（平均真の範囲）を計算
        calculate_bollinger_bands: ボリンジャーバンドを計算
        calculate_support_resistance: サポート・レジスタンスレベルを計算
        calculate_all: 全ての指標を一度に計算
    """

    def __init__(self):
        """
        TechnicalIndicatorsの初期化
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

    @staticmethod
    def calculate_ema(
        data: pd.Series,
        period: int,
        adjust: bool = False
    ) -> pd.Series:
        """
        EMA（指数移動平均）を計算

        【計算式】
        EMA(t) = Price(t) * k + EMA(t-1) * (1 - k)
        ただし、k = 2 / (period + 1)

        【特徴】
        - 直近の価格に大きな重みを付ける
        - SMAより反応が早い
        - トレンドフォロー指標として使用

        Args:
            data (pd.Series): 価格データ（通常はclose）
            period (int): 期間（例: 20, 50, 200）
            adjust (bool): 調整方法
                - False: 標準的なEMA（デフォルト）
                - True: 初期値調整あり

        Returns:
            pd.Series: EMA値のシリーズ

        Example:
            >>> ema_20 = TechnicalIndicators.calculate_ema(df['close'], 20)
            >>> ema_50 = TechnicalIndicators.calculate_ema(df['close'], 50)
        """
        return data.ewm(span=period, adjust=adjust).mean()

    @staticmethod
    def calculate_rsi(
        data: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """
        RSI（相対力指数）を計算

        【計算式】
        RSI = 100 - (100 / (1 + RS))
        RS = (平均上昇幅) / (平均下降幅)

        【解釈】
        - 0～100の範囲で推移
        - 70以上: 買われすぎ（Overbought）
        - 30以下: 売られすぎ（Oversold）
        - 50付近: 中立

        Args:
            data (pd.Series): 価格データ（通常はclose）
            period (int): 期間（デフォルト: 14）

        Returns:
            pd.Series: RSI値のシリーズ（0～100）

        Example:
            >>> rsi = TechnicalIndicators.calculate_rsi(df['close'], 14)
            >>> overbought = rsi > 70
            >>> oversold = rsi < 30
        """
        # 価格変化を計算
        delta = data.diff()

        # 上昇分と下降分を分離
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        # 平均を計算（EMAを使用）
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        # RSを計算
        rs = avg_gain / avg_loss

        # RSIを計算
        rsi = 100 - (100 / (1 + rs))

        return rsi

    @staticmethod
    def calculate_macd(
        data: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> Dict[str, pd.Series]:
        """
        MACD（移動平均収束拡散法）を計算

        【計算式】
        MACD Line = EMA(fast) - EMA(slow)
        Signal Line = EMA(MACD Line, signal)
        Histogram = MACD Line - Signal Line

        【解釈】
        - MACD Line > Signal Line: 買いシグナル
        - MACD Line < Signal Line: 売りシグナル
        - Histogram > 0: 強気（Bullish）
        - Histogram < 0: 弱気（Bearish）

        Args:
            data (pd.Series): 価格データ（通常はclose）
            fast (int): 短期EMA期間（デフォルト: 12）
            slow (int): 長期EMA期間（デフォルト: 26）
            signal (int): シグナルライン期間（デフォルト: 9）

        Returns:
            Dict[str, pd.Series]: MACD、シグナル、ヒストグラムを含む辞書
                {
                    'macd': MACD Line,
                    'signal': Signal Line,
                    'histogram': Histogram
                }

        Example:
            >>> macd_data = TechnicalIndicators.calculate_macd(df['close'])
            >>> macd_line = macd_data['macd']
            >>> signal_line = macd_data['signal']
            >>> histogram = macd_data['histogram']
        """
        # 短期EMAと長期EMAを計算
        ema_fast = data.ewm(span=fast, adjust=False).mean()
        ema_slow = data.ewm(span=slow, adjust=False).mean()

        # MACDラインを計算
        macd_line = ema_fast - ema_slow

        # シグナルラインを計算
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()

        # ヒストグラムを計算
        histogram = macd_line - signal_line

        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }

    @staticmethod
    def calculate_atr(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """
        ATR（平均真の範囲）を計算

        【計算式】
        TR = max(High - Low, |High - Close(前日)|, |Low - Close(前日)|)
        ATR = TR の移動平均（period期間）

        【用途】
        - ボラティリティの測定
        - ストップロスの設定
        - ポジションサイズの調整

        Args:
            high (pd.Series): 高値データ
            low (pd.Series): 安値データ
            close (pd.Series): 終値データ
            period (int): 期間（デフォルト: 14）

        Returns:
            pd.Series: ATR値のシリーズ

        Example:
            >>> atr = TechnicalIndicators.calculate_atr(
            ...     df['high'], df['low'], df['close'], 14
            ... )
            >>> # ATRが大きい = ボラティリティ高
            >>> high_volatility = atr > atr.mean() * 1.5
        """
        # True Range（真の範囲）を計算
        # TR = max(H-L, |H-C(前日)|, |L-C(前日)|)
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        # 3つのうち最大値を取得
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # ATRを計算（移動平均）
        atr = tr.rolling(window=period).mean()

        return atr

    @staticmethod
    def calculate_bollinger_bands(
        data: pd.Series,
        period: int = 20,
        std_dev: float = 2.0
    ) -> Dict[str, pd.Series]:
        """
        ボリンジャーバンド（Bollinger Bands）を計算

        【計算式】
        Middle Band = SMA(period)
        Upper Band = Middle Band + (std_dev × 標準偏差)
        Lower Band = Middle Band - (std_dev × 標準偏差)

        【解釈】
        - 価格がUpper Bandに接近: 買われすぎ
        - 価格がLower Bandに接近: 売られすぎ
        - バンド幅が広い: ボラティリティ高
        - バンド幅が狭い: ボラティリティ低（ブレイク前兆）

        Args:
            data (pd.Series): 価格データ（通常はclose）
            period (int): 期間（デフォルト: 20）
            std_dev (float): 標準偏差の倍数（デフォルト: 2.0）

        Returns:
            Dict[str, pd.Series]: 上限、中央、下限バンドを含む辞書
                {
                    'upper': Upper Band,
                    'middle': Middle Band (SMA),
                    'lower': Lower Band
                }

        Example:
            >>> bb = TechnicalIndicators.calculate_bollinger_bands(df['close'])
            >>> upper = bb['upper']
            >>> middle = bb['middle']
            >>> lower = bb['lower']
            >>> # 価格がバンドを超えたかチェック
            >>> above_upper = df['close'] > upper
            >>> below_lower = df['close'] < lower
        """
        # 移動平均（中央バンド）を計算
        sma = data.rolling(window=period).mean()

        # 標準偏差を計算
        std = data.rolling(window=period).std()

        # 上限バンドと下限バンドを計算
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)

        return {
            'upper': upper_band,
            'middle': sma,
            'lower': lower_band
        }

    @staticmethod
    def calculate_support_resistance(
        high: pd.Series,
        low: pd.Series,
        window: int = 20
    ) -> Dict[str, float]:
        """
        サポート・レジスタンスレベルを計算

        【計算方法】
        - レジスタンス: 直近window期間の最高値
        - サポート: 直近window期間の最安値

        【用途】
        - エントリー/エグジットポイントの判断
        - ストップロスの設定
        - 価格目標の設定

        Args:
            high (pd.Series): 高値データ
            low (pd.Series): 安値データ
            window (int): 期間（デフォルト: 20）

        Returns:
            Dict[str, float]: レジスタンスとサポートレベル
                {
                    'resistance': レジスタンス（上値抵抗線）,
                    'support': サポート（下値支持線）
                }

        Example:
            >>> sr = TechnicalIndicators.calculate_support_resistance(
            ...     df['high'], df['low'], window=20
            ... )
            >>> print(f"レジスタンス: {sr['resistance']}")
            >>> print(f"サポート: {sr['support']}")
        """
        # 直近window期間のデータを取得
        recent_high = high.tail(window)
        recent_low = low.tail(window)

        # サポート・レジスタンスレベルを計算
        resistance = recent_high.max()
        support = recent_low.min()

        return {
            'resistance': resistance,
            'support': support
        }

    def calculate_all(
        self,
        ohlcv: pd.DataFrame,
        ema_short: int = 20,
        ema_long: int = 50
    ) -> Dict[str, any]:
        """
        全てのテクニカル指標を一度に計算

        【計算される指標】
        1. EMA（短期・長期）
        2. RSI
        3. MACD
        4. ATR
        5. ボリンジャーバンド
        6. サポート・レジスタンス

        Args:
            ohlcv (pd.DataFrame): OHLCVデータフレーム
                必須カラム: open, high, low, close, volume
            ema_short (int): 短期EMA期間（デフォルト: 20）
            ema_long (int): 長期EMA期間（デフォルト: 50）

        Returns:
            Dict[str, any]: 全ての指標を含む辞書

        Example:
            >>> ti = TechnicalIndicators()
            >>> indicators = ti.calculate_all(ohlcv_df)
            >>> print(indicators['ema_short'].tail())
            >>> print(indicators['rsi'].tail())
        """
        self.logger.info("全テクニカル指標の計算開始")

        indicators = {}

        try:
            # EMA（短期・長期）
            indicators['ema_short'] = self.calculate_ema(
                ohlcv['close'], ema_short
            )
            indicators['ema_long'] = self.calculate_ema(
                ohlcv['close'], ema_long
            )

            # RSI
            indicators['rsi'] = self.calculate_rsi(ohlcv['close'], 14)

            # MACD
            macd_data = self.calculate_macd(ohlcv['close'])
            indicators['macd'] = macd_data

            # ATR
            indicators['atr'] = self.calculate_atr(
                ohlcv['high'],
                ohlcv['low'],
                ohlcv['close'],
                14
            )

            # ボリンジャーバンド
            indicators['bollinger'] = self.calculate_bollinger_bands(
                ohlcv['close'], 20, 2.0
            )

            # サポート・レジスタンス
            indicators['support_resistance'] = self.calculate_support_resistance(
                ohlcv['high'],
                ohlcv['low'],
                20
            )

            self.logger.info("全テクニカル指標の計算完了")

        except Exception as e:
            self.logger.error(f"指標計算エラー: {e}")
            raise

        return indicators


# モジュールテスト用のメイン関数
if __name__ == "__main__":
    """
    モジュールの動作確認用コード

    実行方法:
        python -m src.data_processing.technical_indicators
    """
    import sys
    sys.path.insert(0, '/home/user/fx-ai-autotrade')

    from src.data_processing.tick_loader import TickDataLoader
    from src.data_processing.timeframe_converter import TimeframeConverter

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

        print("\n=== 全テクニカル指標の計算 ===")
        indicators = ti.calculate_all(ohlcv_h1)

        # 結果を表示
        print(f"\nEMA（短期）最新値: {indicators['ema_short'].iloc[-1]:.3f}")
        print(f"EMA（長期）最新値: {indicators['ema_long'].iloc[-1]:.3f}")
        print(f"RSI最新値: {indicators['rsi'].iloc[-1]:.2f}")
        print(f"MACD最新値: {indicators['macd']['macd'].iloc[-1]:.5f}")
        print(f"ATR最新値: {indicators['atr'].iloc[-1]:.5f}")
        print(f"BB上限: {indicators['bollinger']['upper'].iloc[-1]:.3f}")
        print(f"BB中央: {indicators['bollinger']['middle'].iloc[-1]:.3f}")
        print(f"BB下限: {indicators['bollinger']['lower'].iloc[-1]:.3f}")
        print(f"レジスタンス: {indicators['support_resistance']['resistance']:.3f}")
        print(f"サポート: {indicators['support_resistance']['support']:.3f}")

    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
