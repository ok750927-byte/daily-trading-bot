import unittest
import sys
import os
from unittest.mock import patch

# 테스트 실행을 위해 프로젝트 루트 디렉토리를 sys.path에 추가
# 이 파일의 위치(tests/)에서 한 단계 위로 올라가면 프로젝트 루트
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 이제 main 모듈 임포트 가능
from main import run_pipeline as main

class TestMain(unittest.TestCase):
    """
    main.py의 CLI 로직을 테스트합니다.
    각 action에 따라 올바른 함수들이 호출되는지 확인합니다.
    """

    @patch('main.create_report')
    @patch('main.generate_predictions')
    @patch('main.train_model')
    @patch('main.run_collection')
    @patch('os.path.exists')
    def test_action_all_force_train(self, mock_exists, mock_run_collection, mock_train_model, mock_generate_predictions, mock_create_report):
        """'--action all --force-train' 실행 시 모든 함수가 순서대로 호출되는지 테스트"""
        print("\n- Running test: test_action_all_force_train")
        mock_exists.return_value = True  # 모델이 이미 존재하는 상황을 가정
        # sys.argv를 모의 커맨드라인 인자로 설정
        sys.argv = ['main.py', '--action', 'all', '--force-train']
        
        main()

        # 각 함수가 정확히 한 번씩 호출되었는지 검증
        mock_run_collection.assert_called_once()
        mock_train_model.assert_called_once()
        mock_generate_predictions.assert_called_once()
        mock_create_report.assert_called_once()
        print("  ... Passed")

    @patch('main.create_report')
    @patch('main.generate_predictions')
    @patch('main.train_model')
    @patch('main.run_collection')
    @patch('os.path.exists')
    def test_action_train_model_exists_no_force(self, mock_exists, mock_run_collection, mock_train_model, mock_generate_predictions, mock_create_report):
        """'--action train' 실행 시, 모델이 존재하면 학습을 건너뛰는지 테스트"""
        print("- Running test: test_action_train_model_exists_no_force")
        mock_exists.return_value = True # 모델이 존재하는 것으로 가정
        sys.argv = ['main.py', '--action', 'train']

        main()

        mock_run_collection.assert_called_once()
        mock_train_model.assert_not_called() # 모델이 존재하므로 호출되지 않아야 함
        mock_generate_predictions.assert_not_called()
        mock_create_report.assert_not_called()
        print("  ... Passed")

    @patch('main.create_report')
    @patch('main.generate_predictions')
    @patch('main.train_model')
    @patch('main.run_collection')
    @patch('os.path.exists')
    def test_action_predict_model_exists(self, mock_exists, mock_run_collection, mock_train_model, mock_generate_predictions, mock_create_report):
        """'--action predict' 실행 시, 예측 및 보고서 생성 함수만 호출되는지 테스트"""
        print("- Running test: test_action_predict_model_exists")
        mock_exists.return_value = True # 모델이 존재하는 것으로 가정
        sys.argv = ['main.py', '--action', 'predict']

        main()

        mock_run_collection.assert_not_called()
        mock_train_model.assert_not_called()
        mock_generate_predictions.assert_called_once()
        mock_create_report.assert_called_once()
        print("  ... Passed")

    @patch('sys.exit')
    @patch('builtins.print') 
    @patch('os.path.exists')
    def test_action_predict_no_model(self, mock_exists, mock_print, mock_sys_exit):
        """'--action predict' 실행 시, 모델이 없으면 sys.exit(1)을 호출하는지 테스트"""
        print("- Running test: test_action_predict_no_model")
        mock_exists.return_value = False # 모델이 존재하지 않는 것으로 가정
        sys.argv = ['main.py', '--action', 'predict']

        main()

        mock_sys_exit.assert_called_with(1) # 시스템 종료 코드가 1인지 확인
        print("  ... Passed")

if __name__ == '__main__':
    unittest.main()
