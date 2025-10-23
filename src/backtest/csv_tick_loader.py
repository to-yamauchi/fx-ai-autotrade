"""
========================================
CSV Tick Data Loader
========================================

File: csv_tick_loader.py
Path: src/backtest/csv_tick_loader.py

Description:
Loads tick data from CSV files for backtesting.
Use this when historical data is not available from MT5.

CSV Format:
timestamp,bid,ask,volume
2024-09-23 00:00:00,152.400,152.402,100
2024-09-23 00:00:01,152.401,152.403,150
...

Usage:
from src.backtest.csv_tick_loader import CSVTickLoader

loader = CSVTickLoader('data/ticks/USDJPY_2024-09.csv')
df = loader.load_ticks(
    start_date='2024-09-23',
    end_date='2024-09-30'
)

Created: 2025-10-23
"""

import pandas as pd
from datetime import datetime
from typing import Optional
import logging
import os


class CSVTickLoader:
    """
    CSV Tick Data Loader

    Loads tick data from CSV files for backtesting.
    """

    def __init__(self, csv_path: str, symbol: str = 'USDJPY'):
        """
        Initialize CSV Tick Loader

        Args:
            csv_path: Path to CSV file or directory containing CSV files
            symbol: Currency pair symbol
        """
        self.csv_path = csv_path
        self.symbol = symbol
        self.logger = logging.getLogger(__name__)

        self.logger.info(
            f"CSVTickLoader initialized: path={csv_path}, symbol={symbol}"
        )

    def load_ticks(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Load tick data from CSV file(s)

        Args:
            start_date: Start date (YYYY-MM-DD format), optional
            end_date: End date (YYYY-MM-DD format), optional

        Returns:
            pd.DataFrame: Tick data with columns: timestamp, bid, ask, volume

        Raises:
            FileNotFoundError: If CSV file not found
            ValueError: If CSV format is invalid
        """
        self.logger.info(f"Loading tick data from CSV: {self.csv_path}")

        # Check if path is file or directory
        if os.path.isfile(self.csv_path):
            # Single file
            df = self._load_csv_file(self.csv_path)
        elif os.path.isdir(self.csv_path):
            # Directory - load all CSV files
            df = self._load_csv_directory(self.csv_path)
        else:
            raise FileNotFoundError(
                f"CSV path not found: {self.csv_path}"
            )

        if df.empty:
            raise ValueError(
                f"No tick data loaded from: {self.csv_path}"
            )

        # Filter by date range if specified
        if start_date or end_date:
            df = self._filter_by_date(df, start_date, end_date)

        self.logger.info(
            f"Loaded {len(df):,} ticks from CSV"
        )

        return df

    def _load_csv_file(self, filepath: str) -> pd.DataFrame:
        """
        Load single CSV file

        Args:
            filepath: Path to CSV file

        Returns:
            pd.DataFrame: Tick data
        """
        self.logger.info(f"Reading CSV file: {filepath}")

        try:
            # Read CSV
            df = pd.read_csv(filepath)

            # Validate columns
            required_cols = ['timestamp', 'bid', 'ask']
            missing_cols = [col for col in required_cols if col not in df.columns]

            if missing_cols:
                raise ValueError(
                    f"Missing required columns: {missing_cols}. "
                    f"CSV must have: timestamp, bid, ask (volume is optional)"
                )

            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            # Add volume column if not present
            if 'volume' not in df.columns:
                df['volume'] = 0

            # Select and order columns
            df = df[['timestamp', 'bid', 'ask', 'volume']].copy()

            # Sort by timestamp
            df = df.sort_values('timestamp').reset_index(drop=True)

            self.logger.info(f"Loaded {len(df):,} rows from {filepath}")

            return df

        except Exception as e:
            self.logger.error(f"Failed to load CSV file: {e}")
            raise

    def _load_csv_directory(self, dirpath: str) -> pd.DataFrame:
        """
        Load all CSV files from directory

        Args:
            dirpath: Path to directory

        Returns:
            pd.DataFrame: Combined tick data
        """
        self.logger.info(f"Loading all CSV files from: {dirpath}")

        csv_files = [
            f for f in os.listdir(dirpath)
            if f.endswith('.csv')
        ]

        if not csv_files:
            raise FileNotFoundError(
                f"No CSV files found in: {dirpath}"
            )

        self.logger.info(f"Found {len(csv_files)} CSV files")

        # Load all files
        dfs = []
        for csv_file in sorted(csv_files):
            filepath = os.path.join(dirpath, csv_file)
            df = self._load_csv_file(filepath)
            dfs.append(df)

        # Combine all dataframes
        combined_df = pd.concat(dfs, ignore_index=True)

        # Sort by timestamp
        combined_df = combined_df.sort_values('timestamp').reset_index(drop=True)

        # Remove duplicates
        combined_df = combined_df.drop_duplicates(subset='timestamp')

        self.logger.info(
            f"Combined {len(dfs)} files into {len(combined_df):,} ticks"
        )

        return combined_df

    def _filter_by_date(
        self,
        df: pd.DataFrame,
        start_date: Optional[str],
        end_date: Optional[str]
    ) -> pd.DataFrame:
        """
        Filter dataframe by date range

        Args:
            df: Tick dataframe
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            pd.DataFrame: Filtered dataframe
        """
        filtered_df = df.copy()

        if start_date:
            start_dt = pd.to_datetime(start_date)
            filtered_df = filtered_df[filtered_df['timestamp'] >= start_dt]
            self.logger.info(f"Filtered from {start_date}")

        if end_date:
            end_dt = pd.to_datetime(end_date) + pd.Timedelta(days=1)  # Include end date
            filtered_df = filtered_df[filtered_df['timestamp'] < end_dt]
            self.logger.info(f"Filtered to {end_date}")

        self.logger.info(
            f"Date filter: {len(df):,} -> {len(filtered_df):,} ticks"
        )

        return filtered_df

    def get_date_range(self) -> tuple:
        """
        Get available date range in CSV data

        Returns:
            tuple: (start_date, end_date) as datetime objects
        """
        df = self.load_ticks()

        if df.empty:
            return None, None

        return df['timestamp'].min(), df['timestamp'].max()


# Module exports
__all__ = ['CSVTickLoader']
