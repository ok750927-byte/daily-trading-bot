import pandas as pd
import joblib
import os
import json
from datetime import datetime, timedelta

# 상위 디렉토리의 모듈을 import하기 위해 경로 추가
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from preprocessing.data_preprocessor import preprocess_data

def generate_predictions(data_path, model_path, scaler_path, output_path, target_stocks):
    """
    최신 데이터를 기반으로 다음 날의 주가 방향을 예측하고 결과를 저장합니다.
    """
    print("예측 생성을 시작합니다...")

    # 1. 모델 및 스케일러 로드
    try:
        model = joblib.load(model_path)
        scaler = joblib.load(scaler_path)
        print("모델 및 스케일러 로드 완료.")
    except FileNotFoundError as e:
        print(f"[ERROR] 필수 파일을 찾을 수 없습니다: {e}")
        return

    # 2. 최신 데이터 가져오기 및 전처리
    # 예측을 위해 최근 1년치 데이터 사용
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    print(f"데이터 전처리 중 ({start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')})...")
    # If a single preprocessed file (CSV or parquet) is provided, load it directly.
    if os.path.isfile(data_path) and data_path.lower().endswith('.csv'):
        try:
            df = pd.read_csv(data_path)
        except Exception as e:
            print(f"[ERROR] 데이터 파일 로드 실패: {e}")
            return
    else:
        df = preprocess_data(
            data_path=data_path,
            target_stocks=target_stocks,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d')
        )

    if df is None or df.empty:
        print("[ERROR] 예측에 사용할 데이터를 준비하지 못했습니다.")
        return
        
    # 3. 각 종목의 가장 마지막 데이터로 예측 수행
    predictions = []
    latest_data = df.groupby('code').last().reset_index()

    features = [
        'ma5', 'ma20', 'ma60', 'ma120',
        'volume_ma5', 'volume_ma20',
        'rsi', 'macd_signal',
        'bollinger_upper', 'bollinger_lower',
        'BPS', 'PER', 'PBR', 'EPS', 'DIV', 'DPS'
    ]
    
    # 데이터프레임에 존재하는 피처만 선택 (예측 시점에 일부 피처가 없을 수 있음)
    available_features = [f for f in features if f in latest_data.columns]
    
    # 피처 데이터 준비 및 결측치 확인
    X_latest = latest_data[available_features]
    if X_latest.isnull().values.any():
        print("[WARNING] 예측 데이터에 결측치가 포함되어 있습니다. 0으로 대체합니다.")
        X_latest = X_latest.fillna(0)

    X_latest_scaled = scaler.transform(X_latest)
    latest_data['prediction'] = model.predict(X_latest_scaled)
    
    # 예측 확률 추가 (상승 확률)
    if hasattr(model, 'predict_proba'):
        proba = model.predict_proba(X_latest_scaled)
        latest_data['up_probability'] = proba[:, 1]  # 1(상승) 클래스의 확률
    else:
        latest_data['up_probability'] = 0.5  # 확률을 제공하지 않는 모델의 경우
    
    # 4. '상승' 예측된 종목만 필터링
    recommended_stocks = latest_data[latest_data['prediction'] == 1]

    # 5. 결과 저장 (상승 이유 분석 포함)
    output = {
        'prediction_date': (end_date + timedelta(days=1)).strftime('%Y-%m-%d'),
        'recommendations': []
    }

    for _, row in recommended_stocks.iterrows():
        # 상승 이유 분석
        reasons = []
        
        # RSI 분석
        if 'rsi' in row and pd.notna(row['rsi']):
            if row['rsi'] < 30:
                reasons.append("RSI 과매도 구간 (반등 가능성)")
            elif 30 <= row['rsi'] <= 50:
                reasons.append("RSI 적정 수준 (상승 여력)")
        
        # 이동평균선 분석
        if 'ma5' in row and 'ma20' in row and pd.notna(row['ma5']) and pd.notna(row['ma20']):
            if row['ma5'] > row['ma20']:
                reasons.append("단기 상승 추세 (MA5 > MA20)")
            if 'Close' in row and pd.notna(row['Close']) and row['Close'] > row['ma5']:
                reasons.append("현재가가 단기 이평선 돌파")
        
        # 거래량 분석
        if 'volume_ma5' in row and 'volume_ma20' in row and pd.notna(row['volume_ma5']) and pd.notna(row['volume_ma20']):
            if row['volume_ma5'] > row['volume_ma20'] * 1.2:
                reasons.append("거래량 급증 (관심도 상승)")
        
        # 볼린저 밴드 분석
        if 'bollinger_lower' in row and 'Close' in row and pd.notna(row['bollinger_lower']) and pd.notna(row['Close']):
            if row['Close'] < row['bollinger_lower']:
                reasons.append("볼린저 밴드 하단 근접 (반등 기대)")
        
        # MACD 분석
        if 'macd_signal' in row and pd.notna(row['macd_signal']):
            if row['macd_signal'] > 0:
                reasons.append("MACD 신호 긍정적")
        
        # 기본 이유가 없는 경우
        if not reasons:
            reasons.append("AI 모델이 종합적으로 상승 신호 감지")
        
        # 예상 상승률 계산 (상승 확률 기반 추정)
        up_prob = row.get('up_probability', 0.5)
        # 확률을 상승률로 변환 (단순 선형 변환: 50% = 2%, 100% = 10%)
        estimated_gain = 2 + (up_prob - 0.5) * 16  # 50%일 때 2%, 100%일 때 10%
        estimated_gain = max(0, min(15, estimated_gain))  # 0~15% 범위로 제한
        
        output['recommendations'].append({
            'code': row['code'],
            'last_close_price': row['Close'],
            'up_probability': float(up_prob * 100),  # 퍼센트로 변환
            'estimated_gain_rate': float(estimated_gain),
            'reasons': reasons
        })

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=4, ensure_ascii=False)

    print(f"\n--- 예측 결과 ---")
    if output['recommendations']:
        print(f"다음 영업일({output['prediction_date']}) 추천 종목:")
        for item in output['recommendations']:
            print(f"  - 종목코드: {item['code']}, 최근 종가: {item['last_close_price']:,}")
    else:
        print("추천 종목이 없습니다.")
    print("--------------------")
    print(f"예측 결과를 '{output_path}'에 저장했습니다.")


if __name__ == '__main__':
    # 워크스페이스 루트 자동 탐색(환경변수 우선)
    def find_workspace_root():
        env = os.environ.get('DAILY_TRADING_WORKSPACE')
        if env and os.path.isdir(env):
            return os.path.abspath(env)
        try:
            cur = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        except Exception:
            cur = os.getcwd()
        markers = ('pyproject.toml', 'README.md', 'requirements.txt', '.git')
        root = cur
        while True:
            for m in markers:
                if os.path.exists(os.path.join(root, m)):
                    return os.path.abspath(root)
            parent = os.path.dirname(root)
            if parent == root:
                break
            root = parent
        return os.path.abspath(cur)

    PROJ_DIR = find_workspace_root()
    MODEL_PATH = os.path.join(PROJ_DIR, 'models', 'random_forest_model.joblib')
    SCALER_PATH = os.path.join(PROJ_DIR, 'models', 'scaler.joblib')
    DATA_PATH = os.path.join(PROJ_DIR, 'data')
    OUTPUT_PATH = os.path.join(PROJ_DIR, 'results', 'predictions.json')

    # target_stocks가 None이면 available 가격 데이터(\n    # data/prices/*.parquet)를 스캔하여 종목 목록을 추출합니다.
    target_stocks_list = None
    prices_dir = os.path.join(DATA_PATH, 'prices')
    if os.path.isdir(prices_dir):
        files = [f for f in os.listdir(prices_dir) if f.endswith('.parquet')]
        if files:
            target_stocks_list = [os.path.splitext(f)[0] for f in files]

    # fallback: 만약 prices에 데이터가 없으면 None을 그대로 전달하면 preprocess가 실패하지 않도록
    # generate_predictions는 preprocess_data 내부에서 빈 데이터 처리 시 예외를 출력합니다.

    generate_predictions(
        model_path=MODEL_PATH,
        scaler_path=SCALER_PATH,
        data_path=DATA_PATH,
        output_path=OUTPUT_PATH,
        target_stocks=target_stocks_list
    )
