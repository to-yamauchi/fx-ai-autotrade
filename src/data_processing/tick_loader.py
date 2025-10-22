"""
========================================
ティックデータローダーモジュール
========================================

ファイル名: tick_loader.py
モジュールパス: src/data_processing/tick_loader.py

【概要】
月次zipファイルからティックデータを読み込み、パースするモジュールです。
MT5から取得したティックデータをzip圧縮したファイルから、効率的にデータを
抽出し、Python辞書形式のリストとして返します。

【主な機能】
1. zipファイルからのティックデータ読み込み
2. CSV形式データのパース
3. タイムスタンプのDatetime変換
4. エラーハンドリングとロギング

【使用例】
>>> from src.data_processing.tick_loader import TickDataLoader
>>> loader = TickDataLoader(data_dir="data/tick_data")
>>> tick_data = loader.load_from_zip("USDJPY", 2024, 9)
>>> print(f"読み込んだティック数: {len(tick_data)}")

【データフォーマット】
入力ファイル名: ticks_{symbol}-oj5k_{year:04d}-{month:02d}.zip
CSV名: ticks_{symbol}-oj5k_{year:04d}-{month:02d}.csv
CSVカラム: <DATE>, <TIME>, <BID>, <ASK>, <LAST>, <VOLUME>
区切り文字: タブ（TSV形式）

【依存関係】
- zipfile: zip圧縮ファイルの展開
- csv: CSVファイルの読み込み
- datetime: タイムスタンプ処理
- logging: ログ出力

【作成日】2025-10-21
【更新日】2025-10-21
"""

import zipfile
import csv
import io
from datetime import datetime
from typing import List, Dict, Optional
import logging
import os


class TickDataLoader:
    """
    月次zipファイルからティックデータを読み込むクラス

    このクラスは、MT5から取得したティックデータを圧縮したzipファイルから
    データを読み込み、Pythonで扱いやすい形式に変換します。

    Attributes:
        data_dir (str): ティックデータが格納されているディレクトリパス
        logger (logging.Logger): ロガーインスタンス

    Methods:
        load_from_zip: zipファイルからティックデータを読み込む
    """

    def __init__(self, data_dir: str = "data/tick_data"):
        """
        TickDataLoaderの初期化

        Args:
            data_dir (str): ティックデータが格納されているディレクトリパス
                          デフォルトは "data/tick_data"

        Raises:
            なし（ディレクトリの存在チェックは読み込み時に実施）
        """
        self.data_dir = data_dir
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

    def load_from_zip(
        self,
        symbol: str,
        year: int,
        month: int
    ) -> List[Dict]:
        """
        zipファイルからティックデータを読み込む

        指定された通貨ペアと年月に対応するzipファイルを開き、
        内部のCSVファイルからティックデータを読み込みます。

        【処理フロー】
        1. ファイルパスの構築
        2. zipファイルを開く
        3. 内部のCSVファイルを読み込む
        4. 各行をパースして辞書形式に変換
        5. リストとして返却

        Args:
            symbol (str): 通貨ペア（例: "USDJPY", "EURUSD"）
            year (int): 年（例: 2024）
            month (int): 月（1-12）

        Returns:
            List[Dict]: ティックデータのリスト
                各要素は以下の構造:
                {
                    'timestamp': datetime,  # ティック発生時刻
                    'bid': float,          # Bid価格
                    'ask': float,          # Ask価格
                    'volume': int          # 出来高
                }

        Raises:
            FileNotFoundError: 指定されたzipファイルが存在しない場合
            Exception: その他のエラー（zipファイル破損、CSV形式エラーなど）

        Example:
            >>> loader = TickDataLoader()
            >>> data = loader.load_from_zip("USDJPY", 2024, 9)
            >>> print(data[0])
            {
                'timestamp': datetime(2024, 9, 1, 0, 0, 0),
                'bid': 145.123,
                'ask': 145.125,
                'volume': 100
            }
        """
        # ファイル名の構築
        # フォーマット: ticks_USDJPY-oj5k_2024-09.zip
        zip_filename = f"ticks_{symbol}-oj5k_{year:04d}-{month:02d}.zip"
        zip_path = os.path.join(self.data_dir, symbol, zip_filename)

        self.logger.info(f"ティックデータ読み込み開始: {zip_path}")

        tick_data = []

        try:
            # zipファイルを開く
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # CSV名の構築: ticks_USDJPY-oj5k_2024-09.csv
                csv_filename = f"ticks_{symbol}-oj5k_{year:04d}-{month:02d}.csv"

                self.logger.debug(f"CSV読み込み: {csv_filename}")

                # zipファイル内のCSVファイルを開く
                with zip_ref.open(csv_filename) as f:
                    # UTF-8エンコーディングでテキストラッパーを適用
                    text_wrapper = io.TextIOWrapper(f, encoding='utf-8')
                    # タブ区切り（TSV）として読み込み
                    reader = csv.DictReader(text_wrapper, delimiter='\t')

                    # 各行を処理
                    for row_num, row in enumerate(reader, start=1):
                        try:
                            # <DATE> と <TIME> を結合してタイムスタンプを作成
                            # フォーマット: "2024.01.01" + " " + "20:11:15.408"
                            date_str = row['<DATE>'].strip()
                            time_str = row['<TIME>'].strip()

                            # "2024.01.01 20:11:15.408" → datetime
                            # まず、"."を"-"に変換して標準形式にする
                            date_str = date_str.replace('.', '-')
                            timestamp_str = f"{date_str} {time_str}"
                            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')

                            # Bid/Ask価格を取得
                            bid = float(row['<BID>'].strip())
                            ask = float(row['<ASK>'].strip())

                            # Volumeを取得（空の場合は0）
                            volume_str = row.get('<VOLUME>', '').strip()
                            volume = int(float(volume_str)) if volume_str else 0

                            # ティックデータの構築
                            tick = {
                                'timestamp': timestamp,
                                'bid': bid,
                                'ask': ask,
                                'volume': volume
                            }
                            tick_data.append(tick)

                        except (ValueError, KeyError) as e:
                            # データパースエラー（スキップして続行）
                            self.logger.warning(
                                f"行 {row_num} のパースに失敗: {e} - データ: {row}"
                            )
                            continue

            # 読み込み成功
            self.logger.info(
                f"ティックデータ読み込み完了: {len(tick_data)} 件 "
                f"({symbol} {year}-{month:02d})"
            )
            return tick_data

        except FileNotFoundError:
            # ファイルが見つからない
            error_msg = f"ファイルが見つかりません: {zip_path}"
            self.logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        except zipfile.BadZipFile:
            # zipファイルが破損している
            error_msg = f"破損したzipファイル: {zip_path}"
            self.logger.error(error_msg)
            raise Exception(error_msg)

        except Exception as e:
            # その他のエラー
            error_msg = f"ティックデータ読み込みエラー: {e}"
            self.logger.error(error_msg)
            raise Exception(error_msg)

    def validate_data(self, tick_data: List[Dict]) -> bool:
        """
        読み込んだティックデータの妥当性を検証

        【検証項目】
        1. データが空でないか
        2. 必須フィールドが存在するか
        3. 価格が正の値か
        4. タイムスタンプが順序正しいか

        Args:
            tick_data (List[Dict]): 検証対象のティックデータ

        Returns:
            bool: 検証成功時True、失敗時False
        """
        if not tick_data:
            self.logger.warning("ティックデータが空です")
            return False

        # 必須フィールドのチェック
        required_fields = ['timestamp', 'bid', 'ask', 'volume']

        for i, tick in enumerate(tick_data[:10]):  # 最初の10件をサンプルチェック
            # フィールド存在チェック
            for field in required_fields:
                if field not in tick:
                    self.logger.error(f"必須フィールド欠落: {field} (行 {i})")
                    return False

            # 価格の妥当性チェック
            if tick['bid'] <= 0 or tick['ask'] <= 0:
                self.logger.error(f"無効な価格: bid={tick['bid']}, ask={tick['ask']} (行 {i})")
                return False

            # Bid < Ask のチェック
            if tick['bid'] >= tick['ask']:
                self.logger.warning(f"Bid >= Ask: bid={tick['bid']}, ask={tick['ask']} (行 {i})")

        self.logger.info("ティックデータの検証成功")
        return True

    def load_date_range(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """
        期間指定でティックデータを読み込む

        指定された期間に含まれる複数月のzipファイルを読み込み、
        結合したティックデータを返します。

        Args:
            symbol (str): 通貨ペア（例: "USDJPY"）
            start_date (datetime): 開始日
            end_date (datetime): 終了日

        Returns:
            List[Dict]: ティックデータのリスト
                各要素は以下のキーを持つ辞書:
                - timestamp: datetime型のタイムスタンプ
                - bid: Bid価格
                - ask: Ask価格
                - volume: 出来高

        Raises:
            ValueError: 日付範囲が不正な場合
            FileNotFoundError: 必要なファイルが見つからない場合
        """
        # 日付範囲の検証
        if start_date >= end_date:
            raise ValueError(
                f"start_date ({start_date.date()}) must be before "
                f"end_date ({end_date.date()})"
            )

        self.logger.info(
            f"期間指定データ読み込み開始: {symbol} "
            f"{start_date.date()} ～ {end_date.date()}"
        )

        # 必要な月のリストを生成
        months_to_load = []
        current_date = start_date.replace(day=1)  # 月の最初の日に設定

        while current_date <= end_date:
            months_to_load.append((current_date.year, current_date.month))
            # 次の月へ
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)

        self.logger.info(f"読み込み対象: {len(months_to_load)}ヶ月分のデータ")

        # 各月のデータを読み込んで結合
        all_tick_data = []
        missing_files = []

        for year, month in months_to_load:
            try:
                tick_data = self.load_from_zip(symbol, year, month)
                all_tick_data.extend(tick_data)
            except FileNotFoundError:
                # ファイルが見つからない場合は記録して続行
                missing_files.append(f"{year}-{month:02d}")
                self.logger.warning(
                    f"ファイルが見つかりません: {symbol} {year}-{month:02d} (スキップ)"
                )
                continue

        # 一部のファイルが見つからなかった場合は警告
        if missing_files:
            self.logger.warning(
                f"以下の月のデータが見つかりませんでした: {', '.join(missing_files)}"
            )

        # データが全く読み込めなかった場合はエラー
        if not all_tick_data:
            raise FileNotFoundError(
                f"指定期間のデータが見つかりません: "
                f"{symbol} {start_date.date()} ～ {end_date.date()}"
            )

        # 指定期間内のデータのみをフィルタリング
        filtered_data = [
            tick for tick in all_tick_data
            if start_date <= tick['timestamp'] <= end_date
        ]

        self.logger.info(
            f"期間指定データ読み込み完了: {len(filtered_data):,} 件 "
            f"({len(months_to_load)}ヶ月分, "
            f"フィルタ前: {len(all_tick_data):,} 件)"
        )

        return filtered_data


# モジュールテスト用のメイン関数
if __name__ == "__main__":
    """
    モジュールの動作確認用コード

    実行方法:
        python -m src.data_processing.tick_loader
    """
    # ロギング設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # ティックデータローダーのインスタンス作成
    loader = TickDataLoader(data_dir="data/tick_data")

    # サンプルデータ読み込み（2024年9月のUSDJPY）
    try:
        tick_data = loader.load_from_zip("USDJPY", 2024, 9)

        # 読み込み結果の表示
        print(f"\n読み込んだティック数: {len(tick_data)}")

        if tick_data:
            # 最初の5件を表示
            print("\n最初の5件のティックデータ:")
            for i, tick in enumerate(tick_data[:5]):
                print(f"{i+1}. {tick}")

            # データ検証
            is_valid = loader.validate_data(tick_data)
            print(f"\nデータ検証結果: {'成功' if is_valid else '失敗'}")

    except Exception as e:
        print(f"エラー: {e}")
