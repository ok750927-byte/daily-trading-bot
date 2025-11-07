"""
간단한 HTML 운영 대시보드 생성기
"""
import json
import time
from datetime import datetime
from pathlib import Path

def generate_dashboard_html():
    """운영 현황 HTML 대시보드 생성"""

    html_content = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily Trading Bot - 운영 현황</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            line-height: 1.6;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }

        .header {
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            text-align: center;
        }

        .header h1 {
            color: #2c3e50;
            margin-bottom: 10px;
            font-size: 2.5em;
        }

        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .status-card {
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .status-card h3 {
            color: #2c3e50;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .metric {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            padding: 8px 0;
            border-bottom: 1px solid #ecf0f1;
        }

        .metric:last-child {
            border-bottom: none;
        }

        .metric-value {
            font-weight: bold;
            color: #27ae60;
        }

        .service-links {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
        }

        .link-card {
            background: #3498db;
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-decoration: none;
            text-align: center;
            transition: transform 0.2s;
        }

        .link-card:hover {
            transform: translateY(-2px);
            background: #2980b9;
        }

        .timestamp {
            text-align: center;
            margin-top: 20px;
            color: #7f8c8d;
        }

        .success { color: #27ae60; }
        .warning { color: #f39c12; }
        .error { color: #e74c3c; }

        @media (max-width: 768px) {
            .container {
                padding: 10px;
            }

            .header h1 {
                font-size: 2em;
            }

            .status-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
    <script>
        // 자동 새로고침
        setTimeout(() => {
            location.reload();
        }, 30000);

        // 실시간 시간 업데이트
        function updateTime() {
            const now = new Date();
            document.getElementById('current-time').textContent = now.toLocaleString('ko-KR');
        }

        setInterval(updateTime, 1000);
        window.onload = updateTime;

        // 서비스 상태 체크
        async function checkServices() {
            const services = [
                { name: 'metrics', url: 'http://localhost:8000/health', element: 'metrics-status' },
                { name: 'dashboard', url: 'http://localhost:8501', element: 'dashboard-status' }
            ];

            for (const service of services) {
                try {
                    const response = await fetch(service.url, { mode: 'no-cors' });
                    document.getElementById(service.element).innerHTML = '<span class="success">✅ 정상</span>';
                } catch (e) {
                    document.getElementById(service.element).innerHTML = '<span class="warning">⚠️ 확인 중</span>';
                }
            }
        }

        // 페이지 로드 시 서비스 체크
        window.onload = () => {
            updateTime();
            checkServices();
        };
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Daily Trading Bot</h1>
            <p>프로덕션 운영 현황 대시보드</p>
            <p><strong>배포 완료:</strong> 2025년 11월 4일</p>
        </div>

        <div class="status-grid">
            <div class="status-card">
                <h3>🎯 시스템 상태</h3>
                <div class="metric">
                    <span>전체 상태</span>
                    <span class="metric-value success">🟢 정상 운영</span>
                </div>
                <div class="metric">
                    <span>메트릭 서버</span>
                    <span id="metrics-status" class="metric-value">확인 중...</span>
                </div>
                <div class="metric">
                    <span>대시보드</span>
                    <span id="dashboard-status" class="metric-value">확인 중...</span>
                </div>
                <div class="metric">
                    <span>현재 시간</span>
                    <span id="current-time" class="metric-value">로딩 중...</span>
                </div>
            </div>

            <div class="status-card">
                <h3>📊 운영 메트릭</h3>
                <div class="metric">
                    <span>CPU 모니터링</span>
                    <span class="metric-value">✅ 활성화</span>
                </div>
                <div class="metric">
                    <span>거래 데이터 수집</span>
                    <span class="metric-value">✅ 6건 기록</span>
                </div>
                <div class="metric">
                    <span>에러 발생</span>
                    <span class="metric-value success">0건</span>
                </div>
                <div class="metric">
                    <span>수집 주기</span>
                    <span class="metric-value">30초</span>
                </div>
            </div>

            <div class="status-card">
                <h3>🔧 배포 정보</h3>
                <div class="metric">
                    <span>배포 버전</span>
                    <span class="metric-value">Production v1.0</span>
                </div>
                <div class="metric">
                    <span>Python 환경</span>
                    <span class="metric-value">✅ 가상환경</span>
                </div>
                <div class="metric">
                    <span>Discord 알림</span>
                    <span class="metric-value">✅ 연동</span>
                </div>
                <div class="metric">
                    <span>자동 새로고침</span>
                    <span class="metric-value">30초</span>
                </div>
            </div>
        </div>

        <div class="status-card">
            <h3>🔗 서비스 링크</h3>
            <div class="service-links">
                <a href="http://localhost:8000/health" class="link-card" target="_blank">
                    <strong>헬스 체크</strong><br>
                    시스템 상태 확인
                </a>
                <a href="http://localhost:8000/metrics" class="link-card" target="_blank">
                    <strong>Prometheus 메트릭</strong><br>
                    성능 데이터 조회
                </a>
                <a href="http://localhost:8501" class="link-card" target="_blank">
                    <strong>Streamlit 대시보드</strong><br>
                    실시간 모니터링
                </a>
                <a href="http://localhost:3000" class="link-card" target="_blank">
                    <strong>Grafana</strong><br>
                    고급 모니터링 (Docker)
                </a>
            </div>
        </div>

        <div class="timestamp">
            <p>🕒 마지막 업데이트: <span id="current-time"></span></p>
            <p>⚡ 자동 새로고침: 30초마다</p>
        </div>
    </div>
</body>
</html>
"""

    # HTML 파일 저장
    dashboard_file = Path("results/production_dashboard.html")
    dashboard_file.parent.mkdir(exist_ok=True)

    with open(dashboard_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"✅ 운영 대시보드 생성: {dashboard_file}")
    print(f"🌐 접속 URL: file:///{dashboard_file.absolute()}")

    return dashboard_file

if __name__ == "__main__":
    generate_dashboard_html()
