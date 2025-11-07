import pytest
import os
import json
import joblib
import pandas as pd
import numpy as np
from src.reporting.generate_predictions import generate_predictions
from src.reporting.create_report import create_report


# Module-level dummy classes so joblib can pickle them
class DummyScaler:
    def transform(self, X):
        import numpy as _np
        return _np.asarray(X)


class DummyModel:
    def predict(self, X):
        import numpy as _np
        # predict '1' (상승) for all rows
        n = _np.asarray(X).shape[0]
        return _np.ones(n, dtype=int)

def test_generate_predictions_and_create_report(tmp_path):
    """generate_predictions와 create_report의 통합 기본 동작 테스트"""
    # 1) 간단한 입력 데이터(parquet)를 생성
    df = pd.DataFrame([
        {'date': '2025-10-01', 'code': '005930', 'Close': 85000, 'ma5': 84000, 'ma20': 83000,
         'ma60': 82000, 'ma120': 81000, 'volume_ma5': 1000, 'volume_ma20': 900, 'rsi': 40, 'macd_signal': 0.1},
        {'date': '2025-10-01', 'code': '000660', 'Close': 130000, 'ma5': 129000, 'ma20': 128000,
         'ma60': 127000, 'ma120': 126000, 'volume_ma5': 2000, 'volume_ma20': 1800, 'rsi': 35, 'macd_signal': 0.2}
    ])
    data_file = tmp_path / 'preprocessed_data.csv'
    df.to_csv(str(data_file), index=False)

    # 2) 더미 스케일러/모델 생성 (모듈 스코프에 정의된 DummyModel/DummyScaler 사용)
    model_path = tmp_path / 'model.joblib'
    scaler_path = tmp_path / 'scaler.joblib'
    joblib.dump(DummyModel(), str(model_path))
    joblib.dump(DummyScaler(), str(scaler_path))

    # 3) generate_predictions 실행
    output_path = str(tmp_path / 'predictions.json')
    try:
        generate_predictions(
            data_path=str(data_file),
            model_path=str(model_path),
            scaler_path=str(scaler_path),
            output_path=output_path,
            target_stocks=['005930', '000660']
        )
    except Exception as e:
        pytest.fail(f"generate_predictions 실행 중 예외 발생: {e}")

    assert os.path.exists(output_path), "예측 결과 파일이 생성되지 않았습니다."

    # 4) create_report 호출 및 결과 확인
    report_path = str(tmp_path / 'daily_report.html')
    try:
        create_report(prediction_path=output_path, report_path=report_path)
    except Exception as e:
        pytest.fail(f"create_report 실행 중 예외 발생: {e}")

    assert os.path.exists(report_path)
    with open(report_path, 'r', encoding='utf-8') as f:
        html = f.read()
        assert '<h1' in html or 'AI 추천 종목' in html
