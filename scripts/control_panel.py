"""
통합 운영 제어판 - 최종 단계
모든 서비스를 통합 관리하는 제어판
"""
import os
import sys
import json
import time
import subprocess
from datetime import datetime
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OperationalControlPanel:
    """운영 제어판"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.venv_python = self.project_root / "venv314" / "Scripts" / "python.exe"

        self.services = {
            'metrics_server': {
                'name': '메트릭 서버',
                'script': 'scripts/metrics_server.py',
                'port': 8000,
                'health_url': 'http://localhost:8000/health'
            },
            'performance_monitor': {
                'name': '성능 모니터',
                'script': 'scripts/performance_monitor.py',
                'port': None,
                'health_url': None
            },
            'trading_engine': {
                'name': '거래 엔진',
                'script': 'src/trading/realtime_engine.py',
                'port': None,
                'health_url': None
            }
        }

        self.running_processes = {}

    def show_main_menu(self):
        """메인 메뉴 표시"""
        print("\n" + "="*60)
        print("🎯 Daily Trading Bot - 운영 제어판")
        print("="*60)
        print("1. 📊 시스템 상태 확인")
        print("2. 🚀 모든 서비스 시작")
        print("3. 🛑 모든 서비스 중지")
        print("4. 🔧 개별 서비스 관리")
        print("5. 📈 실시간 모니터링")
        print("6. 📋 성능 리포트")
        print("7. 🔍 시스템 검증")
        print("8. 🌐 대시보드 열기")
        print("9. 📄 로그 확인")
        print("0. 종료")
        print("="*60)

    def check_system_status(self):
        """시스템 상태 확인"""
        print("\n📊 시스템 상태 확인 중...")

        status = {}

        # 각 서비스 상태 체크
        for service_id, service_info in self.services.items():
            print(f"   {service_info['name']} 확인 중...")

            if service_info.get('health_url'):
                # HTTP 헬스 체크
                try:
                    import urllib.request
                    request = urllib.request.Request(service_info['health_url'])
                    response = urllib.request.urlopen(request, timeout=3)
                    if response.getcode() == 200:
                        status[service_id] = "🟢 정상"
                    else:
                        status[service_id] = "🟡 응답 이상"
                except:
                    status[service_id] = "🔴 중지됨"
            else:
                # 프로세스 체크 (간단한 구현)
                if service_id in self.running_processes:
                    status[service_id] = "🟢 실행 중"
                else:
                    status[service_id] = "🔴 중지됨"

        # 결과 출력
        print("\n📋 서비스 상태:")
        for service_id, service_info in self.services.items():
            service_status = status.get(service_id, "❓ 알 수 없음")
            print(f"  {service_info['name']}: {service_status}")

        # 시스템 리소스
        try:
            print("\n🖥️ 시스템 리소스:")

            # CPU 사용률 (Windows)
            cpu_result = subprocess.run(
                ['wmic', 'cpu', 'get', 'loadpercentage', '/value'],
                capture_output=True, text=True, timeout=10
            )

            for line in cpu_result.stdout.split('\n'):
                if 'LoadPercentage=' in line:
                    cpu_percent = line.split('=')[1].strip()
                    print(f"  CPU 사용률: {cpu_percent}%")
                    break

            print(f"  프로젝트 경로: {self.project_root}")
            print(f"  Python 환경: {self.venv_python}")

        except Exception as e:
            print(f"  시스템 리소스 확인 실패: {e}")

        input("\n계속하려면 Enter를 누르세요...")

    def start_all_services(self):
        """모든 서비스 시작"""
        print("\n🚀 모든 서비스 시작 중...")

        for service_id, service_info in self.services.items():
            print(f"   {service_info['name']} 시작 중...")

            try:
                # 새 콘솔 창에서 서비스 실행
                cmd = [
                    'start', 'cmd', '/k',
                    f'cd /d "{self.project_root}" && "{self.venv_python}" {service_info["script"]}'
                ]

                process = subprocess.Popen(cmd, shell=True)
                self.running_processes[service_id] = process

                print(f"   ✅ {service_info['name']} 시작됨")
                time.sleep(2)  # 서비스 시작 대기

            except Exception as e:
                print(f"   ❌ {service_info['name']} 시작 실패: {e}")

        print("\n🎉 모든 서비스 시작 완료!")
        print("각 서비스는 별도의 콘솔 창에서 실행 중입니다.")

        input("\n계속하려면 Enter를 누르세요...")

    def stop_all_services(self):
        """모든 서비스 중지"""
        print("\n🛑 모든 서비스 중지 중...")

        try:
            # Python 프로세스 종료
            subprocess.run(['taskkill', '/f', '/im', 'python.exe'],
                         capture_output=True)
            print("   ✅ Python 프로세스 종료됨")

            # 포트 사용 프로세스 종료
            for service_id, service_info in self.services.items():
                if service_info.get('port'):
                    port = service_info['port']
                    try:
                        # 포트 사용 프로세스 찾기
                        netstat_result = subprocess.run([
                            'netstat', '-ano'
                        ], capture_output=True, text=True)

                        for line in netstat_result.stdout.split('\n'):
                            if f':{port}' in line and 'LISTENING' in line:
                                parts = line.split()
                                if len(parts) >= 5:
                                    pid = parts[-1]
                                    subprocess.run(['taskkill', '/f', '/pid', pid],
                                                 capture_output=True)
                                    print(f"   ✅ 포트 {port} 프로세스 종료됨 (PID: {pid})")
                                    break
                    except Exception as e:
                        print(f"   ⚠️ 포트 {port} 정리 실패: {e}")

            self.running_processes.clear()
            print("\n🎉 모든 서비스 중지 완료!")

        except Exception as e:
            print(f"❌ 서비스 중지 실패: {e}")

        input("\n계속하려면 Enter를 누르세요...")

    def open_dashboards(self):
        """대시보드 열기"""
        print("\n🌐 대시보드 열기...")

        dashboards = [
            ("HTML 운영 대시보드", str(self.project_root / "results" / "production_dashboard.html")),
            ("메트릭 API", "http://localhost:8000/metrics"),
            ("헬스 체크", "http://localhost:8000/health")
        ]

        for name, url in dashboards:
            try:
                if url.startswith('http'):
                    # 웹 URL
                    subprocess.run(['start', url], shell=True)
                    print(f"   ✅ {name}: {url}")
                else:
                    # 파일 경로
                    if os.path.exists(url):
                        subprocess.run(['start', url], shell=True)
                        print(f"   ✅ {name}: 브라우저에서 열림")
                    else:
                        print(f"   ❌ {name}: 파일 없음")

                time.sleep(1)

            except Exception as e:
                print(f"   ❌ {name} 열기 실패: {e}")

        input("\n계속하려면 Enter를 누르세요...")

    def show_performance_report(self):
        """성능 리포트 표시"""
        print("\n📈 성능 리포트")

        try:
            # 최적화 계획 읽기
            plan_file = self.project_root / "results" / "optimization_plan.json"
            if plan_file.exists():
                with open(plan_file, 'r', encoding='utf-8') as f:
                    plan = json.load(f)

                print(f"\n📊 시스템 검증 결과 ({plan.get('generated_at', 'Unknown')})")
                print(f"상태: {plan.get('system_status', 'Unknown')}")

                immediate = plan.get('immediate_actions', [])
                if immediate:
                    print(f"\n🔴 즉시 조치 필요 ({len(immediate)}건):")
                    for action in immediate[:3]:
                        print(f"  • {action['description']}")

                medium = plan.get('medium_term_actions', [])
                if medium:
                    print(f"\n🟡 중기 개선 사항 ({len(medium)}건):")
                    for action in medium[:2]:
                        print(f"  • {action['description']}")

            # 모니터링 데이터
            monitoring_file = self.project_root / "results" / "monitoring.jsonl"
            if monitoring_file.exists():
                with open(monitoring_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                if lines:
                    try:
                        last_data = json.loads(lines[-1].strip())
                        system_metrics = last_data.get('system_metrics', {})

                        print(f"\n🖥️ 현재 시스템 상태:")
                        print(f"  CPU: {system_metrics.get('cpu_percent', 0):.1f}%")
                        print(f"  메모리: {system_metrics.get('memory_percent', 0):.1f}%")
                        print(f"  마지막 업데이트: {system_metrics.get('timestamp', 'Unknown')}")

                    except json.JSONDecodeError:
                        print("  모니터링 데이터 파싱 실패")

            # 배포 정보
            deployment_file = self.project_root / "results" / "deployment_report.json"
            if deployment_file.exists():
                with open(deployment_file, 'r', encoding='utf-8') as f:
                    deployment = json.load(f)

                print(f"\n🚀 배포 정보:")
                deployment_info = deployment.get('deployment_info', {})
                print(f"  버전: {deployment_info.get('version', 'Unknown')}")
                print(f"  상태: {deployment_info.get('status', 'Unknown')}")
                print(f"  배포일: {deployment_info.get('date', 'Unknown')}")

        except Exception as e:
            print(f"성능 리포트 로드 실패: {e}")

        input("\n계속하려면 Enter를 누르세요...")

    def run_system_validation(self):
        """시스템 검증 실행"""
        print("\n🔍 시스템 검증 실행 중...")

        try:
            result = subprocess.run([
                str(self.venv_python),
                "scripts/system_validation.py"
            ], cwd=self.project_root, capture_output=True, text=True)

            print("검증 결과:")
            print(result.stdout)

            if result.stderr:
                print("오류:")
                print(result.stderr)

        except Exception as e:
            print(f"시스템 검증 실행 실패: {e}")

        input("\n계속하려면 Enter를 누르세요...")

    def show_logs(self):
        """로그 확인"""
        print("\n📄 로그 확인")

        log_files = [
            ("배포 요약", "results/deployment_summary.txt"),
            ("최적화 계획", "results/optimization_plan.json"),
            ("알림 로그", "results/alert_log.jsonl"),
            ("모니터링 데이터", "results/monitoring.jsonl")
        ]

        for name, path in log_files:
            full_path = self.project_root / path
            if full_path.exists():
                size = full_path.stat().st_size
                modified = datetime.fromtimestamp(full_path.stat().st_mtime)
                print(f"  {name}: {size} bytes (수정: {modified.strftime('%Y-%m-%d %H:%M')})")
            else:
                print(f"  {name}: 파일 없음")

        print(f"\n📁 로그 디렉토리: {self.project_root / 'results'}")

        input("\n계속하려면 Enter를 누르세요...")

    def run(self):
        """메인 실행 루프"""
        while True:
            try:
                self.show_main_menu()
                choice = input("선택하세요 (0-9): ").strip()

                if choice == '0':
                    print("\n👋 Daily Trading Bot 운영 제어판을 종료합니다.")
                    break
                elif choice == '1':
                    self.check_system_status()
                elif choice == '2':
                    self.start_all_services()
                elif choice == '3':
                    self.stop_all_services()
                elif choice == '4':
                    print("개별 서비스 관리는 추후 구현 예정입니다.")
                    input("계속하려면 Enter를 누르세요...")
                elif choice == '5':
                    print("실시간 모니터링은 별도 창에서 실행해주세요:")
                    print("python scripts/performance_monitor.py")
                    input("계속하려면 Enter를 누르세요...")
                elif choice == '6':
                    self.show_performance_report()
                elif choice == '7':
                    self.run_system_validation()
                elif choice == '8':
                    self.open_dashboards()
                elif choice == '9':
                    self.show_logs()
                else:
                    print("잘못된 선택입니다. 다시 선택해주세요.")
                    time.sleep(1)

            except KeyboardInterrupt:
                print("\n\n👋 프로그램을 종료합니다.")
                break
            except Exception as e:
                print(f"\n오류 발생: {e}")
                input("계속하려면 Enter를 누르세요...")

def main():
    """메인 함수"""
    print("🚀 Daily Trading Bot 운영 제어판 시작")

    try:
        control_panel = OperationalControlPanel()
        control_panel.run()
    except Exception as e:
        print(f"제어판 실행 실패: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
