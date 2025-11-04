
import getpass
import os
import shutil
import datetime

def is_admin():
    """운영자/관리자 권한 분리 샘플: 관리자만 전략 배포/설정 변경 허용"""
    admin_users = os.environ.get('ADMIN_USERS', 'admin').split(',')
    user = getpass.getuser()
    return user in admin_users

def deploy_strategy_with_auth(strategy_file, backup_dir='deploy_backups'):
    if not is_admin():
        print('[권한] 관리자만 전략 배포/설정 변경이 가능합니다.')
        return False
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(backup_dir, f'strategy_{now}.py')
    shutil.copy2(strategy_file, backup_path)
    shutil.copy2(strategy_file, 'src/modeling/strategy_signals.py')
    print(f'[배포] 관리자 인증 완료, 전략 파일 {strategy_file} → 운영 반영 및 백업 완료')
    return True

if __name__ == "__main__":
    deploy_strategy_with_auth('new_strategy.py')
if __name__ == "__main__":
    deploy_strategy_with_auth('new_strategy.py')
