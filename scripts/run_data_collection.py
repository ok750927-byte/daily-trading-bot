"""
데이터 수집 및 저장을 실행하는 스크립트.
- 시세(OHLCV) 데이터
- 재무 데이터
- 거시경제 지표 데이터
를 수집하여 'data' 디렉토리에 Parquet 형식으로 저장합니다.

실행 방법:
- trading-bot 프로젝트 루트 디렉토리에서 실행하세요.
- 예: python scripts/run_data_collection.py
"""
import os
import sys
import logging
from datetime import datetime, timedelta

# 프로젝트 루트를 sys.path에 추가하여 src 모듈을 임포트할 수 있도록 함
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

from src.data import fetch_prices, fetch_fundamentals, fetch_macro

# --- 설정 ---
# 데이터 저장 기본 경로
DATA_PATH = os.path.join(project_root, 'data')

# 1. 시세 데이터 수집 설정
PRICE_TICKERS = ['005930', '000660', '035720'] # 삼성전자, SK하이닉스, 카카오
PRICE_START_DATE = '2020-01-01'
PRICE_END_DATE = datetime.today().strftime('%Y-%m-%d')

# 2. 재무 데이터 수집 설정
# (어제 날짜를 기준으로 수집, 주말일 경우 금요일 데이터가 조회됨)
FUNDAMENTALS_DATE = (datetime.today() - timedelta(days=1)).strftime('%Y%m%d')

# 3. 거시경제 지표 수집 설정
MACRO_SYMBOLS = {
    'KS11': 'KOSPI',
    'KQ11': 'KOSDAQ',
    'USD/KRW': 'USD_KRW',
    'IXIC': 'NASDAQ',
    'US500': 'SP500'
}
MACRO_START_DATE = '2020-01-01'
MACRO_END_DATE = datetime.today().strftime('%Y-%m-%d')

def main():
    """데이터 수집 및 저장 프로세스를 실행합니다."""
    print("=== 데이터 수집 스크립트 시작 ===")

    # 1. 시세 데이터 수집 및 저장
    print(f"\n[1/3] 개별 종목 시세 데이터 수집 중... (대상: {PRICE_TICKERS})")
    prices_path = os.path.join(DATA_PATH, 'prices')
    for ticker in PRICE_TICKERS:
        print(f"  - {ticker} 데이터 수집...")
        df = fetch_prices.fetch_ohlcv(ticker, PRICE_START_DATE, PRICE_END_DATE)
        if df is not None and not df.empty:
            output_path = os.path.join(prices_path, f"{ticker}.parquet")
            df.to_parquet(output_path)
            print(f"    -> 저장 완료: {output_path}")
        else:
            print(f"    -> {ticker} 데이터 수집 실패 또는 데이터 없음.")

    # 2. 재무 데이터 수집 및 저장
    print(f"\n[2/3] 시장 전체 재무 데이터 수집 중... (기준일: {FUNDAMENTALS_DATE})")
    fundamentals_path = os.path.join(DATA_PATH, 'fundamentals')
    df_fund = fetch_fundamentals.get_market_fundamentals(FUNDAMENTALS_DATE)
    if df_fund is not None and not df_fund.empty:
        output_path = os.path.join(fundamentals_path, f"fundamentals_{FUNDAMENTALS_DATE}.parquet")
        df_fund.to_parquet(output_path)
        print(f"  -> 저장 완료: {output_path}")
    else:
        print(f"  -> 재무 데이터 수집 실패 또는 데이터 없음.")

    # 3. 거시경제 지표 수집 및 저장
    print(f"\n[3/3] 거시경제 지표 데이터 수집 중...")
    macro_path = os.path.join(DATA_PATH, 'macro')
    df_macro = fetch_macro.get_macro_data(MACRO_SYMBOLS, MACRO_START_DATE, MACRO_END_DATE)
    if df_macro is not None and not df_macro.empty:
        filename = f"macro_{MACRO_START_DATE.replace('-', '')}_{MACRO_END_DATE.replace('-', '')}.parquet"
        output_path = os.path.join(macro_path, filename)
        df_macro.to_parquet(output_path)
        print(f"  -> 저장 완료: {output_path}")
    else:
        print(f"  -> 거시경제 지표 수집 실패 또는 데이터 없음.")

    print("\n=== 모든 데이터 수집 작업 완료 ===")

if __name__ == "__main__":
    # 기본 로깅 설정
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
    main()
