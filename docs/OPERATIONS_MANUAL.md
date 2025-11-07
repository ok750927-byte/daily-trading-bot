
# Daily Trading Bot - 운영 매뉴얼

## 🎯 시스템 개요
Daily Trading Bot은 AI 기반 자동 주식 거래 시스템으로 다음 구성 요소들로 이루어져 있습니다:

### 핵심 구성 요소
- **ML 파이프라인**: RandomForest 모델 (80% 정확도)
- **실시간 거래 엔진**: WebSocket 기반 자동 매매
- **모니터링 시스템**: Prometheus 메트릭 + 실시간 대시보드
- **알림 시스템**: Discord 웹훅 통합
- **리스크 관리**: 손절(-3%), 익절(+5%) 자동화

## 🚀 일상 운영 가이드

### 1. 시스템 시작 (매일 아침)
```cmd
# 통합 제어판 실행
python scripts/control_panel.py

# 또는 개별 서비스 시작
python scripts/metrics_server.py        # 메트릭 서버
python scripts/performance_monitor.py   # 성능 모니터
python src/trading/realtime_engine.py   # 거래 엔진
```

### 2. 상태 확인
```cmd
# 시스템 검증
python scripts/system_validation.py

# 웹 대시보드 확인
- 메트릭 API: http://localhost:8000/metrics
- 헬스 체크: http://localhost:8000/health
- HTML 대시보드: results/production_dashboard.html
```

### 3. 성능 모니터링
- **CPU 사용률**: 85% 이하 유지
- **메모리 사용률**: 90% 이하 유지
- **에러 발생**: 시간당 5건 이하
- **서비스 응답**: 3초 이내

### 4. 거래 모니터링
- **거래 로그**: results/trade_log.json
- **성과 리포트**: results/performance_summary.json
- **메트릭 데이터**: results/metrics.jsonl

## 🔧 문제 해결

### 일반적인 문제들

#### 1. 메트릭 서버 응답 없음
```cmd
# 포트 8000 사용 프로세스 확인
netstat -ano | findstr :8000

# 프로세스 종료 후 재시작
taskkill /f /pid <PID>
python scripts/metrics_server.py
```

#### 2. 메모리 사용률 높음
```cmd
# 시스템 검증 실행
python scripts/system_validation.py

# 불필요한 프로세스 종료
scripts\service_scripts\stop_all_services.bat
```

#### 3. 거래 엔진 오류
```cmd
# 로그 확인
type logs	rading-engine.log

# API 연결 확인
python scripts	est_api_connection.py

# 엔진 재시작
python src	radingealtime_engine.py
```

#### 4. Discord 알림 실패
```cmd
# secrets.json 확인
# Discord 웹훅 URL 유효성 검증
python scripts\setup_discord.py
```

## 📊 성능 최적화

### CPU 최적화
- **백그라운드 프로세스**: 불필요한 서비스 종료
- **메트릭 수집 주기**: 30초 → 60초 (필요 시)
- **ML 모델 추론**: 배치 처리로 최적화

### 메모리 최적화
- **데이터 캐싱**: 적절한 캐시 크기 설정
- **로그 순환**: 오래된 로그 파일 정리
- **모델 최적화**: 경량화된 모델 사용 검토

### 네트워크 최적화
- **API 호출**: 필요한 경우에만 호출
- **WebSocket 연결**: 연결 풀링 활용
- **데이터 압축**: 대용량 데이터 전송 시

## 🎯 다음 단계 로드맵

### Phase 1: 고도화 (1-2주)
1. **Docker 환경 구축**
   - Grafana/Prometheus 스택 활성화
   - 컨테이너 기반 서비스 오케스트레이션

2. **실시간 백테스팅**
   - 과거 데이터 기반 성능 검증
   - A/B 테스트 프레임워크 구축

3. **고급 알림 시스템**
   - 조건부 알림 (수익률, 손실률 기준)
   - 모바일 푸시 알림 (추가)

### Phase 2: 확장 (2-4주)
1. **멀티 전략 시스템**
   - 다양한 거래 전략 동시 실행
   - 전략별 성과 비교 및 최적화

2. **포트폴리오 관리**
   - 자동 리밸런싱
   - 리스크 분산 전략

3. **기계학습 고도화**
   - 앙상블 모델 (XGBoost, LightGBM 추가)
   - 딥러닝 모델 (LSTM, Transformer)

### Phase 3: 프로덕션 (1-2개월)
1. **실제 거래 연동**
   - 모의 거래 → 소액 실거래
   - 리스크 한도 및 안전장치 강화

2. **클라우드 배포**
   - AWS/Azure 클라우드 환경
   - 24/7 무중단 서비스

3. **웹 포털**
   - 사용자 친화적 웹 인터페이스
   - 실시간 거래 현황 및 제어

## 🔒 보안 관리

### API 키 관리
- **정기 갱신**: 월 1회 API 키 교체
- **권한 최소화**: 필요한 권한만 부여
- **암호화 저장**: secrets.json 암호화

### 시스템 보안
- **방화벽**: 필요한 포트만 개방
- **로그 모니터링**: 비정상 접근 감지
- **백업**: 중요 데이터 정기 백업

### 거래 보안
- **거래 한도**: 일일/월간 거래 한도 설정
- **이상 거래 감지**: 비정상 패턴 자동 차단
- **수동 개입**: 긴급 상황 시 수동 중단

## 📋 체크리스트

### 일일 점검 (5분)
- [ ] 시스템 상태 확인 (control_panel.py)
- [ ] 거래 성과 확인 (performance_summary.json)
- [ ] 에러 로그 점검 (alert_log.jsonl)
- [ ] 리소스 사용률 확인 (monitoring.jsonl)

### 주간 점검 (30분)
- [ ] 시스템 검증 실행 (system_validation.py)
- [ ] 모델 성능 재평가
- [ ] 거래 전략 효과성 분석
- [ ] 백업 데이터 확인

### 월간 점검 (2시간)
- [ ] 전체 시스템 최적화
- [ ] 보안 설정 검토
- [ ] 성능 튜닝
- [ ] 다음 달 전략 수립

## 🆘 긴급 상황 대응

### 시스템 다운
1. **즉시 조치**: 모든 거래 중단
2. **원인 파악**: 로그 분석 및 진단
3. **복구 작업**: 백업에서 복원
4. **재가동**: 단계별 서비스 재시작

### 대량 손실 발생
1. **거래 중단**: 자동 매매 즉시 정지
2. **포지션 정리**: 수동으로 포지션 정리
3. **원인 분석**: 거래 로그 및 시장 상황 분석
4. **전략 수정**: 리스크 관리 강화

### API 연결 실패
1. **백업 API**: 대체 API 엔드포인트 활용
2. **수동 모드**: 자동 거래 → 알림만 모드
3. **연결 복구**: API 제공업체 문의
4. **시스템 재연결**: 연결 복구 후 재가동

---

**📞 지원 연락처**
- 시스템 관리자: [연락처 정보]
- API 지원: 한국투자증권 고객센터
- 기술 문의: [GitHub Issues 또는 이메일]

**📚 추가 자료**
- 개발 문서: docs/ 디렉토리
- API 문서: 한국투자증권 공식 문서
- 커뮤니티: [관련 커뮤니티 링크]

---
*이 매뉴얼은 시스템 변경 시 업데이트됩니다.*
*최종 수정: 2025년 11월 04일*
