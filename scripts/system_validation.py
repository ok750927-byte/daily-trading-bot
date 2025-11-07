"""
간단한 시스템 성능 검증 및 최적화
- 기본 Python 라이브러리만 사용
- 시스템 상태 점검
- 성능 최적화 제안
"""
import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
import subprocess

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SystemValidator:
    """시스템 성능 검증기"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'validation_results': {},
            'performance_metrics': {},
            'optimization_recommendations': []
        }

    def validate_core_components(self) -> bool:
        """핵심 컴포넌트 검증"""
        logger.info("=== 핵심 컴포넌트 검증 ===")

        components = {
            'config.json': '기본 설정 파일',
            'secrets.json': '인증 정보',
            'src/': '소스 코드',
            'scripts/': '스크립트',
            'models/': '저장된 모델',
            'results/': '결과 디렉토리',
            'logs/': '로그 디렉토리'
        }

        validation_results = {}

        for component, description in components.items():
            path = self.project_root / component
            exists = path.exists()
            validation_results[component] = {
                'exists': exists,
                'description': description,
                'status': '✅ 정상' if exists else '❌ 없음'
            }

            if exists:
                logger.info(f"✅ {component}: {description}")
            else:
                logger.warning(f"❌ {component}: {description} (없음)")

        self.results['validation_results'] = validation_results

        # 성공률 계산
        success_count = sum(1 for r in validation_results.values() if r['exists'])
        success_rate = success_count / len(validation_results)

        logger.info(f"컴포넌트 검증 완료: {success_rate*100:.1f}% ({success_count}/{len(validation_results)})")
        return success_rate > 0.8

    def check_ml_models(self) -> bool:
        """ML 모델 상태 확인"""
        logger.info("=== ML 모델 상태 확인 ===")

        models_dir = self.project_root / "models"
        model_files = [
            'random_forest_model.joblib',
            'logistic_regression_model.joblib',
            'scaler.joblib'
        ]

        model_status = {}

        for model_file in model_files:
            model_path = models_dir / model_file
            if model_path.exists():
                # 파일 크기 확인
                file_size = model_path.stat().st_size
                modified_time = datetime.fromtimestamp(model_path.stat().st_mtime)

                model_status[model_file] = {
                    'exists': True,
                    'size_bytes': file_size,
                    'size_mb': round(file_size / (1024*1024), 2),
                    'modified': modified_time.isoformat(),
                    'status': '✅ 정상'
                }

                logger.info(f"✅ {model_file}: {model_status[model_file]['size_mb']}MB")
            else:
                model_status[model_file] = {
                    'exists': False,
                    'status': '❌ 없음'
                }
                logger.warning(f"❌ {model_file}: 모델 파일 없음")

        self.results['ml_models'] = model_status

        # 모델 존재 여부 확인
        existing_models = sum(1 for status in model_status.values() if status['exists'])
        return existing_models >= 2  # 최소 2개 모델 필요

    def check_api_connectivity(self) -> bool:
        """API 연결성 확인"""
        logger.info("=== API 연결성 확인 ===")

        # 메트릭 서버 상태 확인
        metrics_status = self.check_service_health("http://localhost:8000/health")

        api_status = {
            'metrics_server': {
                'url': 'http://localhost:8000',
                'status': '✅ 정상' if metrics_status else '⚠️ 중지됨',
                'accessible': metrics_status
            },
            'dashboard': {
                'url': 'http://localhost:8501',
                'status': '⚠️ 설정 필요',
                'accessible': False
            }
        }

        self.results['api_connectivity'] = api_status

        if metrics_status:
            logger.info("✅ 메트릭 서버: 정상 응답")
        else:
            logger.warning("⚠️ 메트릭 서버: 응답 없음")

        return metrics_status

    def check_service_health(self, url: str) -> bool:
        """서비스 헬스 체크"""
        try:
            import urllib.request

            request = urllib.request.Request(url)
            response = urllib.request.urlopen(request, timeout=3)
            return response.getcode() == 200
        except:
            return False

    def analyze_performance_metrics(self):
        """성능 메트릭 분석"""
        logger.info("=== 성능 메트릭 분석 ===")

        try:
            # 메트릭 파일 확인
            metrics_file = self.project_root / "results" / "metrics.jsonl"

            if metrics_file.exists():
                # 최근 메트릭 데이터 읽기
                with open(metrics_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                if lines:
                    # 마지막 5개 메트릭 분석
                    recent_metrics = []
                    for line in lines[-5:]:
                        try:
                            metric = json.loads(line.strip())
                            recent_metrics.append(metric)
                        except json.JSONDecodeError:
                            continue

                    if recent_metrics:
                        # CPU 사용률 평균
                        cpu_values = []
                        memory_values = []

                        for metric in recent_metrics:
                            if metric.get('system'):
                                cpu_values.append(metric['system'].get('cpu_percent', 0))
                                memory_values.append(metric['system'].get('memory_percent', 0))

                        performance_summary = {
                            'avg_cpu_usage': sum(cpu_values) / len(cpu_values) if cpu_values else 0,
                            'avg_memory_usage': sum(memory_values) / len(memory_values) if memory_values else 0,
                            'metrics_count': len(recent_metrics),
                            'last_update': recent_metrics[-1].get('timestamp', 'Unknown')
                        }

                        self.results['performance_metrics'] = performance_summary

                        logger.info(f"평균 CPU 사용률: {performance_summary['avg_cpu_usage']:.1f}%")
                        logger.info(f"평균 메모리 사용률: {performance_summary['avg_memory_usage']:.1f}%")
                        logger.info(f"메트릭 수집 건수: {performance_summary['metrics_count']}건")

                        return True

            logger.warning("성능 메트릭 데이터 없음")
            return False

        except Exception as e:
            logger.error(f"성능 메트릭 분석 실패: {e}")
            return False

    def generate_optimization_recommendations(self):
        """최적화 권장사항 생성"""
        logger.info("=== 최적화 권장사항 ===")

        recommendations = []

        # 컴포넌트 검증 결과 기반 권장사항
        validation_results = self.results.get('validation_results', {})
        missing_components = [k for k, v in validation_results.items() if not v.get('exists', False)]

        if missing_components:
            recommendations.append({
                'category': '구성 요소',
                'priority': 'HIGH',
                'description': f'누락된 구성 요소 복구: {", ".join(missing_components)}',
                'action': '누락된 파일 및 디렉토리 생성'
            })

        # 모델 상태 기반 권장사항
        ml_models = self.results.get('ml_models', {})
        missing_models = [k for k, v in ml_models.items() if not v.get('exists', False)]

        if missing_models:
            recommendations.append({
                'category': 'ML 모델',
                'priority': 'HIGH',
                'description': f'ML 모델 재학습 필요: {", ".join(missing_models)}',
                'action': 'python src/models/train.py 실행하여 모델 재학습'
            })

        # API 연결성 기반 권장사항
        api_status = self.results.get('api_connectivity', {})
        if not api_status.get('metrics_server', {}).get('accessible', False):
            recommendations.append({
                'category': '서비스',
                'priority': 'MEDIUM',
                'description': '메트릭 서버 비활성화 상태',
                'action': 'python scripts/metrics_server.py 실행하여 메트릭 서버 시작'
            })

        # 성능 메트릭 기반 권장사항
        perf_metrics = self.results.get('performance_metrics', {})
        avg_cpu = perf_metrics.get('avg_cpu_usage', 0)

        if avg_cpu > 80:
            recommendations.append({
                'category': '성능',
                'priority': 'MEDIUM',
                'description': f'높은 CPU 사용률 ({avg_cpu:.1f}%)',
                'action': '백그라운드 프로세스 최적화 또는 하드웨어 업그레이드 고려'
            })
        elif avg_cpu < 5:
            recommendations.append({
                'category': '성능',
                'priority': 'LOW',
                'description': f'낮은 CPU 사용률 ({avg_cpu:.1f}%) - 시스템 유휴 상태',
                'action': '거래 엔진 활성화 또는 더 많은 작업 할당 고려'
            })

        # 일반적인 최적화 권장사항
        recommendations.extend([
            {
                'category': '보안',
                'priority': 'HIGH',
                'description': 'API 키 및 인증 정보 보안 강화',
                'action': 'secrets.json 파일 권한 설정 및 정기적인 키 갱신'
            },
            {
                'category': '백업',
                'priority': 'MEDIUM',
                'description': '중요 데이터 백업 체계 구축',
                'action': '모델, 거래 내역, 설정 파일의 정기 백업 스케줄링'
            },
            {
                'category': '모니터링',
                'priority': 'LOW',
                'description': 'Docker 기반 고급 모니터링 활성화',
                'action': 'Docker 설치 후 Grafana/Prometheus 스택 구동'
            }
        ])

        self.results['optimization_recommendations'] = recommendations

        # 권장사항 출력
        for i, rec in enumerate(recommendations, 1):
            priority_icon = {'HIGH': '🔴', 'MEDIUM': '🟡', 'LOW': '🟢'}
            icon = priority_icon.get(rec['priority'], '⚪')

            logger.info(f"{icon} [{rec['category']}] {rec['description']}")
            logger.info(f"   → {rec['action']}")

    def create_optimization_plan(self):
        """최적화 계획 생성"""
        plan_file = self.project_root / "results" / "optimization_plan.json"

        optimization_plan = {
            'generated_at': datetime.now().isoformat(),
            'system_status': 'OPERATIONAL',
            'validation_summary': self.results,
            'immediate_actions': [
                rec for rec in self.results.get('optimization_recommendations', [])
                if rec['priority'] == 'HIGH'
            ],
            'medium_term_actions': [
                rec for rec in self.results.get('optimization_recommendations', [])
                if rec['priority'] == 'MEDIUM'
            ],
            'long_term_actions': [
                rec for rec in self.results.get('optimization_recommendations', [])
                if rec['priority'] == 'LOW'
            ]
        }

        with open(plan_file, 'w', encoding='utf-8') as f:
            json.dump(optimization_plan, f, ensure_ascii=False, indent=2)

        logger.info(f"최적화 계획 저장: {plan_file}")
        return optimization_plan

    def run_full_validation(self) -> Dict:
        """전체 검증 실행"""
        logger.info("🔍 Daily Trading Bot 시스템 검증 시작")
        logger.info("=" * 50)

        validation_steps = [
            ("핵심 컴포넌트 검증", self.validate_core_components),
            ("ML 모델 상태 확인", self.check_ml_models),
            ("API 연결성 확인", self.check_api_connectivity),
            ("성능 메트릭 분석", self.analyze_performance_metrics)
        ]

        step_results = []

        for step_name, step_func in validation_steps:
            logger.info(f"\n>>> {step_name} 진행 중...")
            try:
                result = step_func()
                step_results.append(result)

                if result:
                    logger.info(f"✅ {step_name} 완료")
                else:
                    logger.warning(f"⚠️ {step_name} 문제 발견")

            except Exception as e:
                logger.error(f"❌ {step_name} 실패: {e}")
                step_results.append(False)

        # 최적화 권장사항 생성
        self.generate_optimization_recommendations()

        # 최적화 계획 생성
        optimization_plan = self.create_optimization_plan()

        # 종합 결과
        success_count = sum(1 for result in step_results if result)
        success_rate = success_count / len(step_results)

        logger.info("\n" + "=" * 50)
        logger.info("📊 시스템 검증 결과")
        logger.info(f"성공률: {success_rate*100:.1f}% ({success_count}/{len(step_results)})")

        if success_rate >= 0.75:
            logger.info("🎉 시스템 상태 양호 - 운영 준비 완료")
        elif success_rate >= 0.5:
            logger.info("⚠️ 시스템 상태 보통 - 일부 최적화 필요")
        else:
            logger.warning("🔧 시스템 상태 불량 - 즉시 개선 필요")

        return optimization_plan

def main():
    """메인 실행 함수"""
    try:
        validator = SystemValidator()
        optimization_plan = validator.run_full_validation()

        print("\n🎯 최적화 계획 요약:")

        immediate = optimization_plan.get('immediate_actions', [])
        if immediate:
            print(f"🔴 즉시 조치 필요: {len(immediate)}건")
            for action in immediate[:3]:  # 상위 3개만 표시
                print(f"  - {action['description']}")

        medium = optimization_plan.get('medium_term_actions', [])
        if medium:
            print(f"🟡 중기 개선 사항: {len(medium)}건")

        long_term = optimization_plan.get('long_term_actions', [])
        if long_term:
            print(f"🟢 장기 최적화: {len(long_term)}건")

        print(f"\n📄 상세 계획: results/optimization_plan.json")

    except Exception as e:
        logger.error(f"검증 실행 실패: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
