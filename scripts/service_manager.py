"""
시스템 서비스 관리 스크립트
거래봇과 모니터링 시스템을 Windows 서비스로 등록/관리
"""
import os
import sys
import subprocess
import json
import time
from pathlib import Path
import logging
from typing import List, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ServiceManager:
    """Windows 서비스 관리자"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.venv_python = self.project_root / "venv314" / "Scripts" / "python.exe"
        
        # 서비스 정의
        self.services = {
            "trading-engine": {
                "display_name": "Daily Trading Bot Engine",
                "description": "AI 기반 자동 주식 거래 엔진",
                "script": "src/trading/realtime_engine.py",
                "dependencies": []
            },
            "metrics-server": {
                "display_name": "Trading Bot Metrics Server", 
                "description": "거래봇 메트릭 수집 및 HTTP 서버",
                "script": "scripts/metrics_server.py",
                "dependencies": []
            },
            "dashboard": {
                "display_name": "Trading Bot Dashboard",
                "description": "거래봇 실시간 대시보드",
                "script": "scripts/dashboard_realtime.py",
                "dependencies": ["trading-engine"]
            }
        }
    
    def create_service_wrapper(self, service_name: str) -> Path:
        """서비스 래퍼 스크립트 생성"""
        service_config = self.services[service_name]
        
        wrapper_content = f'''"""
{service_config["display_name"]} 서비스 래퍼
"""
import os
import sys
import time
import logging
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

# 로깅 설정
log_dir = project_root / "logs"
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "{service_name}.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("{service_name}")

def main():
    """메인 실행 함수"""
    try:
        logger.info("{service_config['display_name']} 서비스 시작")
        
        # 작업 디렉토리를 프로젝트 루트로 설정
        os.chdir(project_root)
        
        # 실제 스크립트 실행
        if "{service_name}" == "trading-engine":
            from src.trading.realtime_engine import RealTimeTradingEngine
            engine = RealTimeTradingEngine()
            engine.start_trading()
            
        elif "{service_name}" == "metrics-server":
            from scripts.metrics_server import main as metrics_main
            metrics_main()
            
        elif "{service_name}" == "dashboard":
            import subprocess
            import streamlit.web.cli as stcli
            sys.argv = ["streamlit", "run", "scripts/dashboard_realtime.py", 
                       "--server.port", "8501", "--server.address", "0.0.0.0"]
            stcli.main()
        
    except Exception as e:
        logger.error(f"서비스 실행 중 오류: {{e}}")
        raise
    except KeyboardInterrupt:
        logger.info("서비스 중지 신호 받음")
    finally:
        logger.info("{service_config['display_name']} 서비스 종료")

if __name__ == "__main__":
    main()
'''
        
        wrapper_file = self.project_root / "services" / f"{service_name}_service.py"
        wrapper_file.parent.mkdir(exist_ok=True)
        
        with open(wrapper_file, 'w', encoding='utf-8') as f:
            f.write(wrapper_content)
        
        logger.info(f"서비스 래퍼 생성: {wrapper_file}")
        return wrapper_file
    
    def create_batch_scripts(self):
        """배치 스크립트 생성"""
        scripts_dir = self.project_root / "scripts" / "service_scripts"
        scripts_dir.mkdir(exist_ok=True)
        
        # 전체 시작 스크립트
        start_all_content = '''@echo off
echo ================================
echo Daily Trading Bot 서비스 시작
echo ================================

echo 1. 거래 엔진 시작...
start "Trading Engine" cmd /k "cd /d "{}" && "{}" services/trading-engine_service.py"

timeout /t 5

echo 2. 메트릭 서버 시작...
start "Metrics Server" cmd /k "cd /d "{}" && "{}" services/metrics-server_service.py"

timeout /t 3

echo 3. 대시보드 시작...
start "Dashboard" cmd /k "cd /d "{}" && "{}" services/dashboard_service.py"

echo.
echo 모든 서비스가 시작되었습니다.
echo - 거래 엔진: 백그라운드 실행
echo - 메트릭 서버: http://localhost:8000
echo - 대시보드: http://localhost:8501
echo.
pause
'''.format(
            self.project_root, self.venv_python,
            self.project_root, self.venv_python,
            self.project_root, self.venv_python
        )
        
        start_all_file = scripts_dir / "start_all_services.bat"
        with open(start_all_file, 'w', encoding='utf-8') as f:
            f.write(start_all_content)
        
        # 서비스 상태 확인 스크립트
        status_content = '''@echo off
echo ================================
echo Daily Trading Bot 서비스 상태
echo ================================

echo 거래 엔진 로그 (최근 10줄):
type "{}\\logs\\trading-engine.log" | find /v "" | more +0 2>nul
if errorlevel 1 echo [로그 파일 없음]

echo.
echo 메트릭 서버 상태 확인:
curl -s http://localhost:8000/health 2>nul
if errorlevel 1 echo [메트릭 서버 연결 실패]

echo.
echo 대시보드 상태 확인:
curl -s http://localhost:8501 2>nul | find "Streamlit" >nul
if errorlevel 1 (
    echo [대시보드 연결 실패]
) else (
    echo [대시보드 정상 실행 중]
)

echo.
pause
'''.format(self.project_root)
        
        status_file = scripts_dir / "check_services.bat"
        with open(status_file, 'w', encoding='utf-8') as f:
            f.write(status_content)
        
        # 서비스 중지 스크립트  
        stop_content = '''@echo off
echo ================================
echo Daily Trading Bot 서비스 중지
echo ================================

echo Python 프로세스 확인 및 종료...
taskkill /f /im python.exe 2>nul
taskkill /f /im streamlit.exe 2>nul

echo 포트 사용 프로세스 확인...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8000" ^| find "LISTENING"') do (
    echo 포트 8000 프로세스 (PID: %%a) 종료 중...
    taskkill /f /pid %%a 2>nul
)

for /f "tokens=5" %%a in ('netstat -aon ^| find ":8501" ^| find "LISTENING"') do (
    echo 포트 8501 프로세스 (PID: %%a) 종료 중...
    taskkill /f /pid %%a 2>nul
)

echo.
echo 모든 서비스가 중지되었습니다.
pause
'''
        
        stop_file = scripts_dir / "stop_all_services.bat"
        with open(stop_file, 'w', encoding='utf-8') as f:
            f.write(stop_content)
        
        logger.info(f"배치 스크립트 생성 완료:")
        logger.info(f"  - 시작: {start_all_file}")
        logger.info(f"  - 상태: {status_file}")
        logger.info(f"  - 중지: {stop_file}")
        
        return {
            'start': start_all_file,
            'status': status_file,
            'stop': stop_file
        }
    
    def create_scheduled_task_xml(self, service_name: str) -> Path:
        """Windows 작업 스케줄러용 XML 생성"""
        service_config = self.services[service_name]
        wrapper_file = self.project_root / "services" / f"{service_name}_service.py"
        
        task_xml = f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Date>{time.strftime("%Y-%m-%dT%H:%M:%S")}</Date>
    <Author>Daily Trading Bot</Author>
    <Description>{service_config["description"]}</Description>
  </RegistrationInfo>
  <Triggers>
    <BootTrigger>
      <Enabled>true</Enabled>
    </BootTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>{os.getlogin()}</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>false</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{self.venv_python}</Command>
      <Arguments>"{wrapper_file}"</Arguments>
      <WorkingDirectory>{self.project_root}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>'''
        
        task_file = self.project_root / "services" / f"{service_name}_task.xml"
        with open(task_file, 'w', encoding='utf-16') as f:
            f.write(task_xml)
        
        logger.info(f"작업 스케줄러 XML 생성: {task_file}")
        return task_file
    
    def install_service(self, service_name: str):
        """서비스 설치 (작업 스케줄러 사용)"""
        try:
            # 래퍼 스크립트 생성
            wrapper_file = self.create_service_wrapper(service_name)
            
            # 작업 스케줄러 XML 생성
            task_file = self.create_scheduled_task_xml(service_name)
            
            # 작업 스케줄러에 등록
            task_name = f"DailyTradingBot_{service_name}"
            cmd = [
                "schtasks", "/create",
                "/tn", task_name,
                "/xml", str(task_file),
                "/f"  # 덮어쓰기
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"서비스 설치 완료: {service_name}")
                return True
            else:
                logger.error(f"서비스 설치 실패: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"서비스 설치 중 오류: {e}")
            return False
    
    def uninstall_service(self, service_name: str):
        """서비스 제거"""
        try:
            task_name = f"DailyTradingBot_{service_name}"
            cmd = ["schtasks", "/delete", "/tn", task_name, "/f"]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"서비스 제거 완료: {service_name}")
                return True
            else:
                logger.error(f"서비스 제거 실패: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"서비스 제거 중 오류: {e}")
            return False
    
    def start_service(self, service_name: str):
        """서비스 시작"""
        try:
            task_name = f"DailyTradingBot_{service_name}"
            cmd = ["schtasks", "/run", "/tn", task_name]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"서비스 시작: {service_name}")
                return True
            else:
                logger.error(f"서비스 시작 실패: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"서비스 시작 중 오류: {e}")
            return False
    
    def stop_service(self, service_name: str):
        """서비스 중지"""
        try:
            task_name = f"DailyTradingBot_{service_name}"
            cmd = ["schtasks", "/end", "/tn", task_name]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"서비스 중지: {service_name}")
                return True
            else:
                logger.error(f"서비스 중지 실패: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"서비스 중지 중 오류: {e}")
            return False

def main():
    """메인 함수"""
    manager = ServiceManager()
    
    if len(sys.argv) < 2:
        print("사용법:")
        print("  python service_manager.py install [service_name]")
        print("  python service_manager.py uninstall [service_name]") 
        print("  python service_manager.py start [service_name]")
        print("  python service_manager.py stop [service_name]")
        print("  python service_manager.py create_scripts")
        print()
        print("사용 가능한 서비스:")
        for name, config in manager.services.items():
            print(f"  - {name}: {config['display_name']}")
        return
    
    action = sys.argv[1]
    
    if action == "create_scripts":
        scripts = manager.create_batch_scripts()
        print("배치 스크립트가 생성되었습니다:")
        for script_type, path in scripts.items():
            print(f"  {script_type}: {path}")
        return
    
    if len(sys.argv) < 3:
        print("서비스 이름을 지정해주세요.")
        return
    
    service_name = sys.argv[2]
    
    if service_name not in manager.services:
        print(f"알 수 없는 서비스: {service_name}")
        print("사용 가능한 서비스:")
        for name in manager.services.keys():
            print(f"  - {name}")
        return
    
    if action == "install":
        manager.install_service(service_name)
    elif action == "uninstall":
        manager.uninstall_service(service_name)
    elif action == "start":
        manager.start_service(service_name)
    elif action == "stop":
        manager.stop_service(service_name)
    else:
        print(f"알 수 없는 액션: {action}")

if __name__ == "__main__":
    main()