"""
메트릭 HTTP 서버
Prometheus가 스크래핑할 수 있는 HTTP 엔드포인트 제공
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.metrics_collector import MetricsCollector
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MetricsHandler(BaseHTTPRequestHandler):
    """메트릭 HTTP 요청 핸들러"""
    
    def __init__(self, metrics_collector, *args, **kwargs):
        self.metrics_collector = metrics_collector
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """GET 요청 처리"""
        if self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.end_headers()
            
            # Prometheus 형식 메트릭 생성
            metrics_text = self.metrics_collector.generate_prometheus_metrics()
            self.wfile.write(metrics_text.encode('utf-8'))
            
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            health_status = {
                "status": "healthy",
                "timestamp": time.time(),
                "service": "trading-bot-metrics"
            }
            
            import json
            self.wfile.write(json.dumps(health_status).encode('utf-8'))
            
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """로그 메시지 (기본 로그 비활성화)"""
        pass

class MetricsServer:
    """메트릭 HTTP 서버"""
    
    def __init__(self, port=8000, host='localhost'):
        self.port = port
        self.host = host
        self.server = None
        self.running = False
        self.metrics_collector = MetricsCollector(collection_interval=30)
        
    def start(self):
        """서버 시작"""
        if not self.running:
            self.running = True
            
            # 메트릭 수집기 시작
            self.metrics_collector.start()
            
            # HTTP 서버 설정
            def handler(*args, **kwargs):
                return MetricsHandler(self.metrics_collector, *args, **kwargs)
            
            self.server = HTTPServer((self.host, self.port), handler)
            
            # 서버를 별도 스레드에서 실행
            self.server_thread = threading.Thread(
                target=self.server.serve_forever, 
                daemon=True
            )
            self.server_thread.start()
            
            logger.info(f"메트릭 서버 시작: http://{self.host}:{self.port}")
            logger.info("엔드포인트:")
            logger.info(f"  - http://{self.host}:{self.port}/metrics (Prometheus)")
            logger.info(f"  - http://{self.host}:{self.port}/health (Health Check)")
    
    def stop(self):
        """서버 중지"""
        if self.running:
            self.running = False
            
            # 메트릭 수집기 중지
            self.metrics_collector.stop()
            
            # HTTP 서버 중지
            if self.server:
                self.server.shutdown()
                self.server_thread.join()
            
            logger.info("메트릭 서버 중지됨")

def main():
    """메인 실행 함수"""
    server = MetricsServer(port=8000, host='0.0.0.0')  # 모든 인터페이스에서 접근 가능
    
    try:
        server.start()
        
        print("메트릭 서버가 실행 중입니다...")
        print("http://localhost:8000/metrics - Prometheus 메트릭")
        print("http://localhost:8000/health - 헬스 체크")
        print("Ctrl+C로 중지")
        
        # 메인 루프
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("사용자 중단 신호 받음")
    finally:
        server.stop()

if __name__ == "__main__":
    main()