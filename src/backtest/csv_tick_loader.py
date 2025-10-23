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
from typing import Optional, List
import logging
import os
import zipfile
import re


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
            # Directory - load CSV files (filter by date range if specified)
            df = self._load_csv_directory(self.csv_path, start_date, end_date)
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

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize CSV column names to standard format

        Supports common variations:
        - time, datetime, date → timestamp
        - Bid, BID → bid
        - Ask, ASK → ask
        - Volume, VOLUME, volume_real → volume

        Special handling for MT5 CSV format:
        - <DATE> + <TIME> → timestamp
        - <BID> → bid
        - <ASK> → ask
        - <VOLUME> → volume

        Args:
            df: Input dataframe

        Returns:
            pd.DataFrame: Dataframe with normalized column names
        """
        # Handle MT5 CSV format with <DATE> and <TIME>
        if '<DATE>' in df.columns and '<TIME>' in df.columns:
            self.logger.info("Detected MT5 CSV format with <DATE> and <TIME>")

            # Combine <DATE> and <TIME> into timestamp
            df['timestamp'] = pd.to_datetime(
                df['<DATE>'].astype(str) + ' ' + df['<TIME>'].astype(str),
                format='%Y.%m.%d %H:%M:%S.%f',
                errors='coerce'
            )

            # Rename MT5 columns
            column_map = {}
            if '<BID>' in df.columns:
                column_map['<BID>'] = 'bid'
            if '<ASK>' in df.columns:
                column_map['<ASK>'] = 'ask'
            if '<VOLUME>' in df.columns:
                column_map['<VOLUME>'] = 'volume'

            if column_map:
                df = df.rename(columns=column_map)
                self.logger.info(f"Normalized MT5 columns: {column_map}")

            return df

        # Standard column normalization (case-insensitive)
        column_map = {}

        for col in df.columns:
            col_lower = col.lower().strip()

            # Timestamp variations
            if col_lower in ['time', 'datetime', 'date']:
                column_map[col] = 'timestamp'
            # Bid variations
            elif col_lower == 'bid':
                column_map[col] = 'bid'
            # Ask variations
            elif col_lower == 'ask':
                column_map[col] = 'ask'
            # Volume variations
            elif col_lower in ['volume', 'volume_real', 'vol']:
                column_map[col] = 'volume'

        # Apply renaming
        if column_map:
            df = df.rename(columns=column_map)
            self.logger.info(f"Normalized columns: {column_map}")

        return df

    def _load_csv_file(self, filepath: str) -> pd.DataFrame:
        """
        Load single CSV file (supports .csv and .zip files)

        Args:
            filepath: Path to CSV or ZIP file

        Returns:
            pd.DataFrame: Tick data
        """
        self.logger.info(f"Reading file: {filepath}")

        try:
            # Check if file is ZIP
            if filepath.lower().endswith('.zip'):
                df = self._load_zip_file(filepath)
            else:
                # Read CSV directly (try tab-separated first, then comma-separated)
                try:
                    df = pd.read_csv(filepath, sep='\t')
                    # Check if only one column - might be comma-separated
                    if len(df.columns) == 1:
                        df = pd.read_csv(filepath, sep=',')
                except Exception:
                    df = pd.read_csv(filepath, sep=',')

            # Normalize column names (auto-rename common variations)
            df = self._normalize_columns(df)

            # Validate columns
            required_cols = ['timestamp', 'bid', 'ask']
            missing_cols = [col for col in required_cols if col not in df.columns]

            if missing_cols:
                available_cols = list(df.columns)
                raise ValueError(
                    f"Missing required columns: {missing_cols}. "
                    f"Available columns: {available_cols}. "
                    f"CSV must have: timestamp (or time/datetime), bid, ask (volume is optional)"
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
            self.logger.error(f"Failed to load file: {e}")
            raise

    def _load_zip_file(self, zip_path: str) -> pd.DataFrame:
        """
        Load CSV from ZIP file

        Args:
            zip_path: Path to ZIP file

        Returns:
            pd.DataFrame: Tick data
        """
        self.logger.info(f"Extracting CSV from ZIP: {zip_path}")

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Get list of CSV files in ZIP
            csv_files = [f for f in zip_ref.namelist() if f.endswith('.csv')]

            if not csv_files:
                raise ValueError(f"No CSV files found in ZIP: {zip_path}")

            if len(csv_files) > 1:
                self.logger.warning(
                    f"Multiple CSV files found in ZIP. Using first one: {csv_files[0]}"
                )

            csv_file = csv_files[0]
            self.logger.info(f"Reading CSV from ZIP: {csv_file}")

            # Read CSV from ZIP (try tab-separated first, then comma-separated)
            with zip_ref.open(csv_file) as f:
                try:
                    df = pd.read_csv(f, sep='\t')
                    # Check if only one column - might be comma-separated
                    if len(df.columns) == 1:
                        f.seek(0)  # Reset file pointer
                        df = pd.read_csv(f, sep=',')
                except Exception:
                    f.seek(0)  # Reset file pointer
                    df = pd.read_csv(f, sep=',')

            return df

    def _filter_files_by_date(
        self,
        files: List[str],
        start_date: Optional[str],
        end_date: Optional[str]
    ) -> List[str]:
        """
        Filter files by extracting year-month from filename

        Supports filenames like:
        - ticks_USDJPY-oj5k_2024-01.zip
        - USDJPY_2024-09.csv
        - data_2024-12.zip

        Args:
            files: List of filenames
            start_date: Start date (YYYY-MM-DD format)
            end_date: End date (YYYY-MM-DD format)

        Returns:
            List[str]: Filtered filenames
        """
        if not start_date and not end_date:
            return files

        # Parse start and end dates
        start_dt = pd.to_datetime(start_date) if start_date else None
        end_dt = pd.to_datetime(end_date) if end_date else None

        # Extract year-month range needed
        if start_dt and end_dt:
            # Generate list of YYYY-MM strings in range
            date_range = pd.date_range(
                start=start_dt.replace(day=1),
                end=end_dt.replace(day=1),
                freq='MS'  # Month start
            )
            needed_months = set(dt.strftime('%Y-%m') for dt in date_range)

            self.logger.info(
                f"Date range {start_date} to {end_date} requires months: "
                f"{sorted(needed_months)}"
            )
        else:
            needed_months = None

        # Filter files by year-month pattern
        filtered_files = []
        pattern = re.compile(r'(\d{4}-\d{2})')  # Match YYYY-MM

        for filename in files:
            match = pattern.search(filename)
            if match:
                file_year_month = match.group(1)

                # Check if this file's month is in the needed range
                if needed_months is None or file_year_month in needed_months:
                    filtered_files.append(filename)
                    self.logger.debug(
                        f"Including file: {filename} (month: {file_year_month})"
                    )
                else:
                    self.logger.debug(
                        f"Skipping file: {filename} (month: {file_year_month} not in range)"
                    )
            else:
                # No date pattern found in filename, include it anyway
                filtered_files.append(filename)
                self.logger.debug(
                    f"Including file: {filename} (no date pattern found)"
                )

        return filtered_files

    def _load_csv_directory(
        self,
        dirpath: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Load CSV/ZIP files from directory, optionally filtered by date range

        Args:
            dirpath: Path to directory
            start_date: Start date (YYYY-MM-DD format), optional
            end_date: End date (YYYY-MM-DD format), optional

        Returns:
            pd.DataFrame: Combined tick data
        """
        self.logger.info(f"Loading CSV/ZIP files from: {dirpath}")

        # Get both CSV and ZIP files
        all_files = [
            f for f in os.listdir(dirpath)
            if f.endswith('.csv') or f.endswith('.zip')
        ]

        if not all_files:
            raise FileNotFoundError(
                f"No CSV or ZIP files found in: {dirpath}"
            )

        # Filter files by date range if specified
        data_files = self._filter_files_by_date(all_files, start_date, end_date)

        if not data_files:
            self.logger.warning(
                f"No files found matching date range {start_date} to {end_date}. "
                f"Loading all {len(all_files)} files."
            )
            data_files = all_files

        self.logger.info(
            f"Found {len(all_files)} total files, "
            f"loading {len(data_files)} files for date range"
        )

        # Load filtered files
        dfs = []
        for data_file in sorted(data_files):
            filepath = os.path.join(dirpath, data_file)
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
