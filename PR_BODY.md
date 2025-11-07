변경 요약
- 운영자 승인(Operator Approval) 기능 추가 및 GUI 연동
  - 대시보드의 실시간 트레이딩 화면에 승인 대기창 추가(자동 새로고침, 상세 JSON 뷰, 다중 승인/거부).
- 승인 매니저 통합
  - `src/trading/approval.py`: 파일 기반 persistence(JSONL), audit, webhook, 핸들러 등록(register_handler) 지원. 기존 레거시 호출 양식과 호환되도록 설계.
  - 핸들러는 가능하면 동기 호출을 우선 수행해 테스트/제한된 환경에서 안정적으로 동작하도록 구현.
- 테스트 추가
  - `tests/test_approval_manager.py` — submit/list/approve/reject 및 handler 호출 검증
  - `tests/test_realtime_approval_integration.py` — RealtimeTrader + ApprovalManager 통합 검증(승인 후 send_order 호출)
- 문서 추가/수정
  - `README.md` 및 `DEV_GUIDE.md`에 운영자 승인 사용법, 파일 위치, 환경변수 및 테스트 방법을 문서화

검증
- 로컬에서 pytest로 새로 추가한 테스트 포함 전체 테스트를 실행해 통과함을 확인했습니다.

보안/운영 주의사항
- 승인 관련 JSONL 파일(`results/pending_approvals.jsonl`, `results/approval_audit.jsonl`, `results/approval_queue.jsonl`)은 감사 기록을 포함하므로 운영 환경에서 권한 제어가 필요합니다.
- Webhook 전송 시 민감필드(토큰/키 등)는 마스킹 처리됩니다.

리뷰 포인트
- 승인 UI UX(컬럼/정렬)와 ApprovalManager의 동기 핸들러 호출 방식 검토

```
PR 생성자: chore/fix-warnings -> main
```
