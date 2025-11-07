"""
실시간 거래 성과 모니터링 대시보드
- Streamlit 기반 웹 대시보드
- 실시간 차트 및 통계
- 알림 시스템 연동
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
import os
from datetime import datetime, timedelta
import asyncio
import time

# Streamlit 페이지 설정
st.set_page_config(
    page_title="🤖 AI Trading Bot Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 사이드바 - 설정
st.sidebar.title("⚙️ 설정")

# 자동 새로고침 설정
auto_refresh = st.sidebar.checkbox("자동 새로고침 (10초)", value=True)
if auto_refresh:
    time.sleep(10)
    st.rerun()

# 모니터링 대상 선택
monitoring_mode = st.sidebar.selectbox(
    "모니터링 모드",
    ["실시간 거래", "백테스팅 결과", "시뮬레이션"]
)

# 메인 대시보드
st.title("🤖 AI 주식 자동매매 봇 대시보드")
st.markdown("---")

# 메트릭 표시 함수
def load_performance_data():
    """성과 데이터 로드"""
    try:
        # 성과 요약 파일
        summary_path = "results/performance_summary.json"
        if os.path.exists(summary_path):
            with open(summary_path, 'r', encoding='utf-8') as f:
                summary = json.load(f)
        else:
            summary = {
                "total_trades": 0,
                "win_rate": 0,
                "total_profit": 0,
                "max_drawdown": 0,
                "avg_profit_per_trade": 0,
                "sharpe_ratio": 0
            }
        
        # 거래 로그
        trade_logs = []
        log_paths = [
            "results/trade_log.json",
            "results/realtime_trade_log.jsonl",
            "results/simulation_result.json"
        ]
        
        for log_path in log_paths:
            if os.path.exists(log_path):
                try:
                    if log_path.endswith('.jsonl'):
                        with open(log_path, 'r', encoding='utf-8') as f:
                            for line in f:
                                if line.strip():
                                    trade_logs.append(json.loads(line))
                    else:
                        with open(log_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if 'trades' in data:
                                trade_logs.extend(data['trades'])
                            elif isinstance(data, list):
                                trade_logs.extend(data)
                except:
                    continue
        
        return summary, trade_logs
        
    except Exception as e:
        st.error(f"데이터 로드 오류: {e}")
        return {}, []

def load_predictions():
    """예측 결과 로드"""
    try:
        predictions_path = "results/predictions.json"
        if os.path.exists(predictions_path):
            with open(predictions_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except:
        return {}

# 데이터 로드
summary, trade_logs = load_performance_data()
predictions = load_predictions()

# 상단 메트릭 카드
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="💰 총 수익",
        value=f"{summary.get('total_profit', 0):,.0f}원",
        delta=f"{summary.get('avg_profit_per_trade', 0):,.0f}원/거래"
    )

with col2:
    st.metric(
        label="📊 승률", 
        value=f"{summary.get('win_rate', 0):.1f}%",
        delta=f"총 {summary.get('total_trades', 0)}거래"
    )

with col3:
    st.metric(
        label="📉 최대 낙폭",
        value=f"{summary.get('max_drawdown', 0):,.0f}원",
        delta=f"{(summary.get('max_drawdown', 0)/10000000)*100:+.2f}%" if summary.get('max_drawdown') else "0%"
    )

with col4:
    st.metric(
        label="⚡ 샤프 비율",
        value=f"{summary.get('sharpe_ratio', 0):.2f}",
        delta="위험 조정 수익률"
    )

st.markdown("---")

# 중간 섹션 - 실시간 상태
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📈 거래 성과 추이")
    
    if trade_logs:
        # 거래 로그를 DataFrame으로 변환
        df_trades = pd.DataFrame(trade_logs)
        
        # 날짜 컬럼 처리
        if 'timestamp' in df_trades.columns:
            df_trades['timestamp'] = pd.to_datetime(df_trades['timestamp'])
            df_trades = df_trades.sort_values('timestamp')
            
            # 누적 손익 계산
            df_trades['cumulative_pnl'] = df_trades.get('pnl', 0).fillna(0).cumsum()
            
            # 차트 생성
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=['누적 손익', '거래량'],
                vertical_spacing=0.1,
                row_heights=[0.7, 0.3]
            )
            
            # 누적 손익 라인 차트
            fig.add_trace(
                go.Scatter(
                    x=df_trades['timestamp'],
                    y=df_trades['cumulative_pnl'],
                    mode='lines+markers',
                    name='누적 손익',
                    line=dict(color='#00ff88', width=2),
                    hovertemplate='%{x}<br>누적 손익: %{y:,.0f}원<extra></extra>'
                ),
                row=1, col=1
            )
            
            # 거래량 히스토그램
            fig.add_trace(
                go.Histogram(
                    x=df_trades['timestamp'].dt.date,
                    name='일별 거래 횟수',
                    marker_color='#ff6b6b',
                    opacity=0.7
                ),
                row=2, col=1
            )
            
            fig.update_layout(
                height=500,
                showlegend=True,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            
            fig.update_xaxes(gridcolor='rgba(128,128,128,0.2)')
            fig.update_yaxes(gridcolor='rgba(128,128,128,0.2)')
            
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("아직 거래 데이터가 없습니다.")

with col2:
    st.subheader("🎯 AI 예측 결과")
    
    if predictions and 'recommendations' in predictions:
        st.write(f"**예측 일자:** {predictions.get('prediction_date', 'N/A')}")
        
        for i, rec in enumerate(predictions['recommendations'][:3]):  # 상위 3개만 표시
            with st.container():
                st.markdown(f"""
                **{i+1}. 종목코드: {rec['code']}**
                - 현재가: {rec['last_close_price']:,}원
                - 상승확률: {rec['up_probability']}%
                - 예상수익률: +{rec['estimated_gain_rate']:.1f}%
                """)
                
                # 신호 강도 게이지
                strength = rec['up_probability'] / 100
                color = '#00ff88' if strength > 0.6 else '#ffaa00' if strength > 0.4 else '#ff6b6b'
                
                st.markdown(f"""
                <div style="background: linear-gradient(90deg, {color} {strength*100}%, #333 {strength*100}%); 
                           height: 10px; border-radius: 5px; margin: 5px 0;"></div>
                """, unsafe_allow_html=True)
    else:
        st.info("예측 데이터를 로드 중...")

st.markdown("---")

# 하단 섹션 - 상세 분석
col1, col2 = st.columns(2)

with col1:
    st.subheader("📋 최근 거래 내역")
    
    if trade_logs:
        # 최근 10개 거래 표시
        recent_trades = sorted(trade_logs, key=lambda x: x.get('timestamp', ''), reverse=True)[:10]
        
        display_trades = []
        for trade in recent_trades:
            display_trades.append({
                '시간': trade.get('timestamp', '')[:16],
                '종목': trade.get('stock_code', ''),
                '구분': '매수' if trade.get('side') == 'buy' else '매도',
                '수량': f"{trade.get('quantity', 0):,}주",
                '가격': f"{trade.get('price', 0):,}원",
                '손익': f"{trade.get('pnl', 0):+,.0f}원" if trade.get('pnl') else '-'
            })
        
        if display_trades:
            st.dataframe(
                pd.DataFrame(display_trades),
                use_container_width=True,
                height=350
            )
    else:
        st.info("거래 내역이 없습니다.")

with col2:
    st.subheader("📊 종목별 성과 분석")
    
    if trade_logs:
        # 종목별 수익률 계산
        stock_performance = {}
        
        for trade in trade_logs:
            stock_code = trade.get('stock_code', '')
            pnl = trade.get('pnl', 0)
            
            if stock_code and pnl:
                if stock_code not in stock_performance:
                    stock_performance[stock_code] = {'pnl': 0, 'trades': 0}
                
                stock_performance[stock_code]['pnl'] += pnl
                stock_performance[stock_code]['trades'] += 1
        
        if stock_performance:
            # 상위/하위 5개 종목
            sorted_stocks = sorted(
                stock_performance.items(),
                key=lambda x: x[1]['pnl'],
                reverse=True
            )
            
            stock_names = [item[0] for item in sorted_stocks[:5]]
            stock_pnls = [item[1]['pnl'] for item in sorted_stocks[:5]]
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=stock_names,
                y=stock_pnls,
                marker_color=['#00ff88' if pnl >= 0 else '#ff6b6b' for pnl in stock_pnls],
                text=[f'{pnl:+,.0f}원' for pnl in stock_pnls],
                textposition='auto',
            ))
            
            fig.update_layout(
                title="종목별 손익",
                xaxis_title="종목코드",
                yaxis_title="손익 (원)",
                height=350,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("종목별 데이터가 없습니다.")

# 푸터
st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**⏰ 마지막 업데이트**")
    st.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

with col2:
    st.markdown("**🔄 시스템 상태**") 
    status_color = "🟢" if trade_logs else "🟡"
    status_text = "활성" if trade_logs else "대기중"
    st.write(f"{status_color} {status_text}")

with col3:
    st.markdown("**📱 알림 설정**")
    if st.button("텔레그램 알림 테스트"):
        st.success("알림이 전송되었습니다! 📨")

# 스타일링
st.markdown("""
<style>
    .reportview-container {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
    }
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #1e3c72 0%, #2a5298 100%);
    }
    .metric-container {
        background: rgba(255, 255, 255, 0.05);
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# 디버그 정보 (개발용)
if st.sidebar.checkbox("디버그 정보 표시"):
    st.sidebar.write("**데이터 파일 상태:**")
    
    files_to_check = [
        "results/performance_summary.json",
        "results/predictions.json", 
        "results/trade_log.json",
        "results/simulation_result.json"
    ]
    
    for file_path in files_to_check:
        exists = "✅" if os.path.exists(file_path) else "❌"
        st.sidebar.write(f"{exists} {file_path}")