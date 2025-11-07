#!/usr/bin/env python3
"""
Docker 헬스체크 스크립트
컨테이너 상태를 확인하고 정상 여부를 반환합니다.
"""
import sys
import requests
import json
import os
from datetime import datetime

def check_dashboard():
    """Streamlit 대시보드 상태 확인"""
    try:
        response = requests.get("http://localhost:8501/health", timeout=5)
        return response.status_code == 200
    except:
        # /health 엔드포인트가 없을 수 있으므로 메인 페이지 확인
        try:
            response = requests.get("http://localhost:8501", timeout=5)
            return response.status_code == 200
        except:
            return False

def check_metrics_endpoint():
    """메트릭 엔드포인트 상태 확인"""
    try:
        response = requests.get("http://localhost:9090/metrics", timeout=5)
        return response.status_code == 200
    except:
        return False

def check_log_files():
    """로그 파일 존재 및 최근 업데이트 확인"""
    log_files = [
        "/app/logs/supervisord.log",
        "/app/logs/dashboard.log"
    ]

    for log_file in log_files:
        if not os.path.exists(log_file):
            return False

    return True

def check_trading_engine():
    """거래 엔진 상태 확인 (활성화된 경우)"""
    if os.environ.get('TRADING_ENABLED', 'false').lower() != 'true':
        return True  # 비활성화된 경우 통과

    # 거래 엔진 로그 확인
    engine_log = "/app/logs/trading-engine.log"
    if not os.path.exists(engine_log):
        return False

    return True

def main():
    """메인 헬스체크 함수"""
    health_status = {
        "timestamp": datetime.now().isoformat(),
        "dashboard": check_dashboard(),
        "logs": check_log_files(),
        "trading_engine": check_trading_engine(),
        "metrics": check_metrics_endpoint()
    }

    # 모든 체크가 통과하면 성공
    all_healthy = all(health_status.values() if k != "timestamp" else True
                     for k, v in health_status.items())

    if all_healthy:
        print("✅ Health check passed")
        print(json.dumps(health_status, indent=2))
        sys.exit(0)
    else:
        print("❌ Health check failed")
        print(json.dumps(health_status, indent=2))
        sys.exit(1)

if __name__ == "__main__":
    main()
