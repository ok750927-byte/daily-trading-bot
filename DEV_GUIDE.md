Developer Guide — 운영자 승인(Operator Approval) 및 테스트
======================================================

목적
----
이 가이드는 개발자와 운영자가 `ApprovalManager` 기반의 운영자 승인 워크플로우를 이해하고 로컬에서 테스트/운영하는 방법을 제공합니다.

핵심 컴포넌트
----------------
- `src/trading/approval.py` — 통합 ApprovalManager 구현
  - API: `submit(payload) -> approval_id`, `list_pending()`, `check_approval(id)`, `approve(id, approver=...)`, `reject(id, operator=...)`, `register_handler(fn)`
  - 파일: `results/pending_approvals.jsonl`(대기), `results/approval_audit.jsonl`(감사), `results/approval_queue.jsonl`
- GUI: `src/gui/trading_dashboard.py` — 승인 대기창(자동 새로고침, 상세뷰, 승인/거부)
- 실시간 엔진: `src/trading/realtime_trader.py` & `src/trading/live_trading_engine.py` — 승인 요청 제출 및 승인 핸들러 등록

운영자 승인 동작 계약(Contract)
-----------------------------
- 입력: 승인 요청(주문/시그널) — dict 형태 (예: `{'symbol':'005930', 'qty':1, 'price':70000, 'side':'buy'}`)
- 출력/효과:
  - submit -> `approval_id` 반환
  - 승인 시(approve): audit 파일에 감사 로그가 기록되고, 등록된 핸들러가 즉시(동기 호출 우선) 실행되어 주문을 전송합니다.
  - 거부 시(reject): 감사 로그에 기록되고, 대기 큐에서 제거됩니다.
- 오류 모드: 파일 쓰기 실패, 핸들러 예외 등은 내부에서 흡수(log)되며, 가능한 경우 UI에 경고를 띄웁니다.

테스트 및 로컬 검증
--------------------
1. 가상환경 준비

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. 단위/통합 테스트 실행

```powershell
python -m pytest -q
```

3. 수동 흐름 확인(간단)

```powershell
python -c "from src.trading.approval import manager; id=manager.submit({'symbol':'005930','qty':1}); print('id',id); print('pending', manager.list_pending()); manager.approve(id, operator='me');"
```

4. GUI로 승인/거부 확인

- `python run_gui.py` 실행 후 대시보드 → 실시간 트레이딩 → 승인 대기

CI 연동 제안
---------------
- `tests/`에 추가한 테스트들을 GitHub Actions에서 실행하도록 워크플로우를 설정하세요.
- 변경사항 PR 시 `pytest`가 자동 실행되도록 하여 승인 로직의 회귀를 방지합니다.

보안 및 운영 주의사항
---------------------
- `results/` 디렉터리는 운영 환경에서 적절한 접근 제어가 필요합니다 (권한 제한, 백업 제외 등).
- Webhook URL 등 민감 정보는 환경 변수(`APPROVAL_WEBHOOK_URL`)로 관리하고, 로그/감사에 민감값이 노출되지 않도록 마스킹이 적용되어 있습니다.

향후 개선 제안
----------------
- 실시간 이벤트 기반(예: 메시지 큐)으로 전환하여 폴링/파일 기반 대기 큐를 대체
- 승인 이력 조회/검색 UI 강화 (필터, 페이징)
- 승인 시 차익/포지션 영향 요약을 자동 계산해 운영자에게 제공
