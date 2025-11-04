"""
윈도우 작업스케줄러/cron 자동화용 실행 스크립트 예시
- 파이프라인 전체 자동 실행, 결과 리포트/알림 연동
- python run_pipeline.py --action all 등으로 등록
"""
import os
import sys
import subprocess
from datetime import datetime

def find_workspace_root():
    env = os.environ.get('DAILY_TRADING_WORKSPACE')
    if env and os.path.isdir(env):
        return os.path.abspath(env)
    cwd = os.getcwd()
    markers = ('pyproject.toml', 'README.md', 'requirements.txt', '.git')
    cur = cwd
    while True:
        for m in markers:
            if os.path.exists(os.path.join(cur, m)):
                return os.path.abspath(cur)
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    try:
        return os.path.abspath(os.path.dirname(__file__))
    except Exception:
        return os.path.abspath(cwd)

workspace_root = find_workspace_root()
results_dir = os.path.join(workspace_root, 'results')
os.makedirs(results_dir, exist_ok=True)
LOG_PATH = os.path.join(results_dir, 'auto_run.log')

if __name__ == "__main__":
    with open(LOG_PATH, "a", encoding="utf-8") as log:
        log.write(f"\n[{datetime.now()}] 자동 파이프라인 실행 시작\n")
        try:
            # 환경변수 점검
            subprocess.run([sys.executable, "src/trading/env_check.py"], check=True)
            # 전체 파이프라인 실행
            subprocess.run([sys.executable, "main.py", "--action", "all"], check=True)
            # 전략 신호 자동주문 연동
            subprocess.run([sys.executable, "src/trading/signal_order_bridge.py"], check=True)
            log.write(f"[{datetime.now()}] 전체 자동매매/리포트 완료\n")
        except Exception as e:
            log.write(f"[{datetime.now()}] [오류] {e}\n")
        log.write(f"[{datetime.now()}] 자동 파이프라인 종료\n")
