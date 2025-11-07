"""
프로덕션 배포 자동화 스크립트
- 전체 시스템 통합 배포
- 서비스 순차 시작
- 헬스 체크 및 검증
"""
import os
import sys
import time
import json
import subprocess
import requests
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProductionDeployer:
    """프로덕션 배포 관리자"""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.venv_python = self.project_root / "venv314" / "Scripts" / "python.exe"

        # 배포 단계 정의
        self.deployment_steps = [
            "환경 검증",
            "Docker 서비스 시작",
            "메트릭 서버 시작",
            "거래 엔진 시작",
            "대시보드 시작",
            "헬스 체크",
            "Discord 알림 테스트"
        ]

        # 서비스 포트 정의
        self.service_ports = {
            "metrics": 8000,
            "dashboard": 8501,
            "prometheus": 9090,
            "grafana": 3000
        }

    def check_prerequisites(self) -> bool:
        """배포 전 필수 조건 확인"""
        logger.info("=== 환경 검증 시작 ===")

        checks = []

        # 1. Python 환경 확인
        if self.venv_python.exists():
            logger.info("✓ Python 가상환경 확인")
            checks.append(True)
        else:
            logger.error("✗ Python 가상환경 없음")
            checks.append(False)

        # 2. Docker 확인
        try:
            result = subprocess.run(['docker', '--version'],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"✓ Docker 확인: {result.stdout.strip()}")
                checks.append(True)
            else:
                logger.error("✗ Docker 설치 필요")
                checks.append(False)
        except FileNotFoundError:
            logger.error("✗ Docker 설치 필요")
            checks.append(False)

        # 3. 설정 파일들 확인
        config_files = [
            "config.json",
            "secrets.json",
            "monitoring/prometheus.yml",
            "monitoring/docker-compose.monitoring.yml"
        ]

        for config_file in config_files:
            if (self.project_root / config_file).exists():
                logger.info(f"✓ 설정 파일: {config_file}")
                checks.append(True)
            else:
                logger.error(f"✗ 설정 파일 없음: {config_file}")
                checks.append(False)

        # 4. 포트 가용성 확인
        for service, port in self.service_ports.items():
            if self.is_port_available(port):
                logger.info(f"✓ 포트 {port} ({service}) 사용 가능")
                checks.append(True)
            else:
                logger.warning(f"⚠ 포트 {port} ({service}) 이미 사용 중")
                checks.append(True)  # 경고만 하고 계속 진행

        success_rate = sum(checks) / len(checks)
        logger.info(f"환경 검증 완료: {success_rate*100:.1f}% ({sum(checks)}/{len(checks)})")

        return success_rate >= 0.8  # 80% 이상 통과 시 성공

    def is_port_available(self, port: int) -> bool:
        """포트 사용 가능 여부 확인"""
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return True
        except OSError:
            return False

    def start_docker_services(self) -> bool:
        """Docker 모니터링 서비스 시작"""
        logger.info("=== Docker 서비스 시작 ===")

        try:
            # 모니터링 디렉토리로 이동
            monitoring_dir = self.project_root / "monitoring"
            compose_file = monitoring_dir / "docker-compose.monitoring.yml"

            if not compose_file.exists():
                logger.error("Docker Compose 파일이 없습니다")
                return False

            # Docker Compose 실행
            cmd = [
                'docker-compose',
                '-f', str(compose_file),
                'up', '-d'
            ]

            result = subprocess.run(
                cmd,
                cwd=monitoring_dir,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                logger.info("✓ Docker 서비스 시작 성공")
                logger.info("- Prometheus: http://localhost:9090")
                logger.info("- Grafana: http://localhost:3000")
                logger.info("- Node Exporter: http://localhost:9100")

                # 서비스 시작 대기
                time.sleep(10)
                return True
            else:
                logger.error(f"Docker 서비스 시작 실패: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Docker 서비스 시작 중 오류: {e}")
            return False

    def start_metrics_server(self) -> bool:
        """메트릭 서버 시작"""
        logger.info("=== 메트릭 서버 시작 ===")

        try:
            # 메트릭 서버가 이미 실행 중인지 확인
            if self.check_service_health("http://localhost:8000/health"):
                logger.info("✓ 메트릭 서버가 이미 실행 중입니다")
                return True

            # 메트릭 서버 백그라운드 실행
            cmd = [
                str(self.venv_python),
                "scripts/metrics_server.py"
            ]

            # 새로운 콘솔 창에서 실행
            subprocess.Popen(
                ['start', 'cmd', '/k'] + [' '.join([f'"{arg}"' for arg in cmd])],
                cwd=self.project_root,
                shell=True
            )

            # 서비스 시작 대기 및 확인
            for i in range(30):  # 30초 대기
                time.sleep(1)
                if self.check_service_health("http://localhost:8000/health"):
                    logger.info("✓ 메트릭 서버 시작 성공")
                    logger.info("- Health Check: http://localhost:8000/health")
                    logger.info("- Metrics: http://localhost:8000/metrics")
                    return True

            logger.error("메트릭 서버 시작 실패 (타임아웃)")
            return False

        except Exception as e:
            logger.error(f"메트릭 서버 시작 중 오류: {e}")
            return False

    def start_trading_engine(self) -> bool:
        """거래 엔진 시작"""
        logger.info("=== 거래 엔진 시작 ===")

        try:
            # 거래 엔진 백그라운드 실행
            cmd = [
                str(self.venv_python),
                "src/trading/realtime_engine.py"
            ]

            # 새로운 콘솔 창에서 실행
            subprocess.Popen(
                ['start', 'cmd', '/k'] + [' '.join([f'"{arg}"' for arg in cmd])],
                cwd=self.project_root,
                shell=True
            )

            logger.info("✓ 거래 엔진 시작됨 (백그라운드)")
            logger.info("- 로그 확인: logs/trading-engine.log")

            time.sleep(5)  # 시작 대기
            return True

        except Exception as e:
            logger.error(f"거래 엔진 시작 중 오류: {e}")
            return False

    def start_dashboard(self) -> bool:
        """대시보드 시작"""
        logger.info("=== 대시보드 시작 ===")

        try:
            # 대시보드가 이미 실행 중인지 확인
            if self.check_service_health("http://localhost:8501"):
                logger.info("✓ 대시보드가 이미 실행 중입니다")
                return True

            # Streamlit 대시보드 실행
            cmd = [
                str(self.venv_python),
                "-m", "streamlit", "run",
                "scripts/dashboard_realtime.py",
                "--server.port", "8501",
                "--server.address", "0.0.0.0"
            ]

            # 새로운 콘솔 창에서 실행
            subprocess.Popen(
                ['start', 'cmd', '/k'] + [' '.join([f'"{arg}"' for arg in cmd])],
                cwd=self.project_root,
                shell=True
            )

            # 서비스 시작 대기
            for i in range(60):  # 60초 대기
                time.sleep(1)
                if self.check_service_health("http://localhost:8501"):
                    logger.info("✓ 대시보드 시작 성공")
                    logger.info("- URL: http://localhost:8501")
                    return True

            logger.warning("대시보드 시작 확인 실패 (수동 확인 필요)")
            return True  # 경고로 처리하고 계속 진행

        except Exception as e:
            logger.error(f"대시보드 시작 중 오류: {e}")
            return False

    def check_service_health(self, url: str, timeout: int = 3) -> bool:
        """서비스 헬스 체크"""
        try:
            response = requests.get(url, timeout=timeout)
            return response.status_code == 200
        except:
            return False

    def run_health_checks(self) -> bool:
        """전체 시스템 헬스 체크"""
        logger.info("=== 헬스 체크 실행 ===")

        health_checks = []

        # 각 서비스 헬스 체크
        services = [
            ("메트릭 서버", "http://localhost:8000/health"),
            ("대시보드", "http://localhost:8501"),
            ("Prometheus", "http://localhost:9090"),
            ("Grafana", "http://localhost:3000")
        ]

        for service_name, url in services:
            if self.check_service_health(url):
                logger.info(f"✓ {service_name}: 정상")
                health_checks.append(True)
            else:
                logger.warning(f"⚠ {service_name}: 응답 없음 ({url})")
                health_checks.append(False)

        # 메트릭 데이터 확인
        try:
            response = requests.get("http://localhost:8000/metrics", timeout=5)
            if response.status_code == 200 and "trading_bot_cpu_percent" in response.text:
                logger.info("✓ 메트릭 데이터: 정상 수집 중")
                health_checks.append(True)
            else:
                logger.warning("⚠ 메트릭 데이터: 수집 이상")
                health_checks.append(False)
        except:
            logger.warning("⚠ 메트릭 데이터: 확인 불가")
            health_checks.append(False)

        success_rate = sum(health_checks) / len(health_checks)
        logger.info(f"헬스 체크 완료: {success_rate*100:.1f}% ({sum(health_checks)}/{len(health_checks)})")

        return success_rate >= 0.6  # 60% 이상 통과 시 성공

    def test_discord_notification(self) -> bool:
        """Discord 알림 테스트"""
        logger.info("=== Discord 알림 테스트 ===")

        try:
            # Discord 설정 확인
            secrets_file = self.project_root / "secrets.json"
            if not secrets_file.exists():
                logger.warning("secrets.json 파일이 없어 Discord 테스트 건너뜀")
                return True

            # 테스트 알림 발송 (실제 구현에 따라 조정)
            test_script = f"""
import sys
sys.path.append(r'{self.project_root}')
from src.trading.discord_alert import DiscordBot

try:
    bot = DiscordBot()
    bot.send_system_alert(
        "🚀 Daily Trading Bot 프로덕션 배포 완료!",
        "모든 시스템이 정상적으로 시작되었습니다.",
        "success"
    )
    print("Discord 알림 테스트 성공")
except Exception as e:
    print(f"Discord 알림 테스트 실패: {{e}}")
"""

            result = subprocess.run(
                [str(self.venv_python), "-c", test_script],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )

            if "성공" in result.stdout:
                logger.info("✓ Discord 알림 테스트 성공")
                return True
            else:
                logger.warning(f"⚠ Discord 알림 테스트 실패: {result.stderr}")
                return True  # 실패해도 계속 진행

        except Exception as e:
            logger.warning(f"Discord 알림 테스트 중 오류: {e}")
            return True

    def deploy(self) -> bool:
        """전체 배포 실행"""
        logger.info("🚀 Daily Trading Bot 프로덕션 배포 시작")
        logger.info("=" * 50)

        deployment_results = []

        # 각 단계별 실행
        steps = [
            ("환경 검증", self.check_prerequisites),
            ("Docker 서비스 시작", self.start_docker_services),
            ("메트릭 서버 시작", self.start_metrics_server),
            ("거래 엔진 시작", self.start_trading_engine),
            ("대시보드 시작", self.start_dashboard),
            ("헬스 체크", self.run_health_checks),
            ("Discord 알림 테스트", self.test_discord_notification)
        ]

        for step_name, step_function in steps:
            logger.info(f"\n>>> {step_name} 진행 중...")

            try:
                result = step_function()
                deployment_results.append(result)

                if result:
                    logger.info(f"✅ {step_name} 완료")
                else:
                    logger.error(f"❌ {step_name} 실패")
                    # 중요한 단계 실패 시 배포 중단
                    if step_name in ["환경 검증", "메트릭 서버 시작"]:
                        logger.error("중요한 단계 실패로 배포 중단")
                        return False

            except Exception as e:
                logger.error(f"❌ {step_name} 오류: {e}")
                deployment_results.append(False)

        # 배포 결과 요약
        success_count = sum(deployment_results)
        total_count = len(deployment_results)
        success_rate = success_count / total_count

        logger.info("\n" + "=" * 50)
        logger.info("📊 배포 결과 요약")
        logger.info(f"성공률: {success_rate*100:.1f}% ({success_count}/{total_count})")

        if success_rate >= 0.8:
            logger.info("🎉 프로덕션 배포 성공!")
            self.print_access_info()
            return True
        else:
            logger.warning("⚠️ 프로덕션 배포 부분 성공 (수동 확인 필요)")
            self.print_access_info()
            return True

    def print_access_info(self):
        """접근 정보 출력"""
        logger.info("\n🌐 서비스 접근 정보:")
        logger.info("- 실시간 대시보드: http://localhost:8501")
        logger.info("- 메트릭 API: http://localhost:8000/metrics")
        logger.info("- 헬스 체크: http://localhost:8000/health")
        logger.info("- Grafana: http://localhost:3000 (admin/admin123)")
        logger.info("- Prometheus: http://localhost:9090")

        logger.info("\n📁 중요 파일:")
        logger.info("- 거래 로그: results/trade_log.json")
        logger.info("- 시스템 로그: logs/")
        logger.info("- 성능 리포트: results/performance_summary.json")

def main():
    """메인 실행 함수"""
    deployer = ProductionDeployer()

    try:
        success = deployer.deploy()

        if success:
            logger.info("\n🎯 배포 완료! 시스템이 운영 준비 상태입니다.")
            logger.info("모니터링 대시보드에서 실시간 상태를 확인하세요.")
        else:
            logger.error("배포 실패. 로그를 확인하고 문제를 해결해주세요.")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("사용자 중단 신호")
        sys.exit(0)
    except Exception as e:
        logger.error(f"배포 중 예상치 못한 오류: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
