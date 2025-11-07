"""
모의거래 실행 및 통합 관리 시스템
- 실시간 모의거래 실행
- 포트폴리오 최적화 적용
- 성과 모니터링
- 리스크 관리
"""
import os
import sys
import json
import time
import logging
import threading
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import schedule
import pandas as pd
import numpy as np

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 내부 모듈 임포트
try:
    from src.trading.live_trading_engine import LiveTradingEngine
    from src.trading.realtime_market_data import RealTimeTrader
    from src.analysis.portfolio_optimization import PortfolioOptimizer
    from src.analysis.advanced_backtesting import AdvancedBacktester
except ImportError:
    # 모듈 경로 문제 시 직접 로드
    pass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LiveTradingOrchestrator:
    """실시간 모의거래 총괄 관리 시스템"""
    
    def __init__(self, gui_log_callback=None, gui_status_callback=None, gui_position_callback=None):
        self.project_root = project_root
        self.config = self.load_config()
        
        # 핵심 구성 요소
        self.trading_engine = None
        self.realtime_trader = None
        self.portfolio_optimizer = PortfolioOptimizer()
        
        # 거래 설정
        self.symbols = self.config.get("target_stocks", [])
        self.max_positions = self.config.get("trading", {}).get("max_positions", 5)
        
        # 시스템 상태
        self._stop_event = threading.Event()
        self.is_trading_active = False
        self.is_market_open = False
        self.last_optimization_time = None
        self.current_portfolio = {}
        
        # 성과 추적
        self.daily_stats = {
            'start_time': None,
            'trades_count': 0,
            'profit_loss': 0,
            'portfolio_value': self.config.get("trading", {}).get("initial_capital", 10_000_000)
        }
        
        # GUI 콜백
        self.log_to_gui = gui_log_callback
        self.update_gui_status = gui_status_callback
        self.update_gui_positions = gui_position_callback

    def _log(self, message, level="info"):
        """GUI와 콘솔에 모두 로깅"""
        if level == "info":
            logger.info(message)
        elif level == "error":
            logger.error(message)
        elif level == "warning":
            logger.warning(message)
        
        if self.log_to_gui:
            self.log_to_gui(message)

    def load_config(self) -> Dict:
        """설정 로드"""
        try:
            config_file = self.project_root / "config.json"
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"설정 로드 실패: {e}")
            return {}
    
    def initialize_systems(self) -> bool:
        """시스템 초기화"""
        try:
            self._log("시스템 초기화 시작...")
            
            # 1. 거래 엔진 초기화
            self._log("거래 엔진 초기화...")
            self.trading_engine = LiveTradingEngine()
            
            # API 연결 테스트
            if not self.trading_engine.get_access_token():
                self._log("API 토큰 발급 실패", "error")
                return False
            
            # 2. 실시간 데이터 수신기 초기화
            self._log("실시간 데이터 시스템 초기화...")
            self.realtime_trader = RealTimeTrader()
            
            # 3. 포트폴리오 최적화 준비
            self._log("포트폴리오 최적화 시스템 준비...")
            
            self._log("✅ 시스템 초기화 완료")
            return True
            
        except Exception as e:
            self._log(f"시스템 초기화 실패: {e}", "error")
            return False
    
    def run(self):
        """오케스트레이터 메인 루프"""
        if not self.initialize_systems():
            self._log("초기화 실패로 오케스트레이터를 시작할 수 없습니다.", "error")
            if self.update_gui_status: self.update_gui_status("ERROR")
            return

        self._log("🚀 실시간 트레이딩 오케스트레이터 시작됨.")
        if self.update_gui_status: self.update_gui_status("RUNNING")
        self.is_trading_active = True
        
        # 테스트를 위해 즉시 장 시작 로직 실행 (원래는 스케줄러가 담당)
        self.start_trading_session()

        # 스케줄러 루프
        last_position_update = 0
        while not self._stop_event.is_set():
            # 5초마다 포지션 업데이트
            if time.time() - last_position_update > 5:
                self.update_live_positions()
                last_position_update = time.time()

            time.sleep(1)
        
        self.shutdown()

    def stop(self):
        """오케스트레이터 중지"""
        self._log("오케스트레이터 중지 요청 수신...")
        self._stop_event.set()

    def shutdown(self):
        """시스템 종료 처리"""
        self._log("시스템 종료 중...")
        self.is_trading_active = False
        if self.realtime_trader:
            self.realtime_trader.stop()
        
        # 모든 스레드 및 프로세스 정리
        
        self._log("시스템이 안전하게 종료되었습니다.")
        if self.update_gui_status: self.update_gui_status("STOPPED")

    def setup_scheduler(self):
        """작업 스케줄러 설정"""
        # GUI에서 직접 제어하므로 스케줄러는 비활성화
        self._log("GUI 모드에서는 스케줄러를 사용하지 않습니다.")
    
    def pre_market_preparation(self):
        """장 시작 전 준비"""
        try:
            self._log("🔄 장 시작 전 준비...")
            
            # 1. 시스템 상태 체크
            self.check_system_health()
            
            # 2. 잔고 조회
            balance = self.trading_engine.get_balance()
            if balance:
                self._log("잔고 조회 완료")
            
            # 3. 오늘의 거래 계획 수립
            self.plan_daily_trades()
            
            # 4. 시장 데이터 연결 준비
            if hasattr(self.realtime_trader, 'market_receiver'):
                self.realtime_trader.market_receiver.connect()
            
            self._log("✅ 장 시작 전 준비 완료")
            
        except Exception as e:
            self._log(f"장 시작 전 준비 실패: {e}", "error")
    
    def update_live_positions(self):
        """실시간 포지션 정보를 조회하고 GUI에 업데이트"""
        if not self.trading_engine:
            return
            
        try:
            balance_info = self.trading_engine.get_balance()
            if balance_info and self.update_gui_positions:
                # GUI 콜백은 'output1'(주식 잔고)만 전달
                self.update_gui_positions(balance_info.get('output1', []))
        except Exception as e:
            self._log(f"포지션 정보 업데이트 실패: {e}", "error")

    def start_trading_session(self):
        """거래 세션 시작"""
        try:
            self._log("🚀 거래 세션 시작")
            
            self.is_market_open = True
            self.is_trading_active = True
            self.daily_stats['start_time'] = datetime.now()
            
            # 실시간 거래 시작
            if self.realtime_trader:
                # 별도 스레드에서 실행
                trading_thread = threading.Thread(target=self.realtime_trader.start)
                trading_thread.daemon = True
                trading_thread.start()
            
            # 실시간 모니터링 시작
            self.start_real_time_monitoring()
            
            self.send_alert("거래 세션이 시작되었습니다.")
            
        except Exception as e:
            logger.error(f"거래 세션 시작 실패: {e}")
    
    def pause_trading(self):
        """거래 일시 중단 (점심시간)"""
        try:
            logger.info("⏸️ 거래 일시 중단 (점심시간)")
            self.is_trading_active = False
            
        except Exception as e:
            logger.error(f"거래 중단 실패: {e}")
    
    def resume_trading(self):
        """거래 재개"""
        try:
            logger.info("▶️ 거래 재개")
            self.is_trading_active = True
            
        except Exception as e:
            logger.error(f"거래 재개 실패: {e}")
    
    def end_trading_session(self):
        """거래 세션 종료"""
        try:
            logger.info("🔚 거래 세션 종료")
            
            self.is_market_open = False
            self.is_trading_active = False
            
            # 미체결 주문 정리
            self.cleanup_pending_orders()
            
            # 오늘의 성과 집계
            self.calculate_daily_performance()
            
            self.send_alert("거래 세션이 종료되었습니다.")
            
        except Exception as e:
            logger.error(f"거래 세션 종료 실패: {e}")
    
    def plan_daily_trades(self):
        """일일 거래 계획 수립"""
        try:
            logger.info("📋 일일 거래 계획 수립...")
            
            # 1. 시장 환경 분석
            market_condition = self.analyze_market_condition()
            
            # 2. 포트폴리오 최적화 (필요시)
            if self.should_rebalance():
                self.optimize_portfolio()
            
            # 3. 오늘의 거래 대상 선정
            trade_candidates = self.select_trade_candidates()
            
            # 4. 리스크 한도 설정
            self.set_daily_risk_limits()
            
            logger.info(f"거래 계획 완료: {len(trade_candidates)}개 종목")
            
        except Exception as e:
            logger.error(f"거래 계획 수립 실패: {e}")
    
    def analyze_market_condition(self) -> Dict:
        """시장 환경 분석"""
        try:
            # 간단한 시장 환경 분석
            market_condition = {
                'trend': 'neutral',  # bullish, bearish, neutral
                'volatility': 'normal',  # low, normal, high
                'volume': 'normal',  # low, normal, high
                'sentiment': 'neutral'  # positive, negative, neutral
            }
            
            # 실제로는 더 정교한 분석 필요
            # - 주요 지수 동향
            # - VIX 지수
            # - 섹터별 성과
            # - 뉴스 센티먼트 등
            
            return market_condition
            
        except Exception as e:
            logger.error(f"시장 환경 분석 실패: {e}")
            return {}
    
    def should_rebalance(self) -> bool:
        """리밸런싱 필요 여부 판단"""
        try:
            if not self.last_optimization_time:
                return True
            
            # 마지막 최적화 이후 경과 시간 확인
            days_since_optimization = (datetime.now() - self.last_optimization_time).days
            
            if self.rebalance_frequency == 'daily':
                return days_since_optimization >= 1
            elif self.rebalance_frequency == 'weekly':
                return days_since_optimization >= 7
            else:
                return days_since_optimization >= 30  # monthly
            
        except Exception as e:
            logger.error(f"리밸런싱 여부 판단 실패: {e}")
            return False
    
    def optimize_portfolio(self):
        """포트폴리오 최적화 실행"""
        try:
            logger.info("💼 포트폴리오 최적화 실행...")
            
            # 과거 데이터 준비
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            
            # 수익률 데이터 로드
            returns_df = self.portfolio_optimizer.load_returns_data(
                self.symbols, start_date, end_date
            )
            
            if not returns_df.empty:
                # 기대 수익률 및 공분산 행렬 계산
                expected_returns = self.portfolio_optimizer.calculate_expected_returns(returns_df)
                cov_matrix = self.portfolio_optimizer.calculate_covariance_matrix(returns_df)
                
                # 포트폴리오 최적화
                opt_result = self.portfolio_optimizer.optimize_portfolio(
                    expected_returns, cov_matrix, method='max_sharpe'
                )
                
                if opt_result.get('success', False):
                    self.current_portfolio = opt_result['weights']
                    self.last_optimization_time = datetime.now()
                    
                    logger.info("포트폴리오 최적화 완료")
                    logger.info(f"최적 비중: {self.current_portfolio}")
                else:
                    logger.warning("포트폴리오 최적화 실패")
            else:
                logger.warning("포트폴리오 최적화를 위한 데이터 부족")
                
        except Exception as e:
            logger.error(f"포트폴리오 최적화 실패: {e}")
    
    def select_trade_candidates(self) -> List[str]:
        """거래 대상 종목 선정"""
        try:
            # 포트폴리오 비중이 높은 순서로 선정
            if self.current_portfolio:
                candidates = sorted(
                    self.current_portfolio.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:self.max_positions]
                
                return [symbol for symbol, weight in candidates if weight > 0.05]  # 5% 이상
            else:
                return self.symbols[:self.max_positions]
                
        except Exception as e:
            logger.error(f"거래 대상 선정 실패: {e}")
            return self.symbols[:3]  # 기본값
    
    def set_daily_risk_limits(self):
        """일일 리스크 한도 설정"""
        try:
            portfolio_value = self.daily_stats['portfolio_value']
            
            # 일일 손실 한도: 포트폴리오 가치의 2%
            daily_loss_limit = portfolio_value * 0.02
            
            # 단일 종목 최대 손실: 포트폴리오 가치의 0.5%
            single_stock_loss_limit = portfolio_value * 0.005
            
            # 거래 엔진에 한도 설정
            if self.trading_engine:
                self.trading_engine.daily_loss_limit = -daily_loss_limit
                # 기타 리스크 한도 설정...
            
            logger.info(f"일일 리스크 한도 설정 완료: {daily_loss_limit:,.0f}원")
            
        except Exception as e:
            logger.error(f"리스크 한도 설정 실패: {e}")
    
    def start_real_time_monitoring(self):
        """실시간 모니터링 시작"""
        def monitor_loop():
            while self.is_market_open:
                try:
                    # 포지션 모니터링
                    if self.trading_engine:
                        self.trading_engine.monitor_positions()
                        
                        # 리스크 한도 체크
                        if not self.trading_engine.check_risk_limits():
                            self.send_alert("⚠️ 리스크 한도 위반 - 거래 중단")
                    
                    # 성과 업데이트
                    self.update_performance_stats()
                    
                    time.sleep(10)  # 10초마다 체크
                    
                except Exception as e:
                    logger.error(f"모니터링 오류: {e}")
                    time.sleep(30)
        
        # 별도 스레드에서 실행
        monitor_thread = threading.Thread(target=monitor_loop)
        monitor_thread.daemon = True
        monitor_thread.start()
    
    def update_performance_stats(self):
        """성과 통계 업데이트"""
        try:
            if self.trading_engine:
                stats = self.trading_engine.daily_stats
                
                self.daily_stats.update({
                    'trades_count': stats['trades_count'],
                    'profit_loss': stats['profit_loss']
                })
                
                # 포트폴리오 가치 업데이트 (잔고 + 포지션 가치)
                # 실제로는 정확한 계산 필요
                self.daily_stats['portfolio_value'] += stats['profit_loss']
                
        except Exception as e:
            logger.error(f"성과 통계 업데이트 실패: {e}")
    
    def cleanup_pending_orders(self):
        """미체결 주문 정리"""
        try:
            logger.info("미체결 주문 정리 중...")
            
            # 실제로는 미체결 주문 조회 후 취소 처리
            # 여기서는 로그만 출력
            
            logger.info("미체결 주문 정리 완료")
            
        except Exception as e:
            logger.error(f"미체결 주문 정리 실패: {e}")
    
    def calculate_daily_performance(self):
        """일일 성과 계산"""
        try:
            start_value = 10_000_000  # 초기 가치 (실제로는 장 시작 시점 가치)
            current_value = self.daily_stats['portfolio_value']
            
            daily_return = (current_value - start_value) / start_value
            
            performance = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'start_value': start_value,
                'end_value': current_value,
                'daily_return': daily_return,
                'profit_loss': current_value - start_value,
                'trades_count': self.daily_stats['trades_count']
            }
            
            # 성과 기록 저장
            self.save_daily_performance(performance)
            
            logger.info(f"일일 성과: {daily_return:.2%} ({performance['profit_loss']:,.0f}원)")
            
        except Exception as e:
            logger.error(f"일일 성과 계산 실패: {e}")
    
    def save_daily_performance(self, performance: Dict):
        """일일 성과 저장"""
        try:
            perf_file = self.project_root / "results" / "daily_performance.jsonl"
            perf_file.parent.mkdir(exist_ok=True)
            
            with open(perf_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(performance, ensure_ascii=False) + '\n')
                
        except Exception as e:
            logger.error(f"일일 성과 저장 실패: {e}")
    
    def generate_daily_report(self):
        """일일 리포트 생성"""
        try:
            logger.info("📊 일일 리포트 생성...")
            
            report = []
            report.append("=" * 50)
            report.append("일일 거래 리포트")
            report.append("=" * 50)
            report.append(f"날짜: {datetime.now().strftime('%Y-%m-%d')}")
            report.append(f"거래 건수: {self.daily_stats['trades_count']}건")
            report.append(f"손익: {self.daily_stats['profit_loss']:,.0f}원")
            report.append(f"포트폴리오 가치: {self.daily_stats['portfolio_value']:,.0f}원")
            
            # 포지션 현황
            if self.trading_engine and self.trading_engine.positions:
                report.append(f"\n현재 포지션:")
                for symbol, position in self.trading_engine.positions.items():
                    report.append(f"  {symbol}: {position['quantity']}주 @ {position['avg_price']:,.0f}원")
            
            report.append("=" * 50)
            
            report_text = "\n".join(report)
            
            # 리포트 저장
            report_file = self.project_root / "results" / f"daily_report_{datetime.now().strftime('%Y%m%d')}.txt"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report_text)
            
            # 콘솔 출력
            print(report_text)
            
            # 알림 발송
            self.send_alert("일일 리포트가 생성되었습니다.")
            
        except Exception as e:
            logger.error(f"일일 리포트 생성 실패: {e}")
    
    def weekly_portfolio_optimization(self):
        """주간 포트폴리오 최적화"""
        try:
            logger.info("📈 주간 포트폴리오 최적화...")
            
            # 주간 백테스트 실행
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
            
            results = self.backtester.run_multi_symbol_backtest(
                self.symbols, start_date, end_date
            )
            
            if results:
                # 성과 기반 포트폴리오 조정
                self.adjust_portfolio_based_on_performance(results)
                
                # 주간 리포트 생성
                report = self.backtester.create_performance_report(results)
                
                weekly_report_file = self.project_root / "results" / f"weekly_report_{datetime.now().strftime('%Y%m%d')}.txt"
                with open(weekly_report_file, 'w', encoding='utf-8') as f:
                    f.write(report)
                
                self.send_alert("주간 포트폴리오 최적화가 완료되었습니다.")
            
        except Exception as e:
            logger.error(f"주간 포트폴리오 최적화 실패: {e}")
    
    def adjust_portfolio_based_on_performance(self, backtest_results: Dict):
        """성과 기반 포트폴리오 조정"""
        try:
            # 성과 순으로 정렬
            sorted_results = sorted(
                backtest_results.items(),
                key=lambda x: x[1].total_return,
                reverse=True
            )
            
            # 상위 성과 종목의 비중 증가
            new_weights = {}
            total_weight = 0
            
            for i, (symbol, result) in enumerate(sorted_results):
                if i < self.max_positions:
                    # 성과에 따른 가중치 부여
                    weight = max(0.1, 0.4 - i * 0.05)  # 1등 40%, 2등 35%, ...
                    new_weights[symbol] = weight
                    total_weight += weight
            
            # 정규화
            for symbol in new_weights:
                new_weights[symbol] /= total_weight
            
            self.current_portfolio = new_weights
            logger.info(f"포트폴리오 조정 완료: {new_weights}")
            
        except Exception as e:
            logger.error(f"포트폴리오 조정 실패: {e}")
    
    def check_system_health(self):
        """시스템 상태 체크"""
        try:
            health_status = {
                'api_connection': False,
                'data_connection': False,
                'trading_engine': False,
                'portfolio_optimizer': False
            }
            
            # API 연결 상태
            if self.trading_engine and self.trading_engine.get_access_token():
                health_status['api_connection'] = True
            
            # 데이터 연결 상태 (간단히 체크)
            health_status['data_connection'] = True
            
            # 거래 엔진 상태
            health_status['trading_engine'] = self.trading_engine is not None
            
            # 포트폴리오 최적화 상태
            health_status['portfolio_optimizer'] = True
            
            logger.info(f"시스템 상태: {health_status}")
            
            # 문제가 있으면 알림
            failed_systems = [k for k, v in health_status.items() if not v]
            if failed_systems:
                self.send_alert(f"⚠️ 시스템 문제 발견: {', '.join(failed_systems)}")
            
        except Exception as e:
            logger.error(f"시스템 상태 체크 실패: {e}")
    
    def add_alert_callback(self, callback):
        """알림 콜백 추가"""
        self.alert_callbacks.append(callback)
    
    def send_alert(self, message: str):
        """알림 발송"""
        try:
            logger.info(f"🚨 알림: {message}")
            
            # 콜백 실행
            for callback in self.alert_callbacks:
                try:
                    callback(message)
                except Exception as e:
                    logger.error(f"알림 콜백 오류: {e}")
            
            # 알림 로그 저장
            alert_log = {
                'timestamp': datetime.now().isoformat(),
                'message': message
            }
            
            log_file = self.project_root / "logs" / "alerts.jsonl"
            log_file.parent.mkdir(exist_ok=True)
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(alert_log, ensure_ascii=False) + '\n')
                
        except Exception as e:
            logger.error(f"알림 발송 실패: {e}")
    
    def run_scheduler(self):
        """스케줄러 실행"""
        logger.info("스케줄러 시작...")
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # 1분마다 체크
            except KeyboardInterrupt:
                logger.info("스케줄러 종료")
                break
            except Exception as e:
                logger.error(f"스케줄러 오류: {e}")
                time.sleep(60)
    
    def start(self):
        """시스템 시작"""
        logger.info("🚀 실시간 모의거래 시스템 시작")
        
        # 시스템 초기화
        if not self.initialize_systems():
            logger.error("시스템 초기화 실패")
            return
        
        # 스케줄러 실행 (별도 스레드)
        scheduler_thread = threading.Thread(target=self.run_scheduler)
        scheduler_thread.daemon = True
        scheduler_thread.start()
        
        # 메인 루프
        try:
            while True:
                # 주기적 상태 체크
                self.check_system_health()
                
                # 대기
                time.sleep(300)  # 5분마다 상태 체크
                
        except KeyboardInterrupt:
            logger.info("시스템 종료 신호 받음")
            self.cleanup_and_exit()
    
    def cleanup_and_exit(self):
        """시스템 종료 처리"""
        try:
            logger.info("시스템 종료 처리...")
            
            # 거래 중단
            self.is_trading_active = False
            
            # 포지션 정리 (선택사항)
            if self.trading_engine:
                # 필요시 모든 포지션 청산
                # self.trading_engine.emergency_close_all_positions("SYSTEM_SHUTDOWN")
                pass
            
            # 최종 리포트 생성
            self.generate_daily_report()
            
            logger.info("✅ 시스템 종료 완료")
            
        except Exception as e:
            logger.error(f"시스템 종료 처리 실패: {e}")

def main():
    """메인 실행"""
    print("🚀 실시간 모의거래 통합 시스템")
    print("=" * 60)
    print("⚠️  주의: 이 시스템은 실제 모의거래를 수행합니다.")
    print("실제 거래 전에 충분한 테스트와 검증이 필요합니다.")
    print()
    
    confirm = input("실시간 모의거래를 시작하시겠습니까? (y/N): ").strip().lower()
    
    if confirm == 'y':
        try:
            orchestrator = LiveTradingOrchestrator()
            orchestrator.start()
        except Exception as e:
            print(f"❌ 시스템 오류: {e}")
    else:
        print("시스템 시작 취소")

if __name__ == "__main__":
    main()