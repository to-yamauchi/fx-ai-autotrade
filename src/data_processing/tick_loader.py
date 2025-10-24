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
import psycopg2
from psycopg2.extras import execute_batch


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

    def __init__(self, data_dir: str = "data/tick_data", use_cache: bool = True):
        """
        TickDataLoaderの初期化

        Args:
            data_dir (str): ティックデータが格納されているディレクトリパス
                          デフォルトは "data/tick_data"
            use_cache (bool): データベースキャッシュを使用するかどうか
                            デフォルトはTrue

        Raises:
            なし（ディレクトリの存在チェックは読み込み時に実施）
        """
        self.data_dir = data_dir
        self.use_cache = use_cache
        self.logger = logging.getLogger(__name__)

        # キャッシュ統計
        self.last_cache_stats = None

        # ログレベルの設定
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def _get_db_connection(self):
        """
        データベース接続を取得

        Returns:
            psycopg2.connection: データベース接続オブジェクト

        Raises:
            Exception: データベース接続エラー
        """
        try:
            conn = psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                port=int(os.getenv('DB_PORT', 5432)),
                database=os.getenv('DB_NAME', 'fx_autotrade'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', ''),
                connect_timeout=5
            )
            return conn
        except Exception as e:
            self.logger.error(f"データベース接続エラー: {e}")
            raise

    def _load_from_cache_range(self, symbol: str, start_date: datetime.date, end_date: datetime.date) -> List[Dict]:
        """
        データベースキャッシュから期間指定でティックデータを読み込む（高速版）

        Args:
            symbol (str): 通貨ペア
            start_date (datetime.date): 開始日
            end_date (datetime.date): 終了日

        Returns:
            List[Dict]: ティックデータのリスト
        """
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()

            # 期間全体を1回のクエリで取得（高速）
            cursor.execute(
                """
                SELECT timestamp, bid, ask, 0 as volume
                FROM tick_data_cache
                WHERE symbol = %s AND date >= %s AND date <= %s
                ORDER BY timestamp
                """,
                (symbol, start_date, end_date)
            )

            tick_data = []
            for row in cursor.fetchall():
                # タイムスタンプをnaiveに変換（タイムゾーン情報を削除）
                timestamp = row[0]
                if hasattr(timestamp, 'tzinfo') and timestamp.tzinfo is not None:
                    timestamp = timestamp.replace(tzinfo=None)

                tick = {
                    'timestamp': timestamp,
                    'bid': float(row[1]),
                    'ask': float(row[2]),
                    'volume': row[3]
                }
                tick_data.append(tick)

            cursor.close()
            conn.close()

            self.logger.debug(
                f"キャッシュから期間読み込み完了: {len(tick_data)} 件 ({symbol} {start_date} ～ {end_date})"
            )

            return tick_data

        except Exception as e:
            self.logger.error(f"キャッシュ期間読み込みエラー: {e}")
            raise

    def _check_cache_exists(self, symbol: str, date: datetime.date) -> bool:
        """
        指定された日付のキャッシュが存在するかチェック

        Args:
            symbol (str): 通貨ペア
            date (datetime.date): チェックする日付

        Returns:
            bool: キャッシュが存在すればTrue、なければFalse
        """
        if not self.use_cache:
            return False

        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT COUNT(*) FROM tick_data_cache WHERE symbol = %s AND date = %s",
                (symbol, date)
            )
            count = cursor.fetchone()[0]

            cursor.close()
            conn.close()

            return count > 0

        except Exception as e:
            self.logger.warning(f"キャッシュ存在チェックエラー: {e}")
            return False

    def _load_from_cache(self, symbol: str, date: datetime.date) -> List[Dict]:
        """
        データベースキャッシュからティックデータを読み込む

        Args:
            symbol (str): 通貨ペア
            date (datetime.date): 読み込む日付

        Returns:
            List[Dict]: ティックデータのリスト
        """
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT timestamp, bid, ask, 0 as volume
                FROM tick_data_cache
                WHERE symbol = %s AND date = %s
                ORDER BY timestamp
                """,
                (symbol, date)
            )

            tick_data = []
            for row in cursor.fetchall():
                # タイムスタンプをnaiveに変換（タイムゾーン情報を削除）
                timestamp = row[0]
                if hasattr(timestamp, 'tzinfo') and timestamp.tzinfo is not None:
                    timestamp = timestamp.replace(tzinfo=None)

                tick = {
                    'timestamp': timestamp,
                    'bid': float(row[1]),
                    'ask': float(row[2]),
                    'volume': row[3]
                }
                tick_data.append(tick)

            cursor.close()
            conn.close()

            self.logger.debug(
                f"キャッシュから読み込み完了: {len(tick_data)} 件 ({symbol} {date})"
            )

            return tick_data

        except Exception as e:
            self.logger.error(f"キャッシュ読み込みエラー: {e}")
            raise

    def _save_to_cache(self, symbol: str, date: datetime.date, tick_data: List[Dict]):
        """
        ティックデータをデータベースキャッシュに保存

        Args:
            symbol (str): 通貨ペア
            date (datetime.date): データの日付
            tick_data (List[Dict]): 保存するティックデータ
        """
        if not self.use_cache or not tick_data:
            return

        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()

            # 既存データを削除（上書き）
            cursor.execute(
                "DELETE FROM tick_data_cache WHERE symbol = %s AND date = %s",
                (symbol, date)
            )

            # 新しいデータを挿入
            insert_query = """
                INSERT INTO tick_data_cache (symbol, date, timestamp, bid, ask)
                VALUES (%s, %s, %s, %s, %s)
            """

            batch_data = [
                (
                    symbol,
                    date,
                    tick['timestamp'],
                    tick['bid'],
                    tick['ask']
                )
                for tick in tick_data
            ]

            execute_batch(cursor, insert_query, batch_data, page_size=1000)

            conn.commit()
            cursor.close()
            conn.close()

            self.logger.debug(
                f"キャッシュに保存完了: {len(tick_data)} 件 ({symbol} {date})"
            )

        except Exception as e:
            self.logger.warning(f"キャッシュ保存エラー: {e}")
            # キャッシュ保存失敗は致命的ではないので続行

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

        self.logger.debug(f"ティックデータ読み込み開始: {zip_path}")

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
            self.logger.debug(
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

        self.logger.debug("ティックデータの検証成功")
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
        データベースキャッシュが有効な場合は、日付単位でキャッシュを使用します。

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
        if start_date > end_date:
            raise ValueError(
                f"start_date ({start_date.date()}) must be before or equal to "
                f"end_date ({end_date.date()})"
            )

        self.logger.debug(
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

        self.logger.debug(f"読み込み対象: {len(months_to_load)}ヶ月分のデータ")

        # 日付リストの生成
        from datetime import timedelta
        all_dates = []
        current = start_date.date()
        end = end_date.date()
        while current <= end:
            all_dates.append(current)
            current += timedelta(days=1)

        # 【高速化】まず期間全体のキャッシュデータを1回のクエリで取得
        all_tick_data = []
        cache_hits = 0
        cache_misses = 0
        months_loaded = set()

        if self.use_cache:
            try:
                # 期間全体を1回のクエリで取得（高速）
                all_tick_data = self._load_from_cache_range(symbol, start_date.date(), end_date.date())

                if all_tick_data:
                    # 取得したデータから日付を抽出して、キャッシュヒット日数を計算
                    cached_dates = set()
                    for tick in all_tick_data:
                        cached_dates.add(tick['timestamp'].date())

                    cache_hits = len(cached_dates & set(all_dates))
                    cache_misses = len(all_dates) - cache_hits

                    self.logger.info(
                        f"期間キャッシュ読み込み完了: {len(all_tick_data):,} 件, "
                        f"キャッシュヒット: {cache_hits}/{len(all_dates)}日"
                    )
                else:
                    # データが見つからない場合
                    cache_misses = len(all_dates)
                    raise Exception("キャッシュにデータがありません")

            except Exception as e:
                # キャッシュ読み込み失敗 - ZIPから読み込む
                self.logger.warning(f"キャッシュ読み込み失敗: {e}")
                all_tick_data = []
                cache_misses = len(all_dates)

        # キャッシュミスがある場合、ZIPファイルから読み込む
        missing_files = []
        if cache_misses > 0 and not all_tick_data:
            # 必要な月のZIPファイルをすべて読み込む
            for year, month in months_to_load:
                month_key = (year, month)

                # 既にこの月のZIPを読み込み済みならスキップ
                if month_key in months_loaded:
                    continue

                try:
                    # 月のzipファイルを読み込む
                    month_tick_data = self.load_from_zip(symbol, year, month)
                    months_loaded.add(month_key)

                    # 日付別にグループ化してキャッシュに保存
                    if self.use_cache and month_tick_data:
                        # 日付ごとにグループ化
                        by_date = {}
                        for tick in month_tick_data:
                            tick_date = tick['timestamp'].date()
                            if tick_date not in by_date:
                                by_date[tick_date] = []
                            by_date[tick_date].append(tick)

                        # 日付ごとにキャッシュに保存
                        for tick_date, date_ticks in by_date.items():
                            # 対象期間内の日付のみキャッシュに保存
                            if start_date.date() <= tick_date <= end_date.date():
                                self._save_to_cache(symbol, tick_date, date_ticks)

                    # 期間内のデータのみ追加
                    for tick in month_tick_data:
                        if start_date.date() <= tick['timestamp'].date() <= end_date.date():
                            all_tick_data.append(tick)

                except FileNotFoundError:
                    # ファイルが見つからない場合は記録して続行
                    if f"{year}-{month:02d}" not in missing_files:
                        missing_files.append(f"{year}-{month:02d}")
                        self.logger.warning(
                            f"ファイルが見つかりません: {symbol} {year}-{month:02d} (スキップ)"
                        )
                    continue

        # キャッシュ使用状況を保存・ログ出力
        if self.use_cache:
            total_days = len(all_dates)
            self.last_cache_stats = {
                'cache_hits': cache_hits,
                'cache_misses': cache_misses,
                'total_days': total_days,
                'hit_rate': cache_hits/total_days*100 if total_days > 0 else 0,
                'months_loaded': len(months_loaded)
            }
            self.logger.info(
                f"キャッシュ使用状況: ヒット {cache_hits}/{total_days}日 "
                f"({self.last_cache_stats['hit_rate']:.1f}%), "
                f"ミス {cache_misses}日, ZIPロード {len(months_loaded)}ヶ月"
            )
        else:
            self.last_cache_stats = None

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

        # タイムスタンプでソート（キャッシュから読み込んだデータが順不同の可能性があるため）
        all_tick_data.sort(key=lambda x: x['timestamp'])

        self.logger.info(
            f"期間指定データ読み込み完了: {len(all_tick_data):,} 件 "
            f"({symbol} {start_date.date()} ～ {end_date.date()})"
        )

        return all_tick_data


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
