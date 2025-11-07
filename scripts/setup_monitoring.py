"""
Prometheus + Grafana 설정 및 관리
"""
import os
import yaml
import requests
import json
import time
from pathlib import Path

class MonitoringSetup:
    """모니터링 시스템 설정"""

    def __init__(self):
        self.config_dir = Path("monitoring")
        self.config_dir.mkdir(exist_ok=True)

    def create_prometheus_config(self):
        """Prometheus 설정 파일 생성"""
        config = {
            'global': {
                'scrape_interval': '15s',
                'evaluation_interval': '15s'
            },
            'rule_files': [],
            'scrape_configs': [
                {
                    'job_name': 'trading-bot',
                    'static_configs': [
                        {
                            'targets': ['localhost:8000']  # 메트릭 엔드포인트
                        }
                    ],
                    'scrape_interval': '5s',
                    'metrics_path': '/metrics'
                },
                {
                    'job_name': 'node-exporter',
                    'static_configs': [
                        {
                            'targets': ['localhost:9100']
                        }
                    ]
                }
            ],
            'alerting': {
                'alertmanagers': [
                    {
                        'static_configs': [
                            {
                                'targets': ['localhost:9093']
                            }
                        ]
                    }
                ]
            }
        }

        config_file = self.config_dir / "prometheus.yml"
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

        print(f"Prometheus 설정 파일 생성: {config_file}")
        return config_file

    def create_grafana_dashboard(self):
        """Grafana 대시보드 JSON 생성"""
        dashboard = {
            "dashboard": {
                "id": None,
                "title": "Daily Trading Bot Monitor",
                "tags": ["trading", "bot", "automated"],
                "timezone": "Asia/Seoul",
                "refresh": "5s",
                "time": {
                    "from": "now-1h",
                    "to": "now"
                },
                "panels": [
                    {
                        "id": 1,
                        "title": "시스템 리소스",
                        "type": "graph",
                        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
                        "targets": [
                            {
                                "expr": "trading_bot_cpu_percent",
                                "legendFormat": "CPU (%)",
                                "refId": "A"
                            },
                            {
                                "expr": "trading_bot_memory_percent",
                                "legendFormat": "Memory (%)",
                                "refId": "B"
                            }
                        ],
                        "yAxes": [
                            {"min": 0, "max": 100, "unit": "percent"},
                            {"min": 0, "max": 100, "unit": "percent"}
                        ]
                    },
                    {
                        "id": 2,
                        "title": "거래 성과",
                        "type": "stat",
                        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
                        "targets": [
                            {
                                "expr": "trading_bot_total_profit",
                                "legendFormat": "총 손익",
                                "refId": "A"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "krw",
                                "color": {
                                    "mode": "thresholds"
                                },
                                "thresholds": {
                                    "steps": [
                                        {"color": "red", "value": None},
                                        {"color": "yellow", "value": 0},
                                        {"color": "green", "value": 100000}
                                    ]
                                }
                            }
                        }
                    },
                    {
                        "id": 3,
                        "title": "거래 통계",
                        "type": "table",
                        "gridPos": {"h": 8, "w": 24, "x": 0, "y": 8},
                        "targets": [
                            {
                                "expr": "trading_bot_total_trades",
                                "legendFormat": "총 거래수",
                                "refId": "A"
                            },
                            {
                                "expr": "trading_bot_win_rate",
                                "legendFormat": "승률 (%)",
                                "refId": "B"
                            }
                        ]
                    },
                    {
                        "id": 4,
                        "title": "에러 모니터링",
                        "type": "graph",
                        "gridPos": {"h": 8, "w": 24, "x": 0, "y": 16},
                        "targets": [
                            {
                                "expr": "rate(trading_bot_total_errors[5m])",
                                "legendFormat": "에러 발생률",
                                "refId": "A"
                            }
                        ],
                        "alert": {
                            "conditions": [
                                {
                                    "evaluator": {
                                        "params": [5],
                                        "type": "gt"
                                    },
                                    "operator": {
                                        "type": "and"
                                    },
                                    "query": {
                                        "params": ["A", "5m", "now"]
                                    },
                                    "reducer": {
                                        "type": "avg"
                                    },
                                    "type": "query"
                                }
                            ],
                            "executionErrorState": "alerting",
                            "for": "5m",
                            "frequency": "10s",
                            "handler": 1,
                            "name": "High Error Rate",
                            "noDataState": "no_data",
                            "notifications": []
                        }
                    }
                ]
            },
            "overwrite": True
        }

        dashboard_file = self.config_dir / "trading_dashboard.json"
        with open(dashboard_file, 'w', encoding='utf-8') as f:
            json.dump(dashboard, f, ensure_ascii=False, indent=2)

        print(f"Grafana 대시보드 생성: {dashboard_file}")
        return dashboard_file

    def create_docker_monitoring_compose(self):
        """모니터링 서비스 Docker Compose 파일"""
        compose = {
            'version': '3.8',
            'services': {
                'prometheus': {
                    'image': 'prom/prometheus:latest',
                    'container_name': 'prometheus',
                    'ports': ['9090:9090'],
                    'volumes': [
                        './monitoring/prometheus.yml:/etc/prometheus/prometheus.yml'
                    ],
                    'command': [
                        '--config.file=/etc/prometheus/prometheus.yml',
                        '--storage.tsdb.path=/prometheus',
                        '--web.console.libraries=/etc/prometheus/console_libraries',
                        '--web.console.templates=/etc/prometheus/consoles',
                        '--storage.tsdb.retention.time=200h',
                        '--web.enable-lifecycle'
                    ],
                    'restart': 'unless-stopped'
                },
                'grafana': {
                    'image': 'grafana/grafana:latest',
                    'container_name': 'grafana',
                    'ports': ['3000:3000'],
                    'environment': {
                        # Do not hardcode passwords in source. Read from environment at runtime.
                        'GF_SECURITY_ADMIN_PASSWORD': os.environ.get('GF_SECURITY_ADMIN_PASSWORD', 'changeme')
                    },
                    'volumes': [
                        'grafana-storage:/var/lib/grafana'
                    ],
                    'restart': 'unless-stopped'
                },
                'node-exporter': {
                    'image': 'prom/node-exporter:latest',
                    'container_name': 'node-exporter',
                    'ports': ['9100:9100'],
                    'restart': 'unless-stopped'
                }
            },
            'volumes': {
                'grafana-storage': {}
            }
        }

        compose_file = self.config_dir / "docker-compose.monitoring.yml"
        with open(compose_file, 'w', encoding='utf-8') as f:
            yaml.dump(compose, f, default_flow_style=False)

        print(f"모니터링 Docker Compose 파일 생성: {compose_file}")
        return compose_file

    def setup_grafana_datasource(self, grafana_url="http://localhost:3000",
                                admin_user="admin", admin_password=None):
        """Grafana 데이터소스 설정"""
        try:
            # Avoid hardcoded credentials: allow caller to pass admin_password or
            # read from environment variable GF_SECURITY_ADMIN_PASSWORD at runtime.
            if admin_password is None:
                admin_password = os.environ.get('GF_SECURITY_ADMIN_PASSWORD', 'changeme')
            # Grafana API를 통한 데이터소스 추가
            datasource_config = {
                "name": "Prometheus",
                "type": "prometheus",
                "url": "http://prometheus:9090",
                "access": "proxy",
                "isDefault": True
            }

            response = requests.post(
                f"{grafana_url}/api/datasources",
                json=datasource_config,
                auth=(admin_user, admin_password),
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code in [200, 409]:  # 200: 성공, 409: 이미 존재
                print("Grafana 데이터소스 설정 완료")
                return True
            else:
                print(f"데이터소스 설정 실패: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"Grafana 데이터소스 설정 중 오류: {e}")
            return False

    def import_dashboard(self, grafana_url="http://localhost:3000",
                        admin_user="admin", admin_password=None):
        """대시보드 임포트"""
        try:
            if admin_password is None:
                admin_password = os.environ.get('GF_SECURITY_ADMIN_PASSWORD', 'changeme')
            dashboard_file = self.config_dir / "trading_dashboard.json"
            if not dashboard_file.exists():
                print("대시보드 파일이 없습니다. 먼저 create_grafana_dashboard()를 실행하세요.")
                return False

            with open(dashboard_file, 'r', encoding='utf-8') as f:
                dashboard_json = json.load(f)

            response = requests.post(
                f"{grafana_url}/api/dashboards/db",
                json=dashboard_json,
                auth=(admin_user, admin_password),
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code == 200:
                print("Grafana 대시보드 임포트 완료")
                return True
            else:
                print(f"대시보드 임포트 실패: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"대시보드 임포트 중 오류: {e}")
            return False

def setup_monitoring():
    """전체 모니터링 시스템 설정"""
    setup = MonitoringSetup()

    print("=== 모니터링 시스템 설정 시작 ===")

    # 1. 설정 파일들 생성
    setup.create_prometheus_config()
    setup.create_grafana_dashboard()
    setup.create_docker_monitoring_compose()

    print("\n=== Docker Compose로 모니터링 서비스 시작 ===")
    print("다음 명령어를 실행하세요:")
    print("cd monitoring")
    print("docker-compose -f docker-compose.monitoring.yml up -d")

    print("\n=== 서비스 접근 정보 ===")
    print("- Prometheus: http://localhost:9090")
    print("- Grafana: http://localhost:3000 (admin/admin123)")
    print("- Node Exporter: http://localhost:9100")

    print("\n=== Grafana 설정 (Docker 시작 후 실행) ===")
    print("setup.setup_grafana_datasource()")
    print("setup.import_dashboard()")

if __name__ == "__main__":
    setup_monitoring()
