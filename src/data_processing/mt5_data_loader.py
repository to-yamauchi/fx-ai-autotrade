"""
========================================
MT5リアルタイムデータ取得モジュール
========================================

ファイル名: mt5_data_loader.py
パス: src/data_processing/mt5_data_loader.py

【概要】
MetaTrader5から直近のティックデータをリアルタイムで取得します。
DEMO/LIVEモードで使用され、最新の市場データでAI分析を行います。

【主な機能】
1. 直近Nティックの取得
2. 期間指定でのティック取得
3. ティックデータのDataFrame変換

【使用例】
```python
from src.data_processing import MT5DataLoader

loader = MT5DataLoader(symbol='USDJPY')
tick_data = loader.load_recent_ticks(days=30)
```

【作成日】2025-10-23
"""

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import logging
import os


class MT5DataLoader:
    """
    MT5リアルタイムデータ取得クラス

    MetaTrader5に接続して、リアルタイムのティックデータを取得します。
    """

    def __init__(self, symbol: str = 'USDJPY'):
        """
        MT5DataLoaderの初期化

        Args:
            symbol: 通貨ペア（デフォルト: USDJPY）
        """
        self.symbol = symbol
        self.logger = logging.getLogger(__name__)
        self._mt5_initialized = False

    def _ensure_mt5_initialized(self) -> bool:
        """
        MT5が初期化されているか確認し、必要なら初期化する

        Returns:
            bool: True=初期化済み、False=初期化失敗
        """
        # 既に初期化されているか確認
        if mt5.terminal_info() is not None:
            self._mt5_initialized = True
            return True

        # MT5が初期化されていない場合、初期化を試みる
        self.logger.info("MT5 is not initialized. Attempting to initialize...")

        # MT5初期化
        if not mt5.initialize():
            error_code = mt5.last_error()
            self.logger.error(
                f"MT5 initialization failed: {error_code}. "
                "Make sure MT5 is running."
            )
            return False

        # ログイン情報を環境変数から取得
        mt5_login = os.getenv('MT5_LOGIN')
        mt5_password = os.getenv('MT5_PASSWORD')
        mt5_server = os.getenv('MT5_SERVER')

        # ログイン情報がある場合はログイン
        if mt5_login and mt5_password and mt5_server:
            try:
                login_int = int(mt5_login)
                authorized = mt5.login(
                    login=login_int,
                    password=mt5_password,
                    server=mt5_server
                )

                if not authorized:
                    error_code = mt5.last_error()
                    self.logger.error(
                        f"MT5 login failed: {error_code}. "
                        "Check your MT5 credentials."
                    )
                    mt5.shutdown()
                    return False

                self.logger.info(
                    f"MT5 initialized and logged in successfully: "
                    f"account={login_int}, server={mt5_server}"
                )
            except ValueError:
                self.logger.error(f"Invalid MT5_LOGIN value: {mt5_login}")
                mt5.shutdown()
                return False
        else:
            self.logger.warning(
                "MT5 credentials not found in environment variables. "
                "Continuing without login."
            )

        self._mt5_initialized = True
        return True

    def load_recent_ticks(self, days: int = 30) -> pd.DataFrame:
        """
        直近N日分のティックデータを取得

        Args:
            days: 取得する日数（デフォルト: 30日）

        Returns:
            pd.DataFrame: ティックデータ
                列: timestamp, bid, ask, volume

        Raises:
            ValueError: MT5の初期化に失敗した場合
            ValueError: データ取得に失敗した場合
        """
        # MT5の初期化確認（必要なら初期化）
        if not self._ensure_mt5_initialized():
            raise ValueError(
                "Failed to initialize MT5. "
                "Make sure MT5 is running and credentials are correct."
            )

        # 期間の計算
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)

        self.logger.info(
            f"Fetching {days} days of tick data for {self.symbol}: "
            f"{start_time.date()} to {end_time.date()}"
        )

        # ティックデータを取得
        ticks = mt5.copy_ticks_range(
            self.symbol,
            start_time,
            end_time,
            mt5.COPY_TICKS_ALL
        )

        if ticks is None or len(ticks) == 0:
            error_code = mt5.last_error()
            raise ValueError(
                f"Failed to fetch tick data for {self.symbol}. "
                f"MT5 error: {error_code}"
            )

        # DataFrameに変換
        df = pd.DataFrame(ticks)

        # タイムスタンプをdatetimeに変換
        df['time'] = pd.to_datetime(df['time'], unit='s')

        # 必要な列のみ抽出してリネーム
        df = df[['time', 'bid', 'ask', 'volume_real']].copy()
        df.columns = ['timestamp', 'bid', 'ask', 'volume']

        self.logger.info(
            f"Successfully fetched {len(df):,} ticks for {self.symbol}"
        )

        return df

    def load_ticks_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """
        指定期間のティックデータを取得

        Args:
            start_date: 開始日時
            end_date: 終了日時

        Returns:
            pd.DataFrame: ティックデータ
                列: timestamp, bid, ask, volume

        Raises:
            ValueError: MT5の初期化に失敗した場合
            ValueError: データ取得に失敗した場合
            ValueError: 日付範囲が不正な場合
        """
        # MT5の初期化確認（必要なら初期化）
        if not self._ensure_mt5_initialized():
            raise ValueError(
                "Failed to initialize MT5. "
                "Make sure MT5 is running and credentials are correct."
            )

        # 日付範囲の検証
        if start_date >= end_date:
            raise ValueError(
                f"start_date ({start_date}) must be before end_date ({end_date})"
            )

        self.logger.info(
            f"Fetching tick data for {self.symbol}: "
            f"{start_date.date()} to {end_date.date()}"
        )

        # ティックデータを取得
        ticks = mt5.copy_ticks_range(
            self.symbol,
            start_date,
            end_date,
            mt5.COPY_TICKS_ALL
        )

        if ticks is None or len(ticks) == 0:
            error_code = mt5.last_error()
            raise ValueError(
                f"Failed to fetch tick data for {self.symbol}. "
                f"MT5 error: {error_code}"
            )

        # DataFrameに変換
        df = pd.DataFrame(ticks)

        # タイムスタンプをdatetimeに変換
        df['time'] = pd.to_datetime(df['time'], unit='s')

        # 必要な列のみ抽出してリネーム
        df = df[['time', 'bid', 'ask', 'volume_real']].copy()
        df.columns = ['timestamp', 'bid', 'ask', 'volume']

        self.logger.info(
            f"Successfully fetched {len(df):,} ticks for {self.symbol}"
        )

        return df

    def get_latest_tick(self) -> Optional[dict]:
        """
        最新のティックデータを1件取得

        Returns:
            dict: 最新ティックデータ
                {
                    'timestamp': datetime,
                    'bid': float,
                    'ask': float,
                    'volume': int
                }
            None: 取得失敗時

        """
        # MT5の初期化確認（必要なら初期化）
        if not self._ensure_mt5_initialized():
            self.logger.error("Failed to initialize MT5")
            return None

        # 最新ティックを取得
        tick = mt5.symbol_info_tick(self.symbol)

        if tick is None:
            error_code = mt5.last_error()
            self.logger.error(f"Failed to fetch latest tick: {error_code}")
            return None

        return {
            'timestamp': datetime.fromtimestamp(tick.time),
            'bid': tick.bid,
            'ask': tick.ask,
            'volume': tick.volume
        }

    def validate_data(self, df: pd.DataFrame) -> bool:
        """
        取得したティックデータの検証

        Args:
            df: ティックデータのDataFrame

        Returns:
            bool: True=有効、False=無効
        """
        # データが空でないか
        if df is None or len(df) == 0:
            self.logger.error("Tick data is empty")
            return False

        # 必要な列が存在するか
        required_columns = ['timestamp', 'bid', 'ask', 'volume']
        if not all(col in df.columns for col in required_columns):
            self.logger.error(f"Missing required columns. Required: {required_columns}")
            return False

        # bid/askが正の値か
        if (df['bid'] <= 0).any() or (df['ask'] <= 0).any():
            self.logger.error("Invalid bid/ask values (must be positive)")
            return False

        # askがbidより大きいか（スプレッドが正）
        if (df['ask'] < df['bid']).any():
            self.logger.error("Invalid spread (ask < bid)")
            return False

        # タイムスタンプが昇順か
        if not df['timestamp'].is_monotonic_increasing:
            self.logger.warning("Timestamps are not in ascending order")
            # 昇順にソート
            df.sort_values('timestamp', inplace=True)

        self.logger.info("Tick data validation: PASS")
        return True


# モジュールのエクスポート
__all__ = ['MT5DataLoader']
