"""
========================================
時間足変換モジュール
========================================

ファイル名: timeframe_converter.py
モジュールパス: src/data_processing/timeframe_converter.py

【概要】
ティックデータから複数の時間足（D1/H4/H1/M15）のOHLCVデータを生成する
モジュールです。pandasのresample機能を使用して、効率的に時間足データを
生成します。

【主な機能】
1. ティックデータから時間足データへの変換
2. OHLCV形式（始値、高値、安値、終値、出来高）の生成
3. 複数の時間足に同時対応（D1、H4、H1、M15）
4. 欠損データの処理

【使用例】
>>> from src.data_processing.timeframe_converter import TimeframeConverter
>>> converter = TimeframeConverter()
>>> ohlcv_h1 = converter.convert(tick_data, "H1")
>>> print(ohlcv_h1.head())

【対応時間足】
- D1: 日足（1日）
- H4: 4時間足
- H1: 1時間足
- M15: 15分足

【依存関係】
- pandas: データフレーム操作とリサンプリング
- numpy: 数値計算
- typing: 型ヒント

【作成日】2025-10-22
【更新日】2025-10-22
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging


class TimeframeConverter:
    """
    ティックデータを時間足データに変換するクラス

    このクラスは、ティックデータ（リスト形式）を受け取り、
    指定された時間足のOHLCVデータ（pandas DataFrame）に変換します。

    Attributes:
        TIMEFRAMES (Dict[str, timedelta]): サポートされている時間足の定義
        logger (logging.Logger): ロガーインスタンス

    Methods:
        convert: ティックデータを指定した時間足に変換
        convert_all: 全ての時間足を一度に変換
    """

    # サポートされている時間足の定義
    TIMEFRAMES = {
        'D1': timedelta(days=1),      # 日足
        'H4': timedelta(hours=4),     # 4時間足
        'H1': timedelta(hours=1),     # 1時間足
        'M15': timedelta(minutes=15)  # 15分足
    }

    def __init__(self):
        """
        TimeframeConverterの初期化

        Raises:
            なし
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

    def convert(
        self,
        tick_data: List[Dict],
        timeframe: str,
        price_type: str = 'mid'
    ) -> pd.DataFrame:
        """
        ティックデータを指定した時間足に変換

        【処理フロー】
        1. ティックデータをDataFrameに変換
        2. 価格タイプ（bid/ask/mid）を選択
        3. pandas.resampleで指定時間足にリサンプリング
        4. OHLCV形式に集約
        5. 欠損データの処理

        Args:
            tick_data (List[Dict]): ティックデータのリスト
                各要素は以下の構造:
                {
                    'timestamp': datetime,
                    'bid': float,
                    'ask': float,
                    'volume': int
                }
            timeframe (str): 時間足（"D1", "H4", "H1", "M15"）
            price_type (str): 価格タイプ
                - "mid": Bid/Askの中値（デフォルト）
                - "bid": Bid価格
                - "ask": Ask価格

        Returns:
            pd.DataFrame: OHLCV形式のデータフレーム
                カラム: open, high, low, close, volume
                インデックス: timestamp（DatetimeIndex）

        Raises:
            ValueError: 無効な時間足が指定された場合
            ValueError: tick_dataが空の場合

        Example:
            >>> converter = TimeframeConverter()
            >>> tick_data = [
            ...     {'timestamp': datetime(2024, 1, 1, 0, 0), 'bid': 145.0, 'ask': 145.1, 'volume': 100},
            ...     {'timestamp': datetime(2024, 1, 1, 0, 1), 'bid': 145.1, 'ask': 145.2, 'volume': 150},
            ... ]
            >>> ohlcv = converter.convert(tick_data, "H1")
            >>> print(ohlcv.columns)
            Index(['open', 'high', 'low', 'close', 'volume'], dtype='object')
        """
        # 時間足の検証
        if timeframe not in self.TIMEFRAMES:
            raise ValueError(
                f"無効な時間足: {timeframe}。"
                f"サポートされている時間足: {list(self.TIMEFRAMES.keys())}"
            )

        # データの検証
        if not tick_data:
            raise ValueError("tick_dataが空です")

        self.logger.info(
            f"時間足変換開始: {len(tick_data)} 件のティックデータ → {timeframe}"
        )

        # DataFrameに変換
        df = pd.DataFrame(tick_data)

        # タイムスタンプをインデックスに設定
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp')

        # 価格タイプの選択
        if price_type == 'mid':
            # Bid/Askの中値を計算
            df['price'] = (df['bid'] + df['ask']) / 2
        elif price_type == 'bid':
            df['price'] = df['bid']
        elif price_type == 'ask':
            df['price'] = df['ask']
        else:
            raise ValueError(
                f"無効な価格タイプ: {price_type}。"
                f"サポートされている価格タイプ: mid, bid, ask"
            )

        # リサンプリング周期を取得
        resample_rule = self._get_resample_rule(timeframe)

        # OHLCV形式に変換
        # pandasのresampleを使用して時間足データを生成
        ohlcv = df['price'].resample(resample_rule).agg([
            ('open', 'first'),   # 始値: 期間内の最初の価格
            ('high', 'max'),     # 高値: 期間内の最高価格
            ('low', 'min'),      # 安値: 期間内の最安価格
            ('close', 'last')    # 終値: 期間内の最後の価格
        ])

        # 出来高を集計
        volume = df['volume'].resample(resample_rule).sum()
        ohlcv['volume'] = volume

        # 欠損データ（取引がない期間）を削除
        ohlcv = ohlcv.dropna()

        # データ型を最適化
        ohlcv = ohlcv.astype({
            'open': 'float64',
            'high': 'float64',
            'low': 'float64',
            'close': 'float64',
            'volume': 'int64'
        })

        self.logger.info(
            f"時間足変換完了: {len(ohlcv)} 本の{timeframe}ローソク足を生成"
        )

        return ohlcv

    def convert_all(
        self,
        tick_data: List[Dict],
        price_type: str = 'mid'
    ) -> Dict[str, pd.DataFrame]:
        """
        全ての時間足を一度に変換

        【処理内容】
        全てのサポートされている時間足（D1/H4/H1/M15）に対して
        一度にOHLCVデータを生成します。

        Args:
            tick_data (List[Dict]): ティックデータのリスト
            price_type (str): 価格タイプ（"mid", "bid", "ask"）

        Returns:
            Dict[str, pd.DataFrame]: 時間足名をキーとするOHLCVデータの辞書
                例: {
                    'D1': DataFrame(...),
                    'H4': DataFrame(...),
                    'H1': DataFrame(...),
                    'M15': DataFrame(...)
                }

        Example:
            >>> converter = TimeframeConverter()
            >>> all_ohlcv = converter.convert_all(tick_data)
            >>> print(all_ohlcv.keys())
            dict_keys(['D1', 'H4', 'H1', 'M15'])
            >>> print(f"H1足: {len(all_ohlcv['H1'])} 本")
        """
        self.logger.info(
            f"全時間足変換開始: {len(tick_data)} 件のティックデータ"
        )

        result = {}

        for timeframe in self.TIMEFRAMES.keys():
            try:
                ohlcv = self.convert(tick_data, timeframe, price_type)
                result[timeframe] = ohlcv
                self.logger.debug(
                    f"{timeframe}: {len(ohlcv)} 本のローソク足"
                )
            except Exception as e:
                self.logger.error(
                    f"{timeframe}の変換に失敗: {e}"
                )
                # エラーが発生しても他の時間足の変換を続行
                continue

        self.logger.info(
            f"全時間足変換完了: {len(result)} 種類の時間足を生成"
        )

        return result

    def _get_resample_rule(self, timeframe: str) -> str:
        """
        pandas resampleルールを取得

        【対応表】
        - D1 → 'D' (1日)
        - H4 → '4H' (4時間)
        - H1 → '1H' (1時間)
        - M15 → '15T' (15分、Tは分を表す)

        Args:
            timeframe (str): 時間足名

        Returns:
            str: pandasのresampleルール

        Raises:
            ValueError: 無効な時間足が指定された場合
        """
        rules = {
            'D1': 'D',
            'H4': '4H',
            'H1': '1H',
            'M15': '15T'
        }

        if timeframe not in rules:
            raise ValueError(f"無効な時間足: {timeframe}")

        return rules[timeframe]

    def validate_ohlcv(self, ohlcv: pd.DataFrame) -> bool:
        """
        OHLCVデータの妥当性を検証

        【検証項目】
        1. 必須カラムが存在するか
        2. High >= Low >= 0
        3. High >= Open, Close
        4. Low <= Open, Close
        5. Volume >= 0

        Args:
            ohlcv (pd.DataFrame): OHLCVデータフレーム

        Returns:
            bool: 検証成功時True、失敗時False
        """
        # 必須カラムのチェック
        required_columns = ['open', 'high', 'low', 'close', 'volume']

        for col in required_columns:
            if col not in ohlcv.columns:
                self.logger.error(f"必須カラム欠落: {col}")
                return False

        # データが空でないかチェック
        if len(ohlcv) == 0:
            self.logger.warning("OHLCVデータが空です")
            return False

        # 最初の10件をサンプルチェック
        sample = ohlcv.head(10)

        for idx, row in sample.iterrows():
            # High >= Low のチェック
            if row['high'] < row['low']:
                self.logger.error(
                    f"High < Low: {idx} - High={row['high']}, Low={row['low']}"
                )
                return False

            # High >= Open, Close のチェック
            if row['high'] < row['open'] or row['high'] < row['close']:
                self.logger.warning(
                    f"High < Open/Close: {idx}"
                )

            # Low <= Open, Close のチェック
            if row['low'] > row['open'] or row['low'] > row['close']:
                self.logger.warning(
                    f"Low > Open/Close: {idx}"
                )

            # 価格が正の値かチェック
            if row['low'] <= 0:
                self.logger.error(f"無効な価格: {idx} - Low={row['low']}")
                return False

            # Volumeが非負かチェック
            if row['volume'] < 0:
                self.logger.error(
                    f"無効な出来高: {idx} - Volume={row['volume']}"
                )
                return False

        self.logger.info("OHLCVデータの検証成功")
        return True


# モジュールテスト用のメイン関数
if __name__ == "__main__":
    """
    モジュールの動作確認用コード

    実行方法:
        python -m src.data_processing.timeframe_converter
    """
    import sys
    sys.path.insert(0, '/home/user/fx-ai-autotrade')

    from src.data_processing.tick_loader import TickDataLoader

    # ロギング設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # ティックデータを読み込み
    loader = TickDataLoader(data_dir="data/tick_data")

    try:
        # サンプルデータ読み込み（2024年9月のUSDJPY）
        tick_data = loader.load_from_zip("USDJPY", 2024, 9)

        # 時間足変換
        converter = TimeframeConverter()

        # 1時間足に変換
        print("\n=== H1足への変換 ===")
        ohlcv_h1 = converter.convert(tick_data, "H1")
        print(f"生成されたローソク足: {len(ohlcv_h1)} 本")
        print("\n最初の5本:")
        print(ohlcv_h1.head())

        # 全時間足に変換
        print("\n=== 全時間足への変換 ===")
        all_ohlcv = converter.convert_all(tick_data)

        for tf, data in all_ohlcv.items():
            print(f"{tf}: {len(data)} 本")
            if converter.validate_ohlcv(data):
                print(f"  ✓ データ検証成功")
            else:
                print(f"  ✗ データ検証失敗")

    except Exception as e:
        print(f"エラー: {e}")
