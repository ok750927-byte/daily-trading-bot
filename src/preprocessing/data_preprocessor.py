import pandas as pd
import numpy as np
import os
from typing import List, Optional


def _safe_group_apply(grouped, func):
    """Apply a function to a GroupBy safely across pandas versions.

    Prefer calling include_groups=False when available to silence
    the FutureWarning; otherwise fall back to the plain apply.
    """
    # Prefer excluding grouping columns (include_groups=False) when supported
    # to follow future pandas behavior and silence FutureWarning. If the
    # pandas version does not support include_groups, fall back gracefully.
    try:
        return grouped.apply(func, include_groups=False)
    except TypeError:
        try:
            return grouped.apply(func, include_groups=True)
        except TypeError:
            return grouped.apply(func)


def _safe_read_table(path):
    """Try to read a parquet file, but fall back to CSV if parquet engine is unavailable."""
    try:
        return pd.read_parquet(path)
    except Exception:
        try:
            # When falling back to CSV, read normally then normalize possible index column
            df = pd.read_csv(path)
            # If pandas saved the index as 'Unnamed: 0', restore it as the index
            if 'Unnamed: 0' in df.columns and 'date' not in df.columns and 'Date' not in df.columns:
                df = df.set_index('Unnamed: 0')
            return df
        except Exception:
            raise

def load_all_data(data_path: str, 
                  target_stocks: List[str], 
                  start_date: str, 
                  end_date: str) -> Optional[pd.DataFrame]:
    """
    지정된 경로에서 모든 데이터를 로드하고 병합합니다.
    병합 로직을 수정하여 안정성을 높입니다.
    """
    try:
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)

        # 1. 거시경제 데이터 로드
        macro_df = pd.DataFrame()
        macro_path = os.path.join(data_path, 'macro')
        if os.path.exists(macro_path):
            macro_files = [f for f in os.listdir(macro_path) if f.endswith('.parquet')]
            if macro_files:
                macro_df = _safe_read_table(os.path.join(macro_path, macro_files[-1]))
                if 'date' not in macro_df.columns:
                    macro_df.reset_index(inplace=True)
                macro_df.rename(columns={'Date': 'date', 'index': 'date'}, inplace=True)
                # If rename produced duplicate 'date' columns, coalesce them
                if macro_df.columns.duplicated().any():
                    # combine duplicate 'date' columns by taking the first non-null value
                    date_cols_idx = [i for i, c in enumerate(macro_df.columns) if c == 'date']
                    if date_cols_idx:
                        macro_df['date'] = macro_df.iloc[:, date_cols_idx].bfill(axis=1).iloc[:, 0]
                        # drop duplicated columns, keep first occurrence
                        macro_df = macro_df.loc[:, ~macro_df.columns.duplicated()]
                macro_df['date'] = pd.to_datetime(macro_df['date'])
                macro_df = macro_df[(macro_df['date'] >= start_date) & (macro_df['date'] <= end_date)]
        if macro_df.empty:
            print("[WARNING] 거시경제 데이터를 찾을 수 없거나 기간 내 데이터가 없습니다.")

        # 2. 재무 데이터 로드
        fundamentals_df = pd.DataFrame()
        fundamentals_path = os.path.join(data_path, 'fundamentals')
        if os.path.exists(fundamentals_path):
            fundamentals_files = [f for f in os.listdir(fundamentals_path) if f.endswith('.parquet')]
            if fundamentals_files:
                    # Load all fundamentals files and combine them so historical snapshots are preserved
                    fund_list = []
                    import re
                    for fname in fundamentals_files:
                        fpath = os.path.join(fundamentals_path, fname)
                        try:
                            fdf = _safe_read_table(fpath)
                        except Exception:
                            continue
                        fdf.rename(columns={'Date': 'date', 'index': 'date', '티커': 'code'}, inplace=True, errors='ignore')
                        if 'date' in fdf.columns:
                            fdf['date'] = pd.to_datetime(fdf['date'])
                        else:
                            m = re.search(r"(\d{8})", fname)
                            if m:
                                inferred_date = pd.to_datetime(m.group(1), format='%Y%m%d')
                                fdf['date'] = inferred_date
                            else:
                                fdf['date'] = pd.to_datetime('1970-01-01')
                        fund_list.append(fdf)

                    if fund_list:
                        fundamentals_df = pd.concat(fund_list, ignore_index=True)
                        # prefer the last record per (code, date) if duplicates exist
                        if 'code' in fundamentals_df.columns:
                            fundamentals_df.drop_duplicates(subset=['date', 'code'], keep='last', inplace=True)
                        # ensure earliest snapshot applies to all earlier dates by setting
                        # the earliest record per code to a very early date so merge_asof
                        # will match it for price rows before the first snapshot.
                        try:
                            fundamentals_df['date'] = pd.to_datetime(fundamentals_df['date'])
                            idxs = fundamentals_df.groupby('code')['date'].idxmin()
                            for i in idxs.dropna().astype(int):
                                fundamentals_df.at[i, 'date'] = pd.to_datetime('1970-01-01')
                        except Exception:
                            pass
                    else:
                        fundamentals_df = pd.DataFrame()
        if fundamentals_df.empty:
            print("[WARNING] 재무 데이터를 찾을 수 없습니다.")
        
        # 3. 개별 종목 데이터와 재무 데이터 병합
        all_stocks_df = []
        for stock_code in target_stocks:
            price_path = os.path.join(data_path, 'prices', f"{stock_code}.parquet")
            if not os.path.exists(price_path):
                print(f"[WARNING] {stock_code}의 시세 데이터를 찾을 수 없습니다.")
                continue
            
            price_df = _safe_read_table(price_path)
            if 'date' not in price_df.columns:
                price_df.reset_index(inplace=True)
            price_df.rename(columns={'Date': 'date', 'index': 'date'}, inplace=True)
            # If duplicate 'date' columns exist after rename, coalesce them
            if price_df.columns.duplicated().any():
                date_cols_idx = [i for i, c in enumerate(price_df.columns) if c == 'date']
                if date_cols_idx:
                    price_df['date'] = price_df.iloc[:, date_cols_idx].bfill(axis=1).iloc[:, 0]
                    price_df = price_df.loc[:, ~price_df.columns.duplicated()]
            price_df['date'] = pd.to_datetime(price_df['date'])
            price_df = price_df[(price_df['date'] >= start_date) & (price_df['date'] <= end_date)]
            price_df['code'] = stock_code
            
            merged_df = price_df
            # 재무 데이터 병합
            if not fundamentals_df.empty:
                # normalize code formats so numeric CSVs ('1','2') match zero-padded stock codes like '001'
                fund_copy = fundamentals_df.copy()
                try:
                    fund_copy['code'] = fund_copy['code'].astype(str)
                except Exception:
                    fund_copy['code'] = fund_copy['code'].astype(str)

                fund_copy['code'] = fund_copy['code'].str.zfill(len(stock_code))
                if stock_code in fund_copy['code'].unique():
                    stock_fundamentals = fund_copy[fund_copy['code'] == stock_code].sort_values('date')
                    merged_df = pd.merge_asof(merged_df.sort_values('date'),
                                              stock_fundamentals,
                                              on='date',
                                              by='code',
                                              direction='backward')
            all_stocks_df.append(merged_df)

        if not all_stocks_df:
            print("[ERROR] 처리할 주식 데이터가 없습니다.")
            return None

        # 4. 모든 주식 데이터 취합 후 거시경제 데이터 병합
        final_df = pd.concat(all_stocks_df).sort_values(['code', 'date']).reset_index(drop=True)
        
        if not macro_df.empty:
            final_df = pd.merge(final_df, macro_df, on='date', how='left')

        # Robust fallback: if fundamentals existed but some fundamental columns are still NaN
        # after the per-stock merge (possible due to code-format mismatches), perform a
        # global merge_asof to backfill missing fundamental values. This handles cases
        # where per-stock zfill lengths differed or date types mismatched during the
        # earlier per-stock merge.
        try:
            if not fundamentals_df.empty:
                fund_copy = fundamentals_df.copy()
                # normalize to strings
                fund_copy['code'] = fund_copy['code'].astype(str)
                final_df['code'] = final_df['code'].astype(str)

                # pad codes to a common width to avoid mismatches
                pad = max(fund_copy['code'].str.len().max(), final_df['code'].str.len().max())
                if pd.notna(pad) and pad > 0:
                    fund_copy['code'] = fund_copy['code'].str.zfill(int(pad))
                    final_df['code'] = final_df['code'].str.zfill(int(pad))

                # ensure date columns are datetime
                fund_copy['date'] = pd.to_datetime(fund_copy['date'])
                final_df['date'] = pd.to_datetime(final_df['date'])

                # perform an asof merge to get the latest fundamentals for each price row
                fund_copy = fund_copy.sort_values(['code', 'date'])
                left = final_df.sort_values(['code', 'date'])
                merged_back = pd.merge_asof(left, fund_copy, on='date', by='code', direction='backward', suffixes=(None, '_fund'))

                # For each column from fundamentals, fill missing values in final_df with merged_back values
                for col in fund_copy.columns:
                    if col in ('date', 'code'):
                        continue
                    if col not in final_df.columns:
                        final_df[col] = merged_back[col]
                    else:
                        final_df[col] = final_df[col].fillna(merged_back[col])
        except Exception:
            # keep the original final_df if anything goes wrong here; don't fail the whole pipeline
            pass

        return final_df

    except Exception as e:
        print(f"[ERROR] 데이터 로딩 및 병합 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None

def handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    결측치를 처리합니다. ffill 후 bfill을 사용하여 최대한 데이터를 보존합니다.
    """
    # 종목별로 그룹화하여 ffill, bfill 실행
    # ffill(): 이전 값으로 채우기, bfill(): 다음 값으로 채우기
    grouped = df.groupby('code', group_keys=False)
    df_filled = _safe_group_apply(grouped, lambda x: x.ffill().bfill())

    # 거래량(Volume)의 NaN은 0으로 채움 (ffill/bfill 후에도 남는 경우 대비)
    if 'Volume' in df_filled.columns:
        df_filled['Volume'] = df_filled['Volume'].fillna(0)
    
    return df_filled

def create_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    기술적 분석 지표를 생성합니다.
    """
    df_featured = df.copy()
    
    # 종목별로 그룹화하여 피처 생성
    def calculate_features(group):
        # 종가 이동평균 (min_periods을 설정해 초기 NaN 개수가 테스트와 일치하도록)
        group['ma5'] = group['Close'].rolling(window=5, min_periods=5).mean()
        group['ma20'] = group['Close'].rolling(window=20, min_periods=20).mean()
        group['ma60'] = group['Close'].rolling(window=60, min_periods=60).mean()
        group['ma120'] = group['Close'].rolling(window=120, min_periods=120).mean()

        # 거래량 이동평균
        group['volume_ma5'] = group['Volume'].rolling(window=5, min_periods=5).mean()
        group['volume_ma20'] = group['Volume'].rolling(window=20, min_periods=20).mean()

        # 등락률
        group['daily_return'] = group['Close'].pct_change()

        # RSI (Relative Strength Index)
        delta = group['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        group['rsi'] = 100 - (100 / (1 + rs))

        # MACD (Moving Average Convergence Divergence)
        exp12 = group['Close'].ewm(span=12, adjust=False).mean()
        exp26 = group['Close'].ewm(span=26, adjust=False).mean()
        macd = exp12 - exp26
        group['macd_signal'] = macd.ewm(span=9, adjust=False).mean()

        # Bollinger Bands (볼린저 밴드)
        ma20 = group['Close'].rolling(window=20, min_periods=20).mean()
        std20 = group['Close'].rolling(window=20, min_periods=20).std()
        group['bollinger_upper'] = ma20 + (std20 * 2)
        group['bollinger_lower'] = ma20 - (std20 * 2)

        return group

    grouped = df_featured.groupby('code', group_keys=False)
    df_featured = _safe_group_apply(grouped, calculate_features)
    
    return df_featured

def preprocess_data(data_path: str, 
                    target_stocks: List[str], 
                    start_date: str, 
                    end_date: str) -> Optional[pd.DataFrame]:
    """
    전체 데이터 전처리 파이프라인을 실행합니다.
    수정: parquet 파일에서 직접 데이터를 필터링합니다.
    """
    print("=== 데이터 전처리 시작 ===")
    
    # 1. 단일 Parquet 파일 또는 데이터 디렉토리에서 데이터 로드
    print(f"[1/4] 데이터 로딩 중: {data_path}")
    try:
        if os.path.isdir(data_path):
            # tests provide a data directory (prices/, fundamentals/, macro/)
            df = load_all_data(data_path, target_stocks, start_date, end_date)
            if df is None:
                print(f"[ERROR] 디렉터리에서 데이터 로드 실패: {data_path}")
                return None
        else:
            df = _safe_read_table(data_path)

        # normalize possible index column names into 'Date'
        if 'Date' not in df.columns and 'date' in df.columns:
            df['Date'] = df['date']
        if 'Date' not in df.columns and 'Unnamed: 0' in df.columns:
            df['Date'] = df['Unnamed: 0']

        # If no date-like column exists, try to use a DatetimeIndex; otherwise fail gracefully
        if 'Date' not in df.columns and 'date' not in df.columns:
            if isinstance(df.index, pd.DatetimeIndex):
                df['Date'] = df.index
            else:
                print("[ERROR] 데이터에 'Date' 또는 'date' 컬럼이 없습니다.")
                return None

        df.reset_index(inplace=True, drop=True) # ensure a flat index
        print(f"  -> 전체 데이터 로드 완료. (총 {len(df)}개 행)")
    except Exception as e:
        print(f"[ERROR] 데이터 파일({data_path}) 로딩 실패: {e}")
        return None

    # 2. 날짜 및 종목 필터링
    print("[2/4] 데이터 필터링 중...")
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    
    df['Date'] = pd.to_datetime(df['Date'])
    
    filtered_df = df[
        (df['Date'] >= start_date) & 
        (df['Date'] <= end_date) & 
        (df['code'].isin(target_stocks))
    ].copy()

    if filtered_df.empty:
        print("[ERROR] 지정된 기간과 종목에 해당하는 데이터가 없습니다.")
        return None
    print(f"  -> 필터링 완료. (총 {len(filtered_df)}개 행)")

    # 3. 피처 엔지니어링
    print("[3/4] 피처 생성 중...")
    featured_df = create_features(filtered_df)
    # Drop rows that still have NaNs introduced by rolling calculations (e.g., ma120)
    # These initial rows cannot be meaningfully used for modeling.
    featured_df = featured_df.dropna()
    print("  -> 피처 생성 완료.")

    # 4. 결측치 처리 및 최종 정리
    print("[4/4] 결측치 처리 및 최종 정리 중...")
    # create_features에서 생성된 피처들의 초기 결측치는 당연하므로, ffill/bfill로 채웁니다.
    cleaned_df = handle_missing_values(featured_df)
    final_df = cleaned_df.reset_index(drop=True)
    print(f"  -> 처리 완료. 최종 {len(final_df)}개 행, 남은 결측치: {final_df.isnull().sum().sum()}개")
    
    print("=== 데이터 전처리 완료 ===")
    return final_df
