"""
성능 메트릭 수집기
- 시스템 리소스 모니터링
- 거래 성과 메트릭
- 에러 및 알림 통계
"""
import os
import time
import json
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List
import logging
from dataclasses import dataclass, asdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SystemMetrics:
    """시스템 메트릭"""
    timestamp: str
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    network_bytes_sent: int
    network_bytes_recv: int

@dataclass
class TradingMetrics:
    """거래 메트릭"""
    timestamp: str
    total_trades: int
    successful_trades: int
    failed_trades: int
    total_profit: float
    daily_profit: float
    win_rate: float
    active_positions: int
    portfolio_value: float

@dataclass
class ErrorMetrics:
    """에러 메트릭"""
    timestamp: str
    api_errors: int
    connection_errors: int
    order_errors: int
    data_errors: int
    total_errors: int

class MetricsCollector:
    """메트릭 수집기"""
    
    def __init__(self, collection_interval: int = 60):
        self.collection_interval = collection_interval
        self.running = False
        self.metrics_file = "results/metrics.jsonl"
        
        # 메트릭 저장 디렉토리 생성
        os.makedirs(os.path.dirname(self.metrics_file), exist_ok=True)
        
        # 이전 네트워크 통계 저장
        self._last_network_stats = psutil.net_io_counters()
        
    def collect_system_metrics(self) -> SystemMetrics:
        """시스템 메트릭 수집"""
        try:
            # CPU 사용률
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 메모리 사용률
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # 디스크 사용률
            disk = psutil.disk_usage('/')
            disk_usage_percent = (disk.used / disk.total) * 100
            
            # 네트워크 통계
            net_stats = psutil.net_io_counters()
            
            return SystemMetrics(
                timestamp=datetime.now().isoformat(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                disk_usage_percent=disk_usage_percent,
                network_bytes_sent=net_stats.bytes_sent,
                network_bytes_recv=net_stats.bytes_recv
            )
            
        except Exception as e:
            logger.error(f"시스템 메트릭 수집 실패: {e}")
            return None
    
    def collect_trading_metrics(self) -> TradingMetrics:
        """거래 메트릭 수집"""
        try:
            # 거래 로그 분석
            total_trades = 0
            successful_trades = 0
            failed_trades = 0
            total_profit = 0.0
            daily_profit = 0.0
            
            # 오늘 날짜
            today = datetime.now().date()
            
            # 실시간 거래 로그 읽기
            trade_log_files = [
                "results/trade_log.json",
                "results/realtime_trade_log.jsonl"
            ]
            
            for log_file in trade_log_files:
                if os.path.exists(log_file):
                    try:
                        if log_file.endswith('.jsonl'):
                            with open(log_file, 'r', encoding='utf-8') as f:
                                for line in f:
                                    if line.strip():
                                        trade = json.loads(line)
                                        total_trades += 1
                                        
                                        pnl = trade.get('pnl', 0)
                                        if pnl > 0:
                                            successful_trades += 1
                                        elif pnl < 0:
                                            failed_trades += 1
                                            
                                        total_profit += pnl
                                        
                                        # 오늘 거래 체크
                                        trade_date = datetime.fromisoformat(trade['timestamp']).date()
                                        if trade_date == today:
                                            daily_profit += pnl
                        else:
                            with open(log_file, 'r', encoding='utf-8') as f:
                                trades = json.load(f)
                                if isinstance(trades, list):
                                    for trade in trades:
                                        total_trades += 1
                                        pnl = trade.get('pnl', 0)
                                        total_profit += pnl
                                        
                    except Exception as e:
                        logger.error(f"거래 로그 분석 실패 ({log_file}): {e}")
            
            # 승률 계산
            win_rate = (successful_trades / total_trades * 100) if total_trades > 0 else 0
            
            # 포지션 및 포트폴리오 값은 실제 구현에 따라 조정 필요
            active_positions = 0  # 실제 포지션 데이터에서 가져와야 함
            portfolio_value = 10000000 + total_profit  # 초기 자본 + 총 손익
            
            return TradingMetrics(
                timestamp=datetime.now().isoformat(),
                total_trades=total_trades,
                successful_trades=successful_trades,
                failed_trades=failed_trades,
                total_profit=total_profit,
                daily_profit=daily_profit,
                win_rate=win_rate,
                active_positions=active_positions,
                portfolio_value=portfolio_value
            )
            
        except Exception as e:
            logger.error(f"거래 메트릭 수집 실패: {e}")
            return None
    
    def collect_error_metrics(self) -> ErrorMetrics:
        """에러 메트릭 수집"""
        try:
            # 로그 파일에서 에러 카운트
            api_errors = 0
            connection_errors = 0
            order_errors = 0
            data_errors = 0
            
            log_files = [
                "logs/trading-engine.log",
                "logs/dashboard.log",
                "results/alert_log.jsonl"
            ]
            
            # 최근 1시간 에러만 카운트
            one_hour_ago = datetime.now() - timedelta(hours=1)
            
            for log_file in log_files:
                if os.path.exists(log_file):
                    try:
                        with open(log_file, 'r', encoding='utf-8') as f:
                            for line in f:
                                if 'ERROR' in line or 'error' in line:
                                    # 간단한 에러 분류
                                    if 'api' in line.lower():
                                        api_errors += 1
                                    elif 'connection' in line.lower() or 'network' in line.lower():
                                        connection_errors += 1
                                    elif 'order' in line.lower():
                                        order_errors += 1
                                    elif 'data' in line.lower():
                                        data_errors += 1
                                        
                    except Exception as e:
                        logger.error(f"에러 로그 분석 실패 ({log_file}): {e}")
            
            total_errors = api_errors + connection_errors + order_errors + data_errors
            
            return ErrorMetrics(
                timestamp=datetime.now().isoformat(),
                api_errors=api_errors,
                connection_errors=connection_errors,
                order_errors=order_errors,
                data_errors=data_errors,
                total_errors=total_errors
            )
            
        except Exception as e:
            logger.error(f"에러 메트릭 수집 실패: {e}")
            return None
    
    def save_metrics(self, metrics: Dict[str, Any]):
        """메트릭을 파일에 저장"""
        try:
            with open(self.metrics_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(metrics, ensure_ascii=False) + '\n')
                
        except Exception as e:
            logger.error(f"메트릭 저장 실패: {e}")
    
    def generate_prometheus_metrics(self) -> str:
        """Prometheus 형식 메트릭 생성"""
        try:
            system_metrics = self.collect_system_metrics()
            trading_metrics = self.collect_trading_metrics()
            error_metrics = self.collect_error_metrics()
            
            metrics_text = []
            
            if system_metrics:
                metrics_text.extend([
                    f"# HELP trading_bot_cpu_percent CPU usage percentage",
                    f"# TYPE trading_bot_cpu_percent gauge",
                    f"trading_bot_cpu_percent {system_metrics.cpu_percent}",
                    f"",
                    f"# HELP trading_bot_memory_percent Memory usage percentage", 
                    f"# TYPE trading_bot_memory_percent gauge",
                    f"trading_bot_memory_percent {system_metrics.memory_percent}",
                    f""
                ])
            
            if trading_metrics:
                metrics_text.extend([
                    f"# HELP trading_bot_total_trades Total number of trades",
                    f"# TYPE trading_bot_total_trades counter",
                    f"trading_bot_total_trades {trading_metrics.total_trades}",
                    f"",
                    f"# HELP trading_bot_total_profit Total profit in KRW",
                    f"# TYPE trading_bot_total_profit gauge", 
                    f"trading_bot_total_profit {trading_metrics.total_profit}",
                    f"",
                    f"# HELP trading_bot_win_rate Win rate percentage",
                    f"# TYPE trading_bot_win_rate gauge",
                    f"trading_bot_win_rate {trading_metrics.win_rate}",
                    f""
                ])
            
            if error_metrics:
                metrics_text.extend([
                    f"# HELP trading_bot_total_errors Total error count",
                    f"# TYPE trading_bot_total_errors counter",
                    f"trading_bot_total_errors {error_metrics.total_errors}",
                    f""
                ])
            
            return '\n'.join(metrics_text)
            
        except Exception as e:
            logger.error(f"Prometheus 메트릭 생성 실패: {e}")
            return ""
    
    def run_collection_loop(self):
        """메트릭 수집 루프"""
        logger.info("메트릭 수집 시작...")
        
        while self.running:
            try:
                # 각종 메트릭 수집
                system_metrics = self.collect_system_metrics()
                trading_metrics = self.collect_trading_metrics()
                error_metrics = self.collect_error_metrics()
                
                # 종합 메트릭
                combined_metrics = {
                    "timestamp": datetime.now().isoformat(),
                    "system": asdict(system_metrics) if system_metrics else None,
                    "trading": asdict(trading_metrics) if trading_metrics else None,
                    "errors": asdict(error_metrics) if error_metrics else None
                }
                
                # 파일에 저장
                self.save_metrics(combined_metrics)
                
                # Prometheus 메트릭 파일 생성
                prometheus_metrics = self.generate_prometheus_metrics()
                if prometheus_metrics:
                    with open("results/metrics.prom", 'w', encoding='utf-8') as f:
                        f.write(prometheus_metrics)
                
                logger.info(f"메트릭 수집 완료 - "
                           f"CPU: {system_metrics.cpu_percent if system_metrics else 'N/A'}%, "
                           f"거래: {trading_metrics.total_trades if trading_metrics else 0}건, "
                           f"에러: {error_metrics.total_errors if error_metrics else 0}건")
                
                time.sleep(self.collection_interval)
                
            except Exception as e:
                logger.error(f"메트릭 수집 중 오류: {e}")
                time.sleep(10)  # 오류 시 10초 대기
    
    def start(self):
        """메트릭 수집 시작"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run_collection_loop, daemon=True)
            self.thread.start()
            logger.info("메트릭 수집기 시작됨")
    
    def stop(self):
        """메트릭 수집 중지"""
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join()
        logger.info("메트릭 수집기 중지됨")

def main():
    """메인 실행 함수"""
    collector = MetricsCollector(collection_interval=30)  # 30초마다 수집
    
    try:
        collector.start()
        
        # 메인 루프 - 종료 신호까지 대기
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("사용자 중단 신호 받음")
    finally:
        collector.stop()

if __name__ == "__main__":
    main()