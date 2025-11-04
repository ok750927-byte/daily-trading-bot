import pytest
import os
import joblib
import pandas as pd
import numpy as np
from src.backtesting.backtester import run_backtesting


class DummyScaler:
    def transform(self, X):
        import numpy as _np
        try:
            return _np.asarray(X)
        except Exception:
            return _np.array(X)


class DummyModel:
    def predict(self, X):
        import numpy as _np
        n = _np.asarray(X).shape[0]
        return _np.ones(n, dtype=int)


def test_run_backtesting(tmp_path):
    """run_backtesting 기본 동작 테스트 - 임시 데이터/모델/스케일러 생성 후 실행"""
    # 1) 테스트 데이터 생성 (간단한 DataFrame)
    df = pd.DataFrame([
        {
            'date': '2025-10-01', 'code': 'AAA', 'future_return': 0.02,
            'Close': 100, 'ma5': 99, 'ma20': 95, 'ma60': 90, 'ma120': 85,
            'volume_ma5': 1000, 'volume_ma20': 900, 'rsi': 45, 'macd_signal': 0.1
        },
        {
            'date': '2025-10-02', 'code': 'AAA', 'future_return': -0.01,
            'Close': 101, 'ma5': 100, 'ma20': 96, 'ma60': 91, 'ma120': 86,
            'volume_ma5': 1100, 'volume_ma20': 920, 'rsi': 55, 'macd_signal': -0.05
        },
        {
            'date': '2025-10-01', 'code': 'BBB', 'future_return': 0.03,
            'Close': 200, 'ma5': 198, 'ma20': 190, 'ma60': 185, 'ma120': 180,
            'volume_ma5': 2000, 'volume_ma20': 1800, 'rsi': 40, 'macd_signal': 0.2
        }
    ])

    data_file = tmp_path / 'test_data.csv'
    df.to_csv(str(data_file), index=False)

    # 2) 더미 스케일러 및 모델 생성 (모듈 레벨의 DummyModel/DummyScaler 사용)
    model_path = tmp_path / 'model.joblib'
    scaler_path = tmp_path / 'scaler.joblib'
    joblib.dump(DummyModel(), str(model_path))
    joblib.dump(DummyScaler(), str(scaler_path))

    # 3) 실행 및 결과 확인
    out_dir = tmp_path / 'out'
    os.makedirs(str(out_dir), exist_ok=True)

    try:
        run_backtesting(
            data_path=str(data_file),
            model_path=str(model_path),
            scaler_path=str(scaler_path),
            output_dir=str(out_dir)
        )
    except Exception as e:
        pytest.fail(f"run_backtesting 실행 중 예외 발생: {e}")

    # 결과 그래프 파일 존재 확인
    assert os.path.exists(os.path.join(str(out_dir), 'backtest_results.png'))

