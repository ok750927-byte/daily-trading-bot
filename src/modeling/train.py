import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report
import joblib
import os
import warnings

from src.preprocessing.data_preprocessor import preprocess_data, _safe_read_table
from src.modeling.feature_engineering import create_features, create_target, split_data

# 경고 메시지 무시
warnings.filterwarnings('ignore', category=FutureWarning)

def train_model(data_path, model_save_path, scaler_save_path):
    """
    지정된 경로의 데이터를 사용하여 RandomForest 모델을 훈련, 평가하고 저장합니다.

    Args:
        data_path (str): 훈련에 사용할 데이터 파일(.parquet) 경로.
        model_save_path (str): 훈련된 모델을 저장할 경로.
        scaler_save_path (str): 훈련된 스케일러를 저장할 경로.
    """
    # --- 1. 데이터 로드 ---
    print("데이터 로드를 시작합니다...")
    try:
        df = _safe_read_table(data_path)
        print(f"데이터 로드 완료. 형태: {df.shape}")
    except FileNotFoundError:
        print(f"[ERROR] 데이터 파일({data_path})을 찾을 수 없습니다.")
        return
    except Exception as e:
        print(f"[ERROR] 데이터 파일({data_path}) 로드 실패: {e}")
        return

    # --- 2. 피처 및 타겟 생성 ---
    print("피처 및 타겟 생성을 시작합니다...")
    df_with_features = create_features(df)
    df_with_target = create_target(df_with_features, period=5)

    features = [
        'ma5', 'ma20', 'ma60', 'ma120',
        'volume_ma5', 'volume_ma20',
        'rsi', 'macd_signal',
        'bollinger_upper', 'bollinger_lower',
        'BPS', 'PER', 'PBR', 'EPS', 'DIV', 'DPS'
    ]
    target = 'target'

    # 데이터프레임에 존재하는 피처만 선택
    available_features = [f for f in features if f in df_with_target.columns]
    print(f"사용 가능한 피처: {available_features}")

    df_cleaned = df_with_target.dropna(subset=available_features + [target])

    if df_cleaned.empty:
        print("[ERROR] 훈련에 사용할 데이터가 없습니다. (결측치 제거 후 비어 있음)")
        return

    print(f"결측치 제거 후 최종 훈련 데이터 수: {len(df_cleaned)}")

    # --- 3. 데이터 분할 및 스케일링 ---
    X_train, X_test, y_train, y_test, scaler = split_data(
        df_cleaned, available_features, target, test_size=0.2, random_state=42
    )
    print("데이터를 훈련 세트와 테스트 세트로 분할했습니다.")

    # --- 4. 모델 훈련 ---
    print("RandomForest 모델 훈련을 시작합니다...")
    model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced', n_jobs=-1)
    model.fit(X_train, y_train)
    print("모델 훈련을 완료했습니다.")

    # --- 5. 모델 평가 ---
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    conf_matrix = confusion_matrix(y_test, y_pred)
    class_report = classification_report(y_test, y_pred)

    print("\n--- RandomForest 모델 평가 결과 ---")
    print(f"정확도: {accuracy:.4f}")
    print("\n혼동 행렬:")
    print(conf_matrix)
    print("\n분류 리포트:")
    print(class_report)
    print("-------------------------------------\n")

    # --- 6. 모델 및 스케일러 저장 ---
    os.makedirs(os.path.dirname(model_save_path), exist_ok=True)
    os.makedirs(os.path.dirname(scaler_save_path), exist_ok=True)

    joblib.dump(model, model_save_path)
    joblib.dump(scaler, scaler_save_path)

    print(f"훈련된 모델을 '{model_save_path}'에 저장했습니다.")
    print(f"스케일러를 '{scaler_save_path}'에 저장했습니다.")


if __name__ == '__main__':
    train_model()
