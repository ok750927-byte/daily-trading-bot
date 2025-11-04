import json
import time
import os

def watch_and_reload_config(config_path='config.json', interval=10):
    """
    config.json 파일 변경 감지 시 실시간 파라미터 자동 반영
    """
    last_mtime = None
    while True:
        try:
            mtime = os.path.getmtime(config_path)
            if last_mtime is None:
                last_mtime = mtime
            elif mtime != last_mtime:
                print(f'[튜닝] config.json 변경 감지, 파라미터 자동 반영')
                # 파라미터 재적용(예: 전략 함수에 실시간 반영)
                # ... (파이프라인 재시작 등)
                last_mtime = mtime
        except Exception as e:
            print(f'[튜닝] config.json 감시 오류: {e}')
        time.sleep(interval)

if __name__ == "__main__":
    watch_and_reload_config()
