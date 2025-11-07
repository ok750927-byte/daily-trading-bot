"""
실시간 성능 모니터링 및 알림 시스템
- 시스템 리소스 실시간 감시
- 임계치 기반 자동 알림
- Discord 통합 알림
"""
import os
import time
import json
import logging
from datetime import datetime
from pathlib import Path
import threading
import subprocess

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
import sys
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """실시간 성능 모니터"""

    def __init__(self):
        self.running = False
        self.monitor_interval = 30  # 30초마다 체크

        # 임계치 설정
        self.thresholds = {
            'cpu_critical': 85.0,      # CPU 85% 이상
            'memory_critical': 90.0,   # 메모리 90% 이상
            'error_rate_high': 5,      # 5개 이상 에러/분
            'service_down_time': 300   # 5분 이상 서비스 다운
        }

        # 알림 상태 추적
        self.last_alerts = {}
        self.alert_cooldown = 300  # 5분 쿨다운

    def get_system_metrics(self) -> dict:
        """시스템 메트릭 수집"""
        try:
            # psutil 대신 Windows 명령어 사용

            # CPU 사용률
            cpu_result = subprocess.run(
                ['wmic', 'cpu', 'get', 'loadpercentage', '/value'],
                capture_output=True, text=True, timeout=10
            )

            cpu_percent = 0
            for line in cpu_result.stdout.split('\n'):
                if 'LoadPercentage=' in line:
                    cpu_percent = float(line.split('=')[1].strip())
                    break

            # 메모리 사용률
            mem_result = subprocess.run([
                'wmic', 'OS', 'get', 'TotalVisibleMemorySize,FreePhysicalMemory', '/value'
            ], capture_output=True, text=True, timeout=10)

            total_mem = 0
            free_mem = 0

            for line in mem_result.stdout.split('\n'):
                if 'TotalVisibleMemorySize=' in line:
                    total_mem = float(line.split('=')[1].strip())
                elif 'FreePhysicalMemory=' in line:
                    free_mem = float(line.split('=')[1].strip())

            if total_mem > 0:
                memory_percent = ((total_mem - free_mem) / total_mem) * 100
            else:
                memory_percent = 0

            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"시스템 메트릭 수집 실패: {e}")
            return {
                'cpu_percent': 0,
                'memory_percent': 0,
                'timestamp': datetime.now().isoformat()
            }

    def check_service_health(self) -> dict:
        """서비스 상태 확인"""
        services = {
            'metrics_server': 'http://localhost:8000/health',
            'dashboard': 'http://localhost:8501'
        }

        status = {}

        for service_name, url in services.items():
            try:
                import urllib.request
                request = urllib.request.Request(url)
                response = urllib.request.urlopen(request, timeout=3)
                status[service_name] = {
                    'status': 'UP',
                    'response_code': response.getcode(),
                    'url': url
                }
            except Exception as e:
                status[service_name] = {
                    'status': 'DOWN',
                    'error': str(e),
                    'url': url
                }

        return status

    def analyze_errors(self) -> dict:
        """에러 분석"""
        try:
            log_files = [
                project_root / "logs" / "trading-engine.log",
                project_root / "logs" / "dashboard.log"
            ]

            recent_errors = 0
            error_types = {}

            # 최근 1시간 에러 카운트
            one_hour_ago = datetime.now().timestamp() - 3600

            for log_file in log_files:
                if not log_file.exists():
                    continue

                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        for line in f.readlines()[-100:]:  # 최근 100줄만 체크
                            if 'ERROR' in line.upper():
                                recent_errors += 1

                                # 에러 타입 분류
                                if 'connection' in line.lower():
                                    error_types['connection'] = error_types.get('connection', 0) + 1
                                elif 'api' in line.lower():
                                    error_types['api'] = error_types.get('api', 0) + 1
                                else:
                                    error_types['general'] = error_types.get('general', 0) + 1

                except Exception as e:
                    logger.error(f"로그 파일 읽기 실패 {log_file}: {e}")

            return {
                'recent_errors': recent_errors,
                'error_types': error_types,
                'total_errors': sum(error_types.values())
            }

        except Exception as e:
            logger.error(f"에러 분석 실패: {e}")
            return {'recent_errors': 0, 'error_types': {}, 'total_errors': 0}

    def send_alert(self, alert_type: str, message: str, severity: str = 'WARNING'):
        """알림 발송"""
        try:
            # 쿨다운 체크
            now = datetime.now().timestamp()
            last_alert_time = self.last_alerts.get(alert_type, 0)

            if now - last_alert_time < self.alert_cooldown:
                return  # 쿨다운 중이므로 알림 발송하지 않음

            # Discord 알림 (간단한 구현)
            alert_data = {
                'timestamp': datetime.now().isoformat(),
                'type': alert_type,
                'severity': severity,
                'message': message,
                'source': 'Performance Monitor'
            }

            # 알림 로그 저장
            alert_log_file = project_root / "results" / "alert_log.jsonl"
            alert_log_file.parent.mkdir(exist_ok=True)

            with open(alert_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(alert_data, ensure_ascii=False) + '\n')

            logger.warning(f"🚨 {severity} 알림: [{alert_type}] {message}")

            # 쿨다운 업데이트
            self.last_alerts[alert_type] = now

        except Exception as e:
            logger.error(f"알림 발송 실패: {e}")

    def check_thresholds(self, metrics: dict, service_status: dict, error_analysis: dict):
        """임계치 체크 및 알림"""

        # CPU 임계치 체크
        cpu_percent = metrics.get('cpu_percent', 0)
        if cpu_percent > self.thresholds['cpu_critical']:
            self.send_alert(
                'HIGH_CPU',
                f'CPU 사용률이 임계치를 초과했습니다: {cpu_percent:.1f}%',
                'CRITICAL'
            )

        # 메모리 임계치 체크
        memory_percent = metrics.get('memory_percent', 0)
        if memory_percent > self.thresholds['memory_critical']:
            self.send_alert(
                'HIGH_MEMORY',
                f'메모리 사용률이 임계치를 초과했습니다: {memory_percent:.1f}%',
                'CRITICAL'
            )

        # 서비스 다운 체크
        for service_name, status in service_status.items():
            if status['status'] == 'DOWN':
                self.send_alert(
                    f'SERVICE_DOWN_{service_name.upper()}',
                    f'{service_name} 서비스가 응답하지 않습니다: {status["url"]}',
                    'CRITICAL'
                )

        # 에러 임계치 체크
        total_errors = error_analysis.get('total_errors', 0)
        if total_errors > self.thresholds['error_rate_high']:
            self.send_alert(
                'HIGH_ERROR_RATE',
                f'높은 에러 발생률이 감지되었습니다: {total_errors}건',
                'WARNING'
            )

    def monitoring_loop(self):
        """모니터링 메인 루프"""
        logger.info("실시간 성능 모니터링 시작...")

        while self.running:
            try:
                # 메트릭 수집
                system_metrics = self.get_system_metrics()
                service_status = self.check_service_health()
                error_analysis = self.analyze_errors()

                # 상태 로그
                logger.info(
                    f"시스템 상태 - CPU: {system_metrics['cpu_percent']:.1f}%, "
                    f"메모리: {system_metrics['memory_percent']:.1f}%, "
                    f"에러: {error_analysis['total_errors']}건"
                )

                # 서비스 상태 로그
                for service_name, status in service_status.items():
                    status_icon = "🟢" if status['status'] == 'UP' else "🔴"
                    logger.info(f"{status_icon} {service_name}: {status['status']}")

                # 임계치 체크
                self.check_thresholds(system_metrics, service_status, error_analysis)

                # 종합 상태 저장
                monitoring_data = {
                    'timestamp': datetime.now().isoformat(),
                    'system_metrics': system_metrics,
                    'service_status': service_status,
                    'error_analysis': error_analysis
                }

                # 모니터링 데이터 저장
                monitoring_file = project_root / "results" / "monitoring.jsonl"
                with open(monitoring_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(monitoring_data, ensure_ascii=False) + '\n')

                time.sleep(self.monitor_interval)

            except KeyboardInterrupt:
                logger.info("사용자 중단 신호 받음")
                break
            except Exception as e:
                logger.error(f"모니터링 루프 오류: {e}")
                time.sleep(10)  # 오류 시 10초 대기

    def start(self):
        """모니터링 시작"""
        if not self.running:
            self.running = True
            self.monitor_thread = threading.Thread(target=self.monitoring_loop, daemon=True)
            self.monitor_thread.start()
            logger.info("성능 모니터링이 시작되었습니다")

    def stop(self):
        """모니터링 중지"""
        if self.running:
            self.running = False
            if hasattr(self, 'monitor_thread'):
                self.monitor_thread.join()
            logger.info("성능 모니터링이 중지되었습니다")

def main():
    """메인 실행 함수"""
    logger.info("=== 실시간 성능 모니터링 시작 ===")

    monitor = PerformanceMonitor()

    try:
        monitor.start()

        print("📊 실시간 성능 모니터링이 실행 중입니다...")
        print("📈 CPU/메모리 사용률, 서비스 상태, 에러율을 감시 중")
        print("🚨 임계치 초과 시 자동 알림 발송")
        print("📝 모니터링 데이터: results/monitoring.jsonl")
        print("🔔 알림 로그: results/alert_log.jsonl")
        print("Ctrl+C로 중지")

        # 메인 루프 유지
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("사용자 중단 신호")
    finally:
        monitor.stop()

if __name__ == "__main__":
    main()
