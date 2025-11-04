import sys
from pathlib import Path
import pandas as pd
import numpy as np
# ensure project root is on sys.path
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.preprocessing.data_preprocessor import _safe_read_table, load_all_data

base = Path('tmp_debug_preprocess')
if base.exists():
    import shutil
    shutil.rmtree(base)
base.mkdir()
prices = base / 'prices'
fund = base / 'fundamentals'
macro = base / 'macro'
prices.mkdir()
fund.mkdir()
macro.mkdir()

dates = pd.to_datetime(pd.date_range(start='2022-01-01', end='2023-01-10'))
price_data_001 = pd.DataFrame({
    'Open': np.random.uniform(100, 110, size=len(dates)),
    'High': np.random.uniform(110, 120, size=len(dates)),
    'Low': np.random.uniform(90, 100, size=len(dates)),
    'Close': np.random.uniform(100, 115, size=len(dates)),
    'Volume': np.random.randint(1000, 5000, size=len(dates))
}, index=dates)
price_data_001.index.name = 'date'
price_data_001.to_csv(prices / '001.parquet', index=True)

price_data_002 = (price_data_001 * 1.5)
price_data_002.to_csv(prices / '002.parquet', index=True)

fundamentals_data = pd.DataFrame({'code': ['001', '002'], 'BPS': [1000, 1500]})
fundamentals_data.to_csv(fund / 'fundamentals_20220601.parquet', index=False)
fundamentals_data_2 = pd.DataFrame({'code': ['001', '002'], 'BPS': [1015, 1520]})
fundamentals_data_2.to_csv(fund / 'fundamentals_20221201.parquet', index=False)

macro_data = pd.DataFrame({'KOSPI': np.linspace(2000, 2500, len(dates))}, index=dates)
macro_data.index.name = 'date'
macro_data.to_csv(macro / f"macro_{dates.min().strftime('%Y%m%d')}_{dates.max().strftime('%Y%m%d')}.parquet", index=True)

print('Files created:')
for p in sorted(base.rglob('*')):
    print(p)

# inspect one file via safe read
print('\n_read_table for prices/001.parquet:')
df = _safe_read_table(prices / '001.parquet')
print(df.head())
print(df.index.name, df.columns.tolist())

print('\n_read_table for fundamentals_20220601.parquet:')
df2 = _safe_read_table(fund / 'fundamentals_20220601.parquet')
print(df2.head())
print(df2.index.name, df2.columns.tolist())

print('\nCalling load_all_data...')
res = load_all_data(str(base), ['001','002'], '2022-10-01', '2022-12-31')
print('Result type:', type(res))
print(res)

print('\n-- manual inspection of per-stock files --')
for stock_code in ['001','002']:
    path = base / 'prices' / f"{stock_code}.parquet"
    print('\nStock:', stock_code)
    dfp = _safe_read_table(path)
    print('read shape:', dfp.shape)
    # try to normalize date column
    if 'date' in dfp.columns:
        try:
            print('date min/max:', dfp['date'].min(), dfp['date'].max())
        except Exception as e:
            print('date col type/samp:', dfp['date'].dtype, dfp['date'].head())
    else:
        print('no date column; columns:', dfp.columns.tolist())

print('\n-- replicate load_all_data logic for filtering --')
start_date = pd.to_datetime('2022-10-01')
end_date = pd.to_datetime('2022-12-31')
for stock_code in ['001','002']:
    print('\nReplicate stock', stock_code)
    price_path = base / 'prices' / f"{stock_code}.parquet"
    pdf = _safe_read_table(price_path)
    pdf.reset_index(inplace=True)
    pdf.rename(columns={'Date': 'date', 'index': 'date'}, inplace=True)
    # handle duplicate date columns
    if pdf.columns.duplicated().any():
        date_cols_idx = [i for i, c in enumerate(pdf.columns) if c == 'date']
        if date_cols_idx:
            pdf['date'] = pdf.iloc[:, date_cols_idx].bfill(axis=1).iloc[:, 0]
            pdf = pdf.loc[:, ~pdf.columns.duplicated()]
    pdf['date'] = pd.to_datetime(pdf['date'])
    print('after to_datetime, dtype:', pdf['date'].dtype)
    print('after to_datetime, min/max:', pdf['date'].min(), pdf['date'].max())
    filtered = pdf[(pdf['date'] >= start_date) & (pdf['date'] <= end_date)]
    print('pdf rows total:', len(pdf), 'filtered rows:', len(filtered))
