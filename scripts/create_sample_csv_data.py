"""
========================================
Sample CSV Tick Data Generator
========================================

Creates sample CSV tick data for backtesting when MT5 data is not available.

Usage:
    python scripts/create_sample_csv_data.py

Output:
    data/ticks/USDJPY_sample.csv

Created: 2025-10-23
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os


def create_sample_tick_data(
    symbol: str = 'USDJPY',
    start_date: str = '2024-09-23',
    end_date: str = '2024-09-30',
    base_price: float = 152.400,
    spread_pips: float = 0.2,
    interval_seconds: int = 1
):
    """
    Create sample tick data with realistic price movements

    Args:
        symbol: Currency pair
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        base_price: Base price
        spread_pips: Spread in pips
        interval_seconds: Interval between ticks in seconds

    Returns:
        pd.DataFrame: Tick data
    """
    print(f"Generating sample tick data for {symbol}")
    print(f"Period: {start_date} to {end_date}")

    # Parse dates
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')

    # Calculate number of ticks
    total_seconds = int((end_dt - start_dt).total_seconds())
    num_ticks = total_seconds // interval_seconds

    print(f"Generating {num_ticks:,} ticks...")

    # Generate timestamps
    timestamps = [
        start_dt + timedelta(seconds=i * interval_seconds)
        for i in range(num_ticks)
    ]

    # Generate realistic price movements using random walk
    np.random.seed(42)  # For reproducibility

    # Random walk parameters
    drift = 0.0001  # Small upward drift
    volatility = 0.001  # Price volatility

    # Generate price changes
    price_changes = np.random.normal(drift, volatility, num_ticks)

    # Calculate cumulative prices
    prices = base_price + np.cumsum(price_changes)

    # Add some trends and reversals
    trend_period = num_ticks // 10
    for i in range(0, num_ticks, trend_period):
        # Add occasional strong trends
        if np.random.random() > 0.7:
            trend_strength = np.random.choice([-0.05, 0.05])
            trend_length = min(trend_period, num_ticks - i)
            prices[i:i+trend_length] += np.linspace(0, trend_strength, trend_length)

    # Calculate bid/ask from mid prices
    spread_price = spread_pips / 100  # Convert pips to price
    bids = prices - spread_price / 2
    asks = prices + spread_price / 2

    # Generate volumes (random between 50-200)
    volumes = np.random.randint(50, 200, num_ticks)

    # Create DataFrame
    df = pd.DataFrame({
        'timestamp': timestamps,
        'bid': bids,
        'ask': asks,
        'volume': volumes
    })

    print(f"Generated {len(df):,} ticks")
    print(f"Price range: {df['bid'].min():.3f} - {df['bid'].max():.3f}")

    return df


def main():
    """Main function"""
    print("=" * 80)
    print("Sample CSV Tick Data Generator")
    print("=" * 80)
    print()

    # Create data directory if not exists
    data_dir = 'data/ticks'
    os.makedirs(data_dir, exist_ok=True)
    print(f"Data directory: {data_dir}")
    print()

    # Generate sample data
    df = create_sample_tick_data(
        symbol='USDJPY',
        start_date='2024-09-23',
        end_date='2024-09-30',
        base_price=152.400,
        spread_pips=0.2,
        interval_seconds=1  # 1 tick per second
    )

    # Save to CSV
    output_file = os.path.join(data_dir, 'USDJPY_sample.csv')
    df.to_csv(output_file, index=False)

    print()
    print(f"✅ Sample data saved to: {output_file}")
    print()

    # Display sample
    print("Sample data (first 10 rows):")
    print(df.head(10).to_string(index=False))
    print()

    print("Sample data (last 10 rows):")
    print(df.tail(10).to_string(index=False))
    print()

    # Statistics
    print("=" * 80)
    print("Statistics")
    print("=" * 80)
    print(f"Total ticks: {len(df):,}")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"Price range (bid): {df['bid'].min():.3f} to {df['bid'].max():.3f}")
    print(f"Price range (ask): {df['ask'].min():.3f} to {df['ask'].max():.3f}")
    print(f"Average spread: {(df['ask'] - df['bid']).mean():.5f}")
    print()

    print("=" * 80)
    print("Next steps:")
    print("=" * 80)
    print("1. Review the generated CSV file")
    print("2. Update test_backtest.py to use CSV:")
    print("   csv_path='data/ticks/USDJPY_sample.csv'")
    print("3. Run backtest: python test_backtest.py")
    print()


if __name__ == '__main__':
    main()
