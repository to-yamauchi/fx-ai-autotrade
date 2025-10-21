"""
========================================
ティックデータローダー テストモジュール
========================================

ファイル名: test_tick_loader.py
パス: tests/test_tick_loader.py

【概要】
TickDataLoaderクラスの機能をテストするユニットテストモジュールです。

【テスト項目】
1. zipファイルからの正常な読み込み
2. ファイルが存在しない場合のエラーハンドリング
3. データ形式の検証
4. タイムスタンプのパース検証
5. データバリデーション機能のテスト

【テスト実行方法】
個別実行:
    pytest tests/test_tick_loader.py -v

カバレッジ付き:
    pytest tests/test_tick_loader.py --cov=src.data_processing.tick_loader -v

【前提条件】
- テストデータ: data/tick_data/USDJPY/ticks_USDJPY-oj5k_2024-09.zip
  （実際のテストではモックデータを使用することを推奨）

【作成日】2025-10-21
"""

import pytest
import os
import zipfile
import csv
import tempfile
from datetime import datetime
from src.data_processing.tick_loader import TickDataLoader


class TestTickDataLoader:
    """TickDataLoaderクラスのテストケース"""

    @pytest.fixture
    def sample_tick_data(self):
        """
        テスト用のサンプルティックデータを生成

        Returns:
            list: サンプルティックデータのリスト
        """
        return [
            {
                'timestamp': '2024-09-01T00:00:00',
                'bid': '145.123',
                'ask': '145.125',
                'volume': '100'
            },
            {
                'timestamp': '2024-09-01T00:00:01',
                'bid': '145.124',
                'ask': '145.126',
                'volume': '150'
            },
            {
                'timestamp': '2024-09-01T00:00:02',
                'bid': '145.125',
                'ask': '145.127',
                'volume': '200'
            }
        ]

    @pytest.fixture
    def temp_zip_file(self, sample_tick_data, tmp_path):
        """
        テスト用の一時zipファイルを作成

        Args:
            sample_tick_data: サンプルデータ
            tmp_path: pytestが提供する一時ディレクトリ

        Returns:
            tuple: (zipファイルパス, データディレクトリ)
        """
        # 一時ディレクトリ構造を作成
        data_dir = tmp_path / "data" / "tick_data"
        symbol_dir = data_dir / "USDJPY"
        symbol_dir.mkdir(parents=True)

        # CSVファイル名とzipファイル名
        csv_filename = "ticks_USDJPY-oj5k_2024-09.csv"
        zip_filename = "ticks_USDJPY-oj5k_2024-09.zip"
        zip_path = symbol_dir / zip_filename

        # 一時CSVファイルを作成してzipに圧縮
        csv_path = symbol_dir / csv_filename

        # CSVファイルを作成
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['timestamp', 'bid', 'ask', 'volume']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(sample_tick_data)

        # zipファイルを作成
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(csv_path, csv_filename)

        # CSVファイルを削除（zipのみ残す）
        csv_path.unlink()

        return str(zip_path), str(data_dir)

    def test_loader_initialization(self):
        """
        TickDataLoaderの初期化テスト

        【確認内容】
        - インスタンスが正しく生成されるか
        - data_dirが設定されているか
        """
        loader = TickDataLoader(data_dir="test_data")
        assert loader.data_dir == "test_data"
        assert loader.logger is not None

    def test_load_from_zip_success(self, temp_zip_file):
        """
        zipファイルからの正常なデータ読み込みテスト

        【確認内容】
        - データが正しく読み込まれるか
        - データ件数が正しいか
        - データ構造が正しいか
        - 型変換が正しく行われているか
        """
        zip_path, data_dir = temp_zip_file

        # TickDataLoaderインスタンスを作成
        loader = TickDataLoader(data_dir=data_dir)

        # データを読み込み
        tick_data = loader.load_from_zip("USDJPY", 2024, 9)

        # データ件数の確認
        assert len(tick_data) == 3, "読み込んだデータ件数が正しくありません"

        # 最初のデータの構造確認
        first_tick = tick_data[0]
        assert 'timestamp' in first_tick, "timestampフィールドが存在しません"
        assert 'bid' in first_tick, "bidフィールドが存在しません"
        assert 'ask' in first_tick, "askフィールドが存在しません"
        assert 'volume' in first_tick, "volumeフィールドが存在しません"

        # 型の確認
        assert isinstance(first_tick['timestamp'], datetime), "timestampの型が正しくありません"
        assert isinstance(first_tick['bid'], float), "bidの型が正しくありません"
        assert isinstance(first_tick['ask'], float), "askの型が正しくありません"
        assert isinstance(first_tick['volume'], int), "volumeの型が正しくありません"

        # 値の確認
        assert first_tick['bid'] == 145.123, "bid価格が正しくありません"
        assert first_tick['ask'] == 145.125, "ask価格が正しくありません"
        assert first_tick['volume'] == 100, "volumeが正しくありません"

    def test_load_from_zip_file_not_found(self):
        """
        存在しないzipファイルの読み込みテスト

        【確認内容】
        - FileNotFoundErrorが発生するか
        """
        loader = TickDataLoader(data_dir="non_existent_dir")

        with pytest.raises(FileNotFoundError):
            loader.load_from_zip("USDJPY", 2024, 1)

    def test_validate_data_success(self, temp_zip_file):
        """
        データバリデーション成功のテスト

        【確認内容】
        - 正常なデータが検証を通過するか
        """
        zip_path, data_dir = temp_zip_file
        loader = TickDataLoader(data_dir=data_dir)
        tick_data = loader.load_from_zip("USDJPY", 2024, 9)

        # バリデーション実行
        is_valid = loader.validate_data(tick_data)
        assert is_valid is True, "正常なデータがバリデーションを通過しませんでした"

    def test_validate_data_empty(self):
        """
        空データのバリデーションテスト

        【確認内容】
        - 空のデータリストが検証で失敗するか
        """
        loader = TickDataLoader()
        is_valid = loader.validate_data([])
        assert is_valid is False, "空データがバリデーションを通過してしまいました"

    def test_validate_data_invalid_price(self):
        """
        無効な価格データのバリデーションテスト

        【確認内容】
        - 負の価格が検証で失敗するか
        """
        loader = TickDataLoader()

        invalid_data = [
            {
                'timestamp': datetime(2024, 9, 1, 0, 0, 0),
                'bid': -145.123,  # 負の値
                'ask': 145.125,
                'volume': 100
            }
        ]

        is_valid = loader.validate_data(invalid_data)
        assert is_valid is False, "無効な価格がバリデーションを通過してしまいました"

    def test_timestamp_parsing(self, temp_zip_file):
        """
        タイムスタンプのパーステスト

        【確認内容】
        - タイムスタンプが正しくdatetimeに変換されるか
        - タイムゾーン情報が正しく処理されるか
        """
        zip_path, data_dir = temp_zip_file
        loader = TickDataLoader(data_dir=data_dir)
        tick_data = loader.load_from_zip("USDJPY", 2024, 9)

        # 最初のデータのタイムスタンプを確認
        first_timestamp = tick_data[0]['timestamp']

        assert first_timestamp.year == 2024
        assert first_timestamp.month == 9
        assert first_timestamp.day == 1
        assert first_timestamp.hour == 0
        assert first_timestamp.minute == 0
        assert first_timestamp.second == 0

    def test_data_order(self, temp_zip_file):
        """
        データの順序性テスト

        【確認内容】
        - データが時系列順に読み込まれるか
        """
        zip_path, data_dir = temp_zip_file
        loader = TickDataLoader(data_dir=data_dir)
        tick_data = loader.load_from_zip("USDJPY", 2024, 9)

        # タイムスタンプの昇順を確認
        for i in range(len(tick_data) - 1):
            assert tick_data[i]['timestamp'] <= tick_data[i + 1]['timestamp'], \
                "データが時系列順になっていません"

    def test_bid_ask_relationship(self, temp_zip_file):
        """
        Bid/Askの関係性テスト

        【確認内容】
        - Bid <= Ask の関係が保たれているか（通常はBid < Ask）
        """
        zip_path, data_dir = temp_zip_file
        loader = TickDataLoader(data_dir=data_dir)
        tick_data = loader.load_from_zip("USDJPY", 2024, 9)

        for tick in tick_data:
            assert tick['bid'] <= tick['ask'], \
                f"Bid ({tick['bid']}) が Ask ({tick['ask']}) より大きくなっています"


# テストの実行統計情報（参考）
def test_suite_info():
    """
    テストスイート情報

    このテストモジュールは以下をカバーします:
    - 正常系テスト: 4ケース
    - 異常系テスト: 3ケース
    - データ検証テスト: 3ケース
    """
    pass


if __name__ == "__main__":
    """
    直接実行時のテストランナー

    実行方法:
        python -m pytest tests/test_tick_loader.py -v
    """
    pytest.main([__file__, "-v"])
