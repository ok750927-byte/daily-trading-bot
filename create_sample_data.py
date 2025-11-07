"""
샘플 가격 데이터 생성 스크립트
"""
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

def create_sample_price_data():
    """샘플 가격 데이터 생성"""
    # 프로젝트 루트
    project_root = Path('.')
    symbols = ['005930', '000660', '035420', '035720', '051910']

    print('📊 샘플 가격 데이터 생성 중...')

    # 각 종목별 데이터 생성
    for i, symbol in enumerate(symbols):
        data_file = project_root / 'data' / 'prices' / f'{symbol}.csv'
        data_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 1년간 샘플 데이터 생성
        dates = pd.date_range(start='2023-01-01', end='2024-10-31', freq='D')
        
        # 시드 설정으로 재현 가능한 결과
        np.random.seed(42 + i)
        
        # 종목별 다른 초기 가격
        initial_prices = [70000, 130000, 320000, 2800000, 85000]
        initial_price = initial_prices[i]
        
        # 일간 수익률 (약간의 트렌드 포함)
        trend = np.linspace(0, 0.2, len(dates))  # 연간 20% 상승 트렌드
        daily_trend = np.diff(np.concatenate([[0], trend]))
        
        returns = np.random.normal(0.001, 0.025, len(dates)) + daily_trend
        
        # 가격 계산
        prices = [initial_price]
        for ret in returns[1:]:
            prices.append(max(1000, prices[-1] * (1 + ret)))  # 최소 1000원
        
        # OHLC 데이터 생성
        opens = prices.copy()
        closes = prices.copy()
        
        highs = []
        lows = []
        volumes = []
        
        for price in prices:
            # 일중 변동폭 (1-5%)
            volatility = np.random.uniform(0.01, 0.05)
            
            high = price * (1 + volatility * np.random.uniform(0, 1))
            low = price * (1 - volatility * np.random.uniform(0, 1))
            
            # 거래량 (100만~1000만 주)
            volume = np.random.randint(1000000, 10000000)
            
            highs.append(high)
            lows.append(low)
            volumes.append(volume)
        
        # DataFrame 생성
        df = pd.DataFrame({
            'date': dates.strftime('%Y-%m-%d'),
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes
        })
        
        # CSV 저장
        df.to_csv(data_file, index=False)
        print(f'   ✅ {symbol}: {len(df)}일 데이터 생성')

    print('✅ 모든 샘플 데이터 생성 완료!')

if __name__ == "__main__":
    create_sample_price_data()