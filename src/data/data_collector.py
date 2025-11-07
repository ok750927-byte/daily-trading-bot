import os
import pandas as pd
from datetime import datetime

# 현재 파일의 경로를 기준으로 프로젝트 루트 경로를 계산합니다.
# 이렇게 하면 어떤 위치에서 스크립트를 실행하더라도 올바른 경로를 참조할 수 있습니다.
PROJ_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# data 폴더 내의 다른 데이터 수집 모듈들을 임포트합니다.
from src.data.fetch_prices import fetch_ohlcv as fetch_stock_prices
from src.data.fetch_fundamentals import get_market_fundamentals as fetch_fundamentals
from src.data.fetch_macro import get_macro_data as fetch_macro_data

# 전처리 모듈을 임포트합니다.
from src.preprocessing.data_preprocessor import preprocess_data

def run_collection(target_stocks: list, start_date: str, end_date: str, output_path: str):
    """
    주가, 펀더멘털, 거시 경제 지표 데이터를 수집하고 전처리하여 하나의 파일로 저장합니다.

    Args:
        target_stocks (list): 분석 대상 종목 코드 리스트.
        start_date (str): 데이터 수집 시작일 (YYYY-MM-DD 형식).
        end_date (str): 데이터 수집 종료일 (YYYY-MM-DD 형식).
        output_path (str): 전처리된 데이터를 저장할 Parquet 파일 경로.
    """
    print(f"데이터 수집 및 전처리를 시작합니다. 기간: {start_date} ~ {end_date}")
    print(f"대상 종목: {target_stocks}")

    # --- 1. 개별 데이터 수집 ---
    print("[1/4] 주가 데이터 수집 중...")
    
    all_price_df = []
    for code in target_stocks:
        df = fetch_stock_prices(code, start_date, end_date)
        if df is not None:
            df['Code'] = code
            all_price_df.append(df)

    if not all_price_df:
        print("[경고] 주가 데이터를 수집하지 못했습니다.")
        return

    price_df = pd.concat(all_price_df)
    # Date 인덱스를 컬럼으로 변환
    price_df.reset_index(inplace=True)

    print("[2/4] 펀더멘털 데이터 수집 중...")
    # 펀더멘털 데이터는 연도별로 제공되므로, 시작 연도와 종료 연도를 계산합니다.
    start_year = pd.to_datetime(start_date).year
    end_year = pd.to_datetime(end_date).year
    
    all_fundamentals_df = []
    for year in range(start_year, end_year + 1):
        # 펀더멘털 데이터는 특정 날짜 기준으로 조회해야 하므로, 각 연도의 마지막 영업일을 사용합니다.
        # 여기서는 간단하게 각 연도의 12월 31일을 기준으로 조회합니다.
        # pykrx는 해당 날짜가 영업일이 아니면 가장 가까운 이전 영업일 데이터를 반환합니다.
        date_str = f"{year}1231"
        df = fetch_fundamentals(date_str)
        if df is not None:
            df['Date'] = pd.to_datetime(f"{year}-12-31") # 연말 기준으로 날짜 통일
            all_fundamentals_df.append(df)

    if not all_fundamentals_df:
        print("[정보] 펀더멘털 데이터를 수집하지 못했거나 해당 기간 데이터가 없습니다.")
        fundamentals_df = pd.DataFrame()
    else:
        fundamentals_df = pd.concat(all_fundamentals_df)
        # 필요한 컬럼만 선택하고, 'code'를 'Code'로 통일
        fundamentals_df = fundamentals_df[['Date', 'code', 'BPS', 'PER', 'PBR', 'EPS', 'DIV', 'DPS']]
        fundamentals_df.rename(columns={'code': 'Code'}, inplace=True)

    print("[3/4] 거시 경제 지표 데이터 수집 중...")
    macro_symbols = {
        'KS11': 'KOSPI',
        'KQ11': 'KOSDAQ',
        'USD/KRW': 'USD_KRW',
        # 'IXIC': 'NASDAQ', # 예시: 나스닥 지수
        # 'US10YT=X': 'US_10Y_Bond' # 예시: 미국 10년물 국채 금리
    }
    macro_df = fetch_macro_data(macro_symbols, start_date, end_date)
    if macro_df is None or macro_df.empty:
        print("[정보] 거시 경제 지표 데이터를 수집하지 못했거나 해당 기간 데이터가 없습니다.")
        macro_df = pd.DataFrame()
    else:
        macro_df.reset_index(inplace=True) # Date 인덱스를 컬럼으로

    # --- 2. 데이터 병합 ---
    print("[4/4] 데이터 병합 및 최종 전처리 중...")
    
    # 1. 기준 데이터프레임 준비
    merged_df = price_df.copy()
    merged_df['Date'] = pd.to_datetime(merged_df['Date'])

    # 2. 펀더멘털 데이터 병합
    if not fundamentals_df.empty:
        try:
            # 병합 키('Year') 생성
            merged_df['Year'] = merged_df['Date'].dt.year
            fundamentals_df['Date'] = pd.to_datetime(fundamentals_df['Date'])
            fundamentals_df['Year'] = fundamentals_df['Date'].dt.year
            
            # 'Code'와 'Year'를 기준으로 병합
            # 펀더멘털 데이터의 'Date' 컬럼은 연도 정보만 담고 있으므로, 병합 후 제거
            merged_df = pd.merge(merged_df, fundamentals_df.drop(columns=['Date']), on=['Code', 'Year'], how='left')
            merged_df.drop(columns=['Year'], inplace=True, errors='ignore')
            print("펀더멘털 데이터 병합 완료.")
        except Exception as e:
            print(f"[오류] 펀더멘털 데이터 병합 중 오류 발생: {e}")
            # 병합에 실패하더라도 계속 진행
            if 'Year' in merged_df.columns:
                merged_df.drop(columns=['Year'], inplace=True, errors='ignore')

    # 3. 거시 경제 데이터 병합
    if macro_df is not None and not macro_df.empty:
        try:
            # Date 인덱스를 컬럼으로 변환 (이미 변환되었을 수 있으므로 체크)
            if 'Date' not in macro_df.columns:
                macro_df.reset_index(inplace=True)
            macro_df['Date'] = pd.to_datetime(macro_df['Date'])
            
            # 'Date'를 기준으로 병합
            merged_df = pd.merge(merged_df, macro_df, on='Date', how='left')
            print("거시 경제 데이터 병합 완료.")
        except Exception as e:
            print(f"[오류] 거시 경제 데이터 병합 중 오류 발생: {e}")
            # 병합에 실패하더라도 계속 진행

    # 4. 최종 인덱스 설정 및 컬럼명 변경
    merged_df.rename(columns={'Code': 'code'}, inplace=True)
    merged_df.set_index(['Date', 'code'], inplace=True)

    # --- 3. 데이터 저장 ---
    # 전처리(피처 생성)는 모델링 단계에서 수행하므로, 여기서는 병합된 데이터를 그대로 저장합니다.
    final_df = merged_df.copy()

    # --- 4. 데이터 저장 ---
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        final_df.to_parquet(output_path)
        print(f"성공적으로 전처리된 데이터를 '{output_path}'에 저장했습니다.")
        print(f"최종 데이터 형태: {final_df.shape}")
        print(f"최종 데이터 컬럼: {final_df.columns.tolist()}")
    except Exception as e:
        print(f"[오류] 최종 데이터 저장에 실패했습니다: {e}")

if __name__ == '__main__':
    # 이 스크립트를 직접 실행할 때 사용할 테스트 코드
    TEST_START_DATE = "2022-01-01"
    TEST_END_DATE = datetime.now().strftime('%Y-%m-%d')
    TEST_OUTPUT_PATH = os.path.join(PROJ_DIR, 'data', 'preprocessed_data_test.parquet')
    
    run_collection(
        start_date=TEST_START_DATE,
        end_date=TEST_END_DATE,
        output_path=TEST_OUTPUT_PATH
    )
