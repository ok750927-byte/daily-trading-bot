"""
주식 스크리닝 모듈
전체 상장 종목에서 유망 종목을 빠르게 필터링합니다.
"""
import pandas as pd
from datetime import datetime, timedelta

def get_all_stock_codes():
    """
    전체 상장 종목 코드를 가져옵니다.
    FinanceDataReader를 사용하여 안정적으로 종목 리스트를 가져옵니다.
    """
    try:
        import FinanceDataReader as fdr
        
        # KRX 상장 종목 전체 가져오기
        df_krx = fdr.StockListing('KRX')
        all_codes = df_krx['Code'].tolist()
        
        print(f"전체 상장 종목 수: {len(all_codes)}개")
        return all_codes
    except Exception as e:
        print(f"[오류] 전체 종목 리스트를 가져오는 중 오류 발생: {e}")
        print("[정보] 대신 주요 우량주 30개를 사용합니다.")
        # 폴백: 시가총액 상위 주요 종목 30개
        return [
            '005930', '000660', '035720', '005380', '000270',  # 삼성전자, SK하이닉스, 카카오, 현대차, 기아
            '005490', '035420', '051910', '006400', '012330',  # POSCO, NAVER, LG화학, 삼성SDI, 현대모비스
            '028260', '096770', '207940', '066570', '003670',  # 삼성물산, SK이노베이션, 삼성바이오로직스, LG전자, 포스코퓨처엠
            '323410', '000810', '017670', '034730', '086790',  # 카카오뱅크, 삼성화재, SK텔레콤, SK, 하나금융지주
            '003550', '105560', '055550', '018260', '015760',  # LG, KB금융, 신한지주, 삼성에스디에스, 한국전력
            '032830', '010130', '009150', '011200', '003490'   # 삼성생명, 고려아연, 삼성전기, HMM, 대한항공
        ]


def screen_by_volume(codes, top_n=100):
    """
    거래량 기준으로 상위 종목을 선별합니다.
    """
    try:
        from pykrx import stock
        today = datetime.now().strftime('%Y%m%d')
        
        print(f"[1/3] 거래량 기준 스크리닝 중... (상위 {top_n}개 선별)")
        
        volume_data = []
        for code in codes[:500]:  # 시간 절약을 위해 시가총액 상위 500개만 체크
            try:
                df = stock.get_market_ohlcv_by_date(
                    fromdate=(datetime.now() - timedelta(days=5)).strftime('%Y%m%d'),
                    todate=today,
                    ticker=code
                )
                if not df.empty:
                    avg_volume = df['거래량'].mean()
                    recent_price = df['종가'].iloc[-1]
                    volume_data.append({
                        'code': code,
                        'avg_volume': avg_volume,
                        'price': recent_price
                    })
            except:
                continue
        
        # 거래량 상위 종목 선별
        df_volume = pd.DataFrame(volume_data)
        if df_volume.empty:
            return []
        
        df_volume = df_volume.sort_values('avg_volume', ascending=False).head(top_n)
        selected_codes = df_volume['code'].tolist()
        
        print(f"  -> 거래량 상위 {len(selected_codes)}개 종목 선별 완료")
        return selected_codes
        
    except Exception as e:
        print(f"[오류] 거래량 스크리닝 중 오류 발생: {e}")
        return []


def screen_by_technical_indicators(codes):
    """
    기술적 지표 기반으로 유망 종목을 필터링합니다.
    - RSI: 30~70 범위 (과매도/과매수 제외)
    - 이동평균: 단기 > 장기 (상승 추세)
    - 거래량: 최근 증가 추세
    """
    try:
        import FinanceDataReader as fdr
        
        print(f"[2/3] 기술적 지표 기반 스크리닝 중...")
        
        filtered_codes = []
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)  # 최근 3개월
        
        for i, code in enumerate(codes):
            try:
                if (i + 1) % 10 == 0:
                    print(f"  -> 진행 중: {i+1}/{len(codes)}")
                
                df = fdr.DataReader(code, start_date, end_date)
                
                if df is None or len(df) < 20:
                    continue
                
                # 기술적 지표 계산
                df['MA5'] = df['Close'].rolling(window=5).mean()
                df['MA20'] = df['Close'].rolling(window=20).mean()
                
                # RSI 계산
                delta = df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                df['RSI'] = 100 - (100 / (1 + rs))
                
                # 최근 데이터
                latest = df.iloc[-1]
                
                # 필터링 조건
                if pd.isna(latest['RSI']) or pd.isna(latest['MA5']) or pd.isna(latest['MA20']):
                    continue
                
                # 조건 1: RSI가 30~70 사이 (과매도/과매수 제외)
                if not (30 <= latest['RSI'] <= 70):
                    continue
                
                # 조건 2: 단기 이동평균 > 장기 이동평균 (상승 추세)
                if latest['MA5'] <= latest['MA20']:
                    continue
                
                # 조건 3: 최근 5일 평균 거래량 > 이전 15일 평균 거래량 (거래량 증가)
                recent_volume = df['Volume'].iloc[-5:].mean()
                prev_volume = df['Volume'].iloc[-20:-5].mean()
                if recent_volume <= prev_volume * 1.2:  # 20% 이상 증가
                    continue
                
                filtered_codes.append(code)
                
            except Exception as e:
                continue
        
        print(f"  -> 기술적 지표 필터링 완료: {len(filtered_codes)}개 종목 선별")
        return filtered_codes
        
    except Exception as e:
        print(f"[오류] 기술적 지표 스크리닝 중 오류 발생: {e}")
        return codes[:30]  # 오류 시 상위 30개만 반환


def get_top_market_cap_stocks(n=500):
    """
    시가총액 상위 종목을 가져옵니다.
    FinanceDataReader를 사용하여 안정적으로 조회합니다.
    """
    try:
        import FinanceDataReader as fdr
        
        print(f"[0/3] 시가총액 상위 {n}개 종목 선별 중...")
        
        # KRX 전체 종목 가져오기
        df_krx = fdr.StockListing('KRX')
        
        # 시가총액 기준으로 정렬 (MarketCap 컬럼 사용)
        if 'MarketCap' in df_krx.columns:
            df_sorted = df_krx.sort_values('MarketCap', ascending=False)
        elif 'Marcap' in df_krx.columns:
            df_sorted = df_krx.sort_values('Marcap', ascending=False)
        else:
            # 시가총액 컬럼이 없으면 상장주식수 기준
            print("[정보] 시가총액 정보가 없어 상위 종목 순서로 선별합니다.")
            df_sorted = df_krx
        
        codes = df_sorted.head(n)['Code'].tolist()
        print(f"  -> 시가총액 상위 {len(codes)}개 종목 선별 완료")
        return codes
        
    except Exception as e:
        print(f"[오류] 시가총액 조회 중 오류 발생: {e}")
        print("[정보] 대신 전체 종목 리스트를 사용합니다.")
        all_codes = get_all_stock_codes()
        return all_codes[:min(n, len(all_codes))]


def discover_promising_stocks(max_candidates=50):
    """
    유망 종목을 자동으로 발굴합니다.
    
    Returns:
        list: 선별된 종목 코드 리스트
    """
    print("=" * 60)
    print("자동 종목 발굴을 시작합니다...")
    print("=" * 60)
    
    # 1단계: 시가총액 상위 500개로 범위 축소
    top_stocks = get_top_market_cap_stocks(500)
    
    # 2단계: 거래량 상위 100개 선별
    volume_filtered = screen_by_volume(top_stocks, top_n=100)
    
    if not volume_filtered:
        print("[경고] 거래량 필터링 실패. 시가총액 상위 50개를 사용합니다.")
        return top_stocks[:max_candidates]
    
    # 3단계: 기술적 지표로 최종 필터링
    final_candidates = screen_by_technical_indicators(volume_filtered)
    
    if not final_candidates:
        print("[경고] 기술적 지표 필터링 결과 없음. 거래량 상위 종목을 사용합니다.")
        return volume_filtered[:max_candidates]
    
    # 최대 개수 제한
    result = final_candidates[:max_candidates]
    
    print("=" * 60)
    print(f"[완료] 총 {len(result)}개의 유망 종목을 발굴했습니다.")
    print(f"종목 코드: {result[:10]}{'...' if len(result) > 10 else ''}")
    print("=" * 60)
    
    return result


if __name__ == '__main__':
    # 테스트 실행
    promising_stocks = discover_promising_stocks(max_candidates=30)
    print(f"\n최종 선별된 종목: {promising_stocks}")
