#!/bin/bash
# Docker 컨테이너 엔트리포인트 스크립트

set -e

echo "🚀 AI Trading Bot 시작..."

# 환경변수 확인
echo "Environment: ${ENVIRONMENT:-development}"
echo "Trading Enabled: ${TRADING_ENABLED:-false}"
echo "Dry Run Mode: ${DRY_RUN:-true}"

# 디렉토리 생성 및 권한 설정
mkdir -p /app/logs /app/data /app/models /app/results
chmod 755 /app/logs /app/data /app/models /app/results

# 환경변수 검증
echo "🔍 환경변수 검증 중..."
python src/trading/env_check.py

# 데이터베이스 연결 테스트 (PostgreSQL 사용시)
if [ ! -z "$DB_HOST" ]; then
    echo "🗄️ 데이터베이스 연결 테스트 중..."
    python -c "
import os
import psycopg2
try:
    conn = psycopg2.connect(
        host=os.environ.get('DB_HOST'),
        port=os.environ.get('DB_PORT', 5432),
        database=os.environ.get('DB_NAME'),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD')
    )
    conn.close()
    print('✅ 데이터베이스 연결 성공')
except Exception as e:
    print(f'❌ 데이터베이스 연결 실패: {e}')
    exit(1)
"
fi

# Redis 연결 테스트 (Redis 사용시)
if [ ! -z "$REDIS_URL" ]; then
    echo "📡 Redis 연결 테스트 중..."
    python -c "
import redis
import os
try:
    r = redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379'))
    r.ping()
    print('✅ Redis 연결 성공')
except Exception as e:
    print(f'❌ Redis 연결 실패: {e}')
    exit(1)
"
fi

# Discord 웹훅 테스트 (설정된 경우)
if [ ! -z "$DISCORD_WEBHOOK_URL" ]; then
    echo "🎮 Discord 웹훅 테스트 중..."
    python -c "
import requests
import os
try:
    url = os.environ.get('DISCORD_WEBHOOK_URL')
    response = requests.get(url, timeout=5)
    if response.status_code == 200:
        print('✅ Discord 웹훅 연결 성공')
    else:
        print(f'⚠️ Discord 웹훅 응답: {response.status_code}')
except Exception as e:
    print(f'❌ Discord 웹훅 테스트 실패: {e}')
"
fi

# 모델 파일 존재 여부 확인
echo "🤖 ML 모델 파일 확인 중..."
if [ -f "/app/models/random_forest_model.joblib" ] && [ -f "/app/models/scaler.joblib" ]; then
    echo "✅ ML 모델 파일 존재"
else
    echo "⚠️ ML 모델 파일이 없습니다. 초기 학습이 필요합니다."
fi

# 시스템 시작 알림 전송
echo "📨 시스템 시작 알림 전송 중..."
python -c "
import sys
sys.path.append('/app')
try:
    from src.trading.discord_alert import AlertManager
    alert_manager = AlertManager()
    alert_manager.notify_system('success', '🐳 Docker 컨테이너가 성공적으로 시작되었습니다!')
except Exception as e:
    print(f'알림 전송 실패: {e}')
"

# Supervisor로 서비스 시작
echo "🔄 서비스 시작 중..."
exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf