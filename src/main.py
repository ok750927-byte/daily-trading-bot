import argparse
import os
import sys
from datetime import datetime

# 이 스크립트는 프로젝트 루트 디렉토리에서 'python -m src.main' 명령으로 실행해야 합니다.
from src.data.data_collector import run_collection
from src.modeling.train import train_model
from src.reporting.generate_predictions import generate_predictions
from src.reporting.create_report import create_report

def main():
    """
    주식 자동매매 봇의 메인 실행 스크립트.
    CLI 인자를 통해 '학습', '예측', '전체' 작업을 선택적으로 수행합니다.
    """
    # 프로젝트 루트 디렉토리 결정 (이 파일의 상위-상위 디렉토리)
    PROJ_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    parser = argparse.ArgumentParser(description="주식 자동매매 AI 봇")
    parser.add_argument(
        '--action',
        type=str,
        default='all',
        choices=['train', 'predict', 'all'],
        help="수행할 작업을 선택합니다: 'train' (모델 학습), 'predict' (예측 및 보고), 'all' (전체 프로세스)"
    )
    parser.add_argument(
        '--force-train',
        action='store_true',
        help="모델이 존재하더라도 강제로 재학습을 수행합니다."
    )
    args = parser.parse_args()

    # --- 경로 설정 ---
    DATA_PATH = os.path.join(PROJ_DIR, 'data', 'preprocessed_data.parquet')
    MODEL_PATH = os.path.join(PROJ_DIR, 'models', 'random_forest_model.joblib')
    SCALER_PATH = os.path.join(PROJ_DIR, 'models', 'scaler.joblib')
    PREDICTION_PATH = os.path.join(PROJ_DIR, 'results', 'predictions.json')
    REPORT_PATH = os.path.join(PROJ_DIR, 'results', 'daily_report.txt')
    PLOT_PATH = os.path.join(PROJ_DIR, 'results', 'backtest_results.png')

    print(f"[{datetime.now()}] '{args.action}' 작업을 시작합니다.")

    # --- 1. 모델 학습 ---
    if args.action in ['train', 'all']:
        # 데이터 수집 (항상 최신 데이터로)
        print("\n----- 1. 데이터 수집 및 전처리 시작 -----")
        run_collection(
            start_date="2010-01-01",
            end_date=datetime.now().strftime('%Y-%m-%d'),
            output_path=DATA_PATH
        )
        print("----- 데이터 수집 및 전처리 완료 -----\n")

        # 모델 학습
        model_exists = os.path.exists(MODEL_PATH)
        if not model_exists or args.force_train:
            print("\n----- 2. 모델 학습 시작 -----")
            train_model(
                data_path=DATA_PATH,
                model_save_path=MODEL_PATH,
                scaler_save_path=SCALER_PATH
            )
            print("----- 모델 학습 완료 -----\n")
        else:
            print("\n----- 2. 모델 학습 -----")
            print(f"기존 모델({MODEL_PATH})이 존재하여 학습을 건너뜁니다. (재학습을 원하면 --force-train 옵션을 사용하세요)")
            print("-----------------------\n")


    # --- 2. 예측 및 보고 ---
    if args.action in ['predict', 'all']:
        if not os.path.exists(MODEL_PATH):
            print("[ERROR] 모델 파일이 없습니다. 먼저 '--action train'을 실행하여 모델을 학습시켜주세요.")
            sys.exit(1)

        print("\n----- 3. 예측 생성 시작 -----")
        generate_predictions(
            model_path=MODEL_PATH,
            scaler_path=SCALER_PATH,
            output_path=PREDICTION_PATH
        )
        print("----- 예측 생성 완료 -----\n")

        print("\n----- 4. 보고서 생성 시작 -----")
        create_report(
            prediction_path=PREDICTION_PATH,
            report_path=REPORT_PATH
        )
        print("----- 보고서 생성 완료 -----\n")

    print(f"[{datetime.now()}] '{args.action}' 작업이 모두 완료되었습니다.")


if __name__ == '__main__':
    main()
