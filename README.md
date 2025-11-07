# trading-bot

주식 자동매매 프로젝트 초기 레포. Phase1(환경설정) 템플릿과 예제 파일을 포함합니다.

구성:

빠른 시작:

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

환경 변수 예시 (PowerShell):

```powershell
$env:TRADING_API_KEY = "your_api_key_here"
$env:TRADING_API_SECRET = "your_secret_here"
```

## 운영자(Operator) 승인 흐름

최근 추가된 운영자 승인(Operator Approval) 기능은 실거래 주문 전 운영자의 확인을 받도록 설계되었습니다. 주요 포인트:

- 승인 매니저: `src/trading/approval.py` 에서 `ApprovalManager`를 통해 관리됩니다. 승인 요청은 파일(`results/pending_approvals.jsonl`)에 기록되며, 감사 로그(`results/approval_audit.jsonl`)가 남습니다.
- GUI 통합: 대시보드의 "실시간 트레이딩" 화면에서 "승인 대기" 버튼을 눌러 대기중인 승인 목록을 확인하고, 상세(JSON) 보기 후 승인/거부할 수 있습니다.
- 엔진 연동: `src/trading/realtime_trader.py` 와 `src/trading/live_trading_engine.py` 는 승인 매니저에 요청을 제출하고, 승인 시 등록된 핸들러가 주문을 실행합니다.

사용법 요약:

1. GUI로 확인하기
	- 가상환경 활성화 후: `python run_gui.py`
	- 대시보드 → 실시간 트레이딩 → 상단의 "승인 대기" 버튼을 클릭
	- 목록에서 항목 선택 후 '승인' 또는 '거부' 버튼을 사용

2. 명령형(테스트)
	- ApprovalManager 인스턴스를 통해 직접 제출/승인/거부 가능
	- 예: `python -c "from src.trading.approval import manager; id=manager.submit({'symbol':'005930','qty':1}); manager.approve(id, operator='me')"`

3. 파일 위치
	- 대기 및 감사 파일: `results/pending_approvals.jsonl`, `results/approval_audit.jsonl`, `results/approval_queue.jsonl`

환경변수(선택적)

- `APPROVAL_WEBHOOK_URL`: 승인 요청/결정 시 외부 알림(Webhook)을 전송합니다 (payload는 민감정보를 마스킹해 전송).
- `AUTO_APPROVE`: '1' 또는 'true'로 설정하면 승인 없이 자동으로 주문을 진행합니다 (테스트 용도).

테스트

- 로컬 단위/통합 테스트가 추가되었습니다. 실행:

```powershell
python -m pytest -q
```

문제 보고 및 PR

변경사항은 로컬에서 검증되었으며, 원격에 푸시/PR을 만들려면 적절한 권한(PAT)이 필요합니다. 자세한 단계는 프로젝트 개발 가이드(DEV_GUIDE.md)를 참고하세요.
