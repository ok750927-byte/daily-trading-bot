"""Simple Streamlit dashboard to visualize approvals and audit log.

Run:
    streamlit run scripts/dashboard_streamlit.py

This displays pending approvals and a tail of the audit log.
"""
from pathlib import Path
import streamlit as st
import json
import time

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'results' / 'approval_audit.jsonl'
QUEUE = ROOT / 'results' / 'approval_queue.jsonl'

st.set_page_config(page_title='Daily Trading Bot Dashboard')
st.title('Daily Trading Bot — 운영 대시보드')

st.markdown('### Pending Approvals')

@st.cache_data(ttl=1)
def _read_queue():
    items = []
    if QUEUE.exists():
        for line in QUEUE.read_text(encoding='utf-8').splitlines():
            try:
                items.append(json.loads(line))
            except Exception:
                continue
    return items

@st.cache_data(ttl=1)
def _read_audit(n=200):
    lines = []
    if AUDIT.exists():
        raw = AUDIT.read_text(encoding='utf-8').splitlines()
        for line in raw[-n:]:
            try:
                lines.append(json.loads(line))
            except Exception:
                continue
    return lines

pending = _read_queue()
if not pending:
    st.info('현재 대기중인 승인 요청이 없습니다.')
else:
    for p in pending:
        sig = p.get('signal', {})
        cols = st.columns([1,2,1,1])
        cols[0].write(p.get('id'))
        cols[1].write(f"{sig.get('symbol')} {sig.get('qty')} @ {sig.get('price')}")
        cols[2].write(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(p.get('timestamp',0))))
        cols[3].write(p.get('status'))

st.markdown('---')
st.markdown('### Audit (recent)')
for a in _read_audit(200):
    st.json(a)

st.markdown('---')
st.write('자동 새로고침: 페이지를 새로고침하거나, 브라우저에서 Streamlit의 "R" 버튼을 누르세요.')
