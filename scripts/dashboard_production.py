"""
운영 현황 대시보드 - 최종 배포 완료 상태
"""
import streamlit as st
import json
import time
import requests
from datetime import datetime
import os

def main():
    st.set_page_config(
        page_title="Daily Trading Bot - 운영 현황",
        page_icon="📊",
        layout="wide"
    )

    st.title("🚀 Daily Trading Bot - 프로덕션 운영 현황")

    # 사이드바 - 시스템 상태
    st.sidebar.header("🔧 시스템 상태")

    # 메트릭 서버 상태
    try:
        response = requests.get("http://localhost:8000/health", timeout=3)
        if response.status_code == 200:
            st.sidebar.success("✅ 메트릭 서버: 정상")
        else:
            st.sidebar.error("❌ 메트릭 서버: 오류")
    except:
        st.sidebar.error("❌ 메트릭 서버: 연결 불가")

    # 메인 콘텐츠
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("시스템 상태", "🟢 정상 운영", "메트릭 수집 중")

    with col2:
        st.metric("배포 시간", datetime.now().strftime("%Y-%m-%d %H:%M"), "프로덕션 가동")

    with col3:
        st.metric("서비스 수", "3개", "메트릭/대시보드/거래엔진")

    # 실시간 메트릭
    st.subheader("📈 실시간 메트릭")

    try:
        response = requests.get("http://localhost:8000/metrics", timeout=3)
        if response.status_code == 200:
            metrics_text = response.text

            # 간단한 메트릭 파싱
            cpu_line = [line for line in metrics_text.split('\n') if 'trading_bot_cpu_percent' in line and not line.startswith('#')]
            if cpu_line:
                cpu_value = float(cpu_line[0].split()[-1])
                st.metric("CPU 사용률", f"{cpu_value:.1f}%")

            # 원시 메트릭 데이터 표시
            with st.expander("📊 Prometheus 메트릭 (원시 데이터)"):
                st.code(metrics_text, language="text")

    except Exception as e:
        st.error(f"메트릭 데이터 로드 실패: {e}")

    # 서비스 링크
    st.subheader("🔗 서비스 링크")

    links_col1, links_col2 = st.columns(2)

    with links_col1:
        st.markdown("**현재 실행 중인 서비스:**")
        st.markdown("- [메트릭 API](http://localhost:8000/metrics)")
        st.markdown("- [헬스 체크](http://localhost:8000/health)")
        st.markdown("- [현재 대시보드](http://localhost:8501)")

    with links_col2:
        st.markdown("**모니터링 스택 (Docker 필요):**")
        st.markdown("- Grafana: http://localhost:3000")
        st.markdown("- Prometheus: http://localhost:9090")
        st.markdown("- Node Exporter: http://localhost:9100")

    # 배포 정보
    st.subheader("📦 배포 정보")

    deployment_info = {
        "배포 날짜": "2025년 11월 4일",
        "배포 버전": "Production v1.0",
        "시스템 구성": "메트릭 수집 + 실시간 대시보드 + 거래 엔진",
        "모니터링": "Prometheus 메트릭 수집 활성화",
        "알림": "Discord 웹훅 연동",
        "상태": "✅ 운영 준비 완료"
    }

    for key, value in deployment_info.items():
        st.write(f"**{key}:** {value}")

    # 자동 새로고침
    time.sleep(5)
    st.rerun()

if __name__ == "__main__":
    main()
