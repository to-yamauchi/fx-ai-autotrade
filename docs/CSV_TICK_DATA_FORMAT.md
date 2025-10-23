# CSV Tick Data Format for Backtesting

## Overview

This document describes the CSV format for tick data used in backtesting.
Use CSV files when historical data is not available from MT5.

---

## CSV File Format

### Required Columns

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `timestamp` | datetime | Tick timestamp | `2024-09-23 00:00:00` |
| `bid` | float | Bid price | `152.400` |
| `ask` | float | Ask price | `152.402` |
| `volume` | int | Volume (optional) | `100` |

### CSV Structure

```csv
timestamp,bid,ask,volume
2024-09-23 00:00:00,152.400,152.402,100
2024-09-23 00:00:01,152.401,152.403,150
2024-09-23 00:00:02,152.400,152.402,120
2024-09-23 00:00:03,152.399,152.401,80
...
```

### Important Notes

- **Header row required**: First row must contain column names
- **Timestamp format**: `YYYY-MM-DD HH:MM:SS` or ISO 8601 format
- **Sorted by time**: Data should be sorted chronologically
- **No duplicates**: Each timestamp should appear only once
- **Volume optional**: If not provided, defaults to 0

---

## File Organization

### Single File

Place all tick data in a single CSV file or ZIP file:

```
data/ticks/USDJPY_2024-09.csv
```

Or compressed:

```
data/tick_data/USDJPY/ticks_USDJPY-oj5k_2024-01.zip
```

**ZIP File Support**:
- ZIP files are automatically detected and extracted
- No need to manually unzip
- Supports single CSV inside ZIP
- File must contain `.csv` extension inside

### Multiple Files (Directory)

Place multiple CSV/ZIP files in a directory (will be combined):

```
data/tick_data/USDJPY/
├── ticks_USDJPY-oj5k_2024-01.zip
├── ticks_USDJPY-oj5k_2024-02.zip
├── ticks_USDJPY-oj5k_2024-03.zip
└── ...
```

Or mixed CSV and ZIP:

```
data/ticks/USDJPY/
├── 2024-09-01.csv
├── 2024-09-02.zip
├── 2024-09-03.csv
└── ...
```

---

## Usage Examples

### Example 1: Single ZIP File

```python
from src.backtest import BacktestEngine

engine = BacktestEngine(
    symbol='USDJPY',
    start_date='2024-01-01',
    end_date='2024-01-31',
    initial_balance=100000.0,
    ai_model='flash',
    csv_path='data/tick_data/USDJPY/ticks_USDJPY-oj5k_2024-01.zip'  # ZIP file
)

results = engine.run()
```

### Example 2: Single CSV File

```python
engine = BacktestEngine(
    symbol='USDJPY',
    start_date='2024-09-23',
    end_date='2024-09-30',
    initial_balance=100000.0,
    ai_model='flash',
    csv_path='data/ticks/USDJPY_2024-09.csv'  # CSV file
)

results = engine.run()
```

### Example 3: Directory with Multiple ZIP Files

```python
# Automatically loads all ZIP/CSV files in directory
engine = BacktestEngine(
    symbol='USDJPY',
    start_date='2024-01-01',
    end_date='2024-03-31',
    csv_path='data/tick_data/USDJPY/'  # Directory with multiple ZIPs
)

results = engine.run()
```

### Example 4: MT5 Data (Default)

```python
# Without csv_path, uses MT5 data
engine = BacktestEngine(
    symbol='USDJPY',
    start_date='2024-09-23',
    end_date='2024-09-30'
)

results = engine.run()
```

---

## Creating Sample CSV Data

### From MT5 Export

If you have MT5 data available, you can export it to CSV:

```python
from src.data_processing.mt5_data_loader import MT5DataLoader

loader = MT5DataLoader(symbol='USDJPY')
df = loader.load_recent_ticks(days=7)

# Save to CSV
df.to_csv('data/ticks/USDJPY_sample.csv', index=False)
```

### Manual Creation

Create a CSV file with the required format:

```csv
timestamp,bid,ask,volume
2024-09-23 00:00:00,152.400,152.402,100
2024-09-23 00:01:00,152.401,152.403,150
2024-09-23 00:02:00,152.400,152.402,120
```

### Using Pandas

```python
import pandas as pd
from datetime import datetime, timedelta

# Create sample data
data = []
start_time = datetime(2024, 9, 23, 0, 0, 0)

for i in range(1000):
    timestamp = start_time + timedelta(seconds=i)
    bid = 152.400 + (i % 10) * 0.001
    ask = bid + 0.002
    volume = 100 + (i % 50)

    data.append({
        'timestamp': timestamp,
        'bid': bid,
        'ask': ask,
        'volume': volume
    })

df = pd.DataFrame(data)
df.to_csv('data/ticks/USDJPY_sample.csv', index=False)
```

---

## Data Requirements

### Minimum Data Points

For meaningful backtests, ensure you have:

- **1-minute sampling**: ~1,440 ticks per day
- **1-second sampling**: ~86,400 ticks per day
- **Tick-by-tick**: 100,000+ ticks per day (for liquid pairs like USDJPY)

### Date Range

- **Short test**: 1 week (for quick validation)
- **Medium test**: 1 month (for realistic results)
- **Long test**: 3-12 months (for robust validation)

---

## File Location

Recommended directory structure:

```
fx-ai-autotrade/
├── data/
│   └── ticks/
│       ├── USDJPY/
│       │   ├── 2024-09-01.csv
│       │   ├── 2024-09-02.csv
│       │   └── ...
│       ├── EURUSD/
│       │   └── ...
│       └── USDJPY_2024-09.csv  # Or single file
├── src/
│   └── backtest/
│       ├── csv_tick_loader.py
│       └── backtest_engine.py
└── test_backtest.py
```

---

## Troubleshooting

### Error: "Missing required columns"

**Cause**: CSV file doesn't have `timestamp`, `bid`, `ask` columns

**Solution**: Ensure CSV has proper header row:
```csv
timestamp,bid,ask,volume
```

### Error: "No tick data loaded"

**Cause**: CSV file is empty or path is incorrect

**Solution**: Check file path and ensure file contains data

### Error: "Failed to load CSV file"

**Cause**: Invalid CSV format or encoding issue

**Solution**:
- Use UTF-8 encoding
- Ensure valid datetime format
- Check for special characters

---

## Performance Tips

1. **Use compressed files** for large datasets (`.csv.gz` supported)
2. **Split large files** into monthly chunks for faster loading
3. **Filter date range** in CSV loader to reduce memory usage
4. **Remove unnecessary columns** to reduce file size

---

## Next Steps

After preparing CSV data:

1. Place CSV file in `data/ticks/` directory
2. Update `test_backtest.py` with `csv_path` parameter
3. Run backtest: `python test_backtest.py`
4. Review results in `backtest_results` table

---

**Created**: 2025-10-23
**Updated**: 2025-10-23
