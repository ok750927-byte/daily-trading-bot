# 딥러닝(LSTM) 기반 전략 신호 (샘플)
def lstm_predict_signal(df, lstm_model=None):
    """LSTM 등 딥러닝 모델 예측 신호 (모델이 있으면 예측값, 없으면 0)"""
    if lstm_model is not None:
        # 예시: LSTM 모델의 예측 결과를 신호로 사용
        df['lstm_signal'] = lstm_model.predict(df)
    else:
        df['lstm_signal'] = 0
    return df

# 강화학습 기반 전략 신호 (샘플)
def rl_predict_signal(df, rl_agent=None):
    """강화학습 에이전트의 액션 신호 (에이전트가 있으면 예측값, 없으면 0)"""
    if rl_agent is not None:
        df['rl_signal'] = rl_agent.act(df)
    else:
        df['rl_signal'] = 0
    return df
"""
단타 전략 고도화 샘플 (갭매매, 돌파매매 등)
- 기존 feature_engineering.py와 연동, 신호 생성 함수 추가
- 멀티모델/딥러닝 확장 구조 예시 포함
"""
import pandas as pd
import numpy as np

def gap_trading_signal(df, gap_threshold=0.03):
    """갭상승/하락 단타 신호 생성"""
    df['gap'] = (df['Open'] - df['Close'].shift(1)) / df['Close'].shift(1)
    df['gap_signal'] = np.where(df['gap'] > gap_threshold, 1, np.where(df['gap'] < -gap_threshold, -1, 0))
    return df

def breakout_signal(df, window=20):
    """돌파매매 신호 생성 (20일 신고가/신저가 돌파)"""
    df['high_break'] = (df['High'] >= df['High'].rolling(window).max().shift(1)).astype(int)
    df['low_break'] = (df['Low'] <= df['Low'].rolling(window).min().shift(1)).astype(int)
    return df

# 모멘텀 전략 신호
def momentum_signal(df, short_window=10, long_window=60):
    """모멘텀 신호: 단기/장기 이동평균 골든크로스/데드크로스"""
    df['ma_short'] = df['Close'].rolling(window=short_window).mean()
    df['ma_long'] = df['Close'].rolling(window=long_window).mean()
    df['momentum_signal'] = np.where(df['ma_short'] > df['ma_long'], 1, 0)
    return df

# AI 기반 전략 신호 (샘플)
def ai_predict_signal(df, model=None):
    """AI/ML 모델 예측 신호 (모델이 있으면 예측값, 없으면 0)"""
    if model is not None:
        df['ai_signal'] = model.predict(df)
    else:
        df['ai_signal'] = 0
    return df

# 멀티모델/딥러닝 확장 예시 (구현 필요)
def multi_model_predict(df, models):
    """여러 모델 예측 결과 ensemble"""
    preds = [m.predict(df) for m in models]
    return np.mean(preds, axis=0)

# 사용 예시
import json

def load_strategy_params(config_path='config.json'):
    """config.json에서 전략 파라미터 실시간 로드"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config.get('strategy_params', {})
    except Exception:
        return {}

def generate_signals(df, ai_model=None, config_path='config.json'):
    params = load_strategy_params(config_path)
    gap_th = params.get('gap_threshold', 0.03)
    breakout_win = params.get('breakout_window', 20)
    mom_short = params.get('momentum_short', 10)
    mom_long = params.get('momentum_long', 60)
    df = gap_trading_signal(df, gap_threshold=gap_th)
    df = breakout_signal(df, window=breakout_win)
    df = momentum_signal(df, short_window=mom_short, long_window=mom_long)
    df = ai_predict_signal(df, model=ai_model)
    # ... 기존 기술적지표/ML 신호와 결합
    return df

if __name__ == "__main__":
    # 샘플 데이터 로드 및 신호 생성
    df = pd.read_csv('data/prices/sample.csv')
    df = generate_signals(df)
    print(df[['gap_signal', 'high_break', 'low_break']].tail())
