import pandas as pd
import joblib
import os
import numpy as np
import matplotlib.pyplot as plt
from src.preprocessing.data_preprocessor import _safe_read_table

def run_backtesting(data_path, model_path, scaler_path, output_dir):
    """
    훈련된 모델을 사용하여 백테스팅을 수행하고 결과를 분석/시각화합니다.

    Args:
        data_path (str): 테스트 데이터 경로.
        model_path (str): 훈련된 모델 경로.
        scaler_path (str): 훈련된 스케일러 경로.
        output_dir (str): 결과물(그래프 등)을 저장할 디렉토리.
    """
    print("백테스팅을 시작합니다...")
    os.makedirs(output_dir, exist_ok=True)

    # 1. 데이터 및 모델/스케일러 로드
    try:
        test_data = _safe_read_table(data_path)

        model = joblib.load(model_path)
        scaler = joblib.load(scaler_path)
        print("데이터 및 모델 로드 완료.")
    except FileNotFoundError as e:
        print(f"[ERROR] 필수 파일을 찾을 수 없습니다: {e}")
        return
    except Exception as e:
        print(f"[ERROR] 데이터 파일({data_path}) 로드 실패: {e}")
        return

    # 2. 모델 예측
    # 모델 훈련 시 사용했던 피처와 정확히 일치해야 함
    features = [
        'ma5', 'ma20', 'ma60', 'ma120',
        'volume_ma5', 'volume_ma20',
        'rsi', 'macd_signal',
    ]
    
    # 테스트 데이터에 피처가 모두 있는지 확인
    if not all(f in test_data.columns for f in features):
        missing_features = [f for f in features if f not in test_data.columns]
        print(f"[ERROR] 테스트 데이터에 필요한 피처가 없습니다: {missing_features}")
        return

    X_test = test_data[features]
    X_test_scaled = scaler.transform(X_test)
    
    test_data['prediction'] = model.predict(X_test_scaled)

    # 3. 수익률 계산
    # 전략 수익률: 모델이 1(상승)로 예측한 날의 '미래 수익률'
    test_data['strategy_return'] = test_data['future_return'] * test_data['prediction']
    
    # 시장 수익률 (Buy & Hold): 모든 날의 '미래 수익률'의 평균
    # 종목별로 계산 후 평균
    test_data['market_return'] = test_data.groupby('code')['future_return'].transform('mean')

    # 4. 누적 수익률 계산
    test_data['strategy_cumulative_return'] = (1 + test_data['strategy_return']).cumprod()
    test_data['market_cumulative_return'] = (1 + test_data['market_return']).cumprod()

    # 5. 성과 분석
    final_strategy_return = test_data['strategy_cumulative_return'].iloc[-1]
    final_market_return = test_data['market_cumulative_return'].iloc[-1]
    
    # 최대 낙폭 (Maximum Drawdown) 계산
    def calculate_mdd(cumulative_returns):
        peak = cumulative_returns.expanding(min_periods=1).max()
        drawdown = (cumulative_returns - peak) / peak
        return drawdown.min()

    strategy_mdd = calculate_mdd(test_data['strategy_cumulative_return'])
    market_mdd = calculate_mdd(test_data['market_cumulative_return'])

    # 샤프 지수 (연율화)
    def calculate_sharpe_ratio(returns, days=252):
        # 일간 수익률의 표준편차가 0인 경우 (수익률이 계속 0일 때) 0을 반환
        if returns.std() == 0:
            return 0
        return np.sqrt(days) * returns.mean() / returns.std()

    strategy_sharpe = calculate_sharpe_ratio(test_data['strategy_return'])
    market_sharpe = calculate_sharpe_ratio(test_data['market_return'])

    print("\n--- 백테스팅 결과 ---")
    print(f"최종 누적 수익률 (전략): {final_strategy_return:.2f}")
    print(f"최종 누적 수익률 (시장): {final_market_return:.2f}")
    print("-" * 20)
    print(f"최대 낙폭 (MDD) (전략): {strategy_mdd:.2%}")
    print(f"최대 낙폭 (MDD) (시장): {market_mdd:.2%}")
    print("-" * 20)
    print(f"샤프 지수 (전략): {strategy_sharpe:.2f}")
    print(f"샤프 지수 (시장): {market_sharpe:.2f}")
    print("-----------------------\n")

    # 6. 결과 시각화
    plt.figure(figsize=(12, 6))
    plt.plot(test_data['date'], test_data['strategy_cumulative_return'], label='Strategy')
    plt.plot(test_data['date'], test_data['market_cumulative_return'], label='Market (Buy & Hold)')
    plt.title('Backtesting Results: Strategy vs. Market')
    plt.xlabel('Date')
    plt.ylabel('Cumulative Return')
    plt.legend()
    plt.grid(True)
    
    # 그래프 파일로 저장
    output_plot_path = os.path.join(output_dir, 'backtest_results.png')
    plt.savefig(output_plot_path)
    print(f"백테스팅 결과 그래프를 '{output_plot_path}'에 저장했습니다.")
    
    print("백테스팅 완료.")


if __name__ == '__main__':
    # 경로 설정: 현재 파일 위치를 기반으로 워크스페이스 루트 탐색
    def find_workspace_root():
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
    TEST_DATA_PATH = os.path.join(PROJ_DIR, 'data', 'processed', 'test_data.parquet')
    MODEL_PATH = os.path.join(PROJ_DIR, 'models', 'random_forest_model.joblib')
    SCALER_PATH = os.path.join(PROJ_DIR, 'models', 'scaler.joblib')
    OUTPUT_DIR = os.path.join(PROJ_DIR, 'results')

    run_backtesting(
        data_path=TEST_DATA_PATH,
        model_path=MODEL_PATH,
        scaler_path=SCALER_PATH,
        output_dir=OUTPUT_DIR
    )
