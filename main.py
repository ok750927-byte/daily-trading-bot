import os
import sys
import json
from datetime import datetime

from src.data.data_collector import run_collection
from src.data.stock_screener import discover_promising_stocks
from src.modeling.train import train_model
from src.reporting.generate_predictions import generate_predictions
from src.reporting.create_report import create_report

# --- 전역 경로 및 설정 ---
PROJ_DIR = os.getcwd()
CONFIG_PATH = os.path.join(PROJ_DIR, 'config.json')
DATA_PATH = os.path.join(PROJ_DIR, 'data', 'preprocessed_data.parquet')
MODEL_PATH = os.path.join(PROJ_DIR, 'models', 'random_forest_model.joblib')
SCALER_PATH = os.path.join(PROJ_DIR, 'models', 'scaler.joblib')
PREDICTION_PATH = os.path.join(PROJ_DIR, 'results', 'predictions.json')
REPORT_PATH = os.path.join(PROJ_DIR, 'results', 'daily_report.html')

def load_config():
    """설정 파일(config.json)을 로드합니다."""
    if not os.path.exists(CONFIG_PATH):
        # 기본 설정 파일 생성
        default_config = {
            "target_stocks": ["005930", "000660", "035720"],
            "start_date": "2010-01-01"
        }
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=4)
        return default_config

    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def run_pipeline(action=None, force_train=False, auto_discover=False):
    """
    GUI 또는 다른 스크립트에서 호출할 수 있는 메인 파이프라인 함수.

    Args:
        action (str): 'train', 'predict', 'all', 'discover' 중 하나.
        force_train (bool): True일 경우 강제로 모델을 재학습.
        auto_discover (bool): True일 경우 자동으로 유망 종목 발굴.
    """
    # If caller did not pass an explicit action, allow parsing from sys.argv
    if action is None:
        import argparse
        p = argparse.ArgumentParser(add_help=False)
        p.add_argument('--action', default='all')
        p.add_argument('--force-train', action='store_true')
        p.add_argument('--auto-discover', action='store_true')
        try:
            ns, _ = p.parse_known_args()
            action = ns.action
            force_train = ns.force_train
            auto_discover = ns.auto_discover
        except Exception:
            action = 'all'

    config = load_config()

    # 자동 발굴 모드
    if auto_discover or action == 'discover':
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] '자동 종목 발굴' 작업을 시작합니다.")

        # 유망 종목 발굴
        promising_stocks = discover_promising_stocks(max_candidates=30)

        if not promising_stocks:
            print("[오류] 유망 종목을 찾지 못했습니다.")
            return

        # 발굴된 종목을 config에 저장
        config['target_stocks'] = promising_stocks
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)

        print(f"\n발굴된 {len(promising_stocks)}개 종목을 설정에 저장했습니다.")
        print(f"종목: {promising_stocks[:10]}{'...' if len(promising_stocks) > 10 else ''}")

        # 발굴 후 자동으로 전체 파이프라인 실행
        action = 'all'
        force_train = True

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] '{action}' 작업을 시작합니다.")
    print(f"설정: 대상 종목={config['target_stocks'][:5]}{'...' if len(config['target_stocks']) > 5 else ''} (총 {len(config['target_stocks'])}개), 데이터 시작일={config['start_date']}")

    # --- 1. 데이터 수집 및 모델 학습 ---
    if action in ['train', 'all']:
        print("\n----- 1. 데이터 수집 및 전처리 시작 -----")
        run_collection(
            target_stocks=config['target_stocks'],
            start_date=config['start_date'],
            end_date=datetime.now().strftime('%Y-%m-%d'),
            output_path=DATA_PATH
        )
        print("----- 데이터 수집 및 전처리 완료 -----\n")

        model_exists = os.path.exists(MODEL_PATH)
        if not model_exists or force_train:
            print("\n----- 2. 모델 학습 시작 -----")
            train_model(
                data_path=DATA_PATH,
                model_save_path=MODEL_PATH,
                scaler_save_path=SCALER_PATH
            )
            print("----- 모델 학습 완료 -----\n")
        else:
            print("\n----- 2. 모델 학습 -----")
            print(f"기존 모델({MODEL_PATH})이 존재하여 학습을 건너뜁니다.")
            if force_train:
                 print("(재학습을 원하면 GUI에서 '강제 재학습'을 체크하세요)")
            print("-----------------------\n")

    # --- 2. 예측 및 보고 ---
    if action in ['predict', 'all']:
        if not os.path.exists(MODEL_PATH):
            print("[오류] 모델 파일이 없습니다. 먼저 '학습' 또는 '전체 실행'을 수행해주세요.")
            sys.exit(1)  # 테스트는 모델이 없을 때 프로세스 종료(코드 1)를 기대함

        print("\n----- 3. 예측 생성 시작 -----")
        generate_predictions(
            data_path=DATA_PATH,
            model_path=MODEL_PATH,
            scaler_path=SCALER_PATH,
            output_path=PREDICTION_PATH,
            target_stocks=config['target_stocks']
        )
        print("----- 예측 생성 완료 -----\n")

        print("\n----- 4. 보고서 생성 시작 -----")
        create_report(
            prediction_path=PREDICTION_PATH,
            report_path=REPORT_PATH
        )
        print("----- 보고서 생성 완료 -----\n")

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] '{action}' 작업이 모두 완료되었습니다.")


if __name__ == '__main__':
    # 이 스크립트를 직접 실행할 경우, 테스트 목적으로 전체 파이프라인 실행
    print("main.py를 직접 실행합니다. 테스트 목적으로 전체 파이프라인을 실행합니다.")
    run_pipeline(action='all', force_train=True)
