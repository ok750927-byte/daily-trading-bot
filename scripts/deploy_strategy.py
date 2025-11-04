import shutil
import os
import datetime

def deploy_strategy(strategy_file, backup_dir='deploy_backups'):
    """
    전략 파일을 운영 디렉토리로 실시간 배포하고, 백업을 남김
    """
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(backup_dir, f'strategy_{now}.py')
    shutil.copy2(strategy_file, backup_path)
    # 운영 디렉토리(예: src/modeling/strategy_signals.py)에 덮어쓰기
    shutil.copy2(strategy_file, 'src/modeling/strategy_signals.py')
    print(f'[배포] 전략 파일 {strategy_file} → 운영 반영 및 백업 완료')

if __name__ == "__main__":
    deploy_strategy('new_strategy.py')
