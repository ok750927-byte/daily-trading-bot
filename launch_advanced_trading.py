"""
실제 모의거래를 위한 고도화 시스템 통합 실행 스크립트
"""
import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_prerequisites() -> bool:
    """시스템 사전 요구사항 체크"""
    try:
        print("🔍 사전 요구사항 체크...")

        # 1. 프로젝트 구조 확인
        required_dirs = ['src', 'data', 'results', 'logs']
        for dir_name in required_dirs:
            dir_path = project_root / dir_name
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
                print(f"   ✅ 디렉토리 생성: {dir_name}")
            else:
                print(f"   ✅ 디렉토리 확인: {dir_name}")

        # 2. 설정 파일 확인
        config_files = ['config.json', 'secrets.json']
        missing_configs = []

        for config_file in config_files:
            file_path = project_root / config_file
            if not file_path.exists():
                missing_configs.append(config_file)
                print(f"   ❌ 설정 파일 누락: {config_file}")
            else:
                print(f"   ✅ 설정 파일 확인: {config_file}")

        # 3. 필수 Python 패키지 확인
        required_packages = [
            'pandas', 'numpy', 'scikit-learn', 'matplotlib', 'seaborn',
            'requests', 'websocket-client', 'schedule'
        ]

        missing_packages = []
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
                print(f"   ✅ 패키지 확인: {package}")
            except ImportError:
                missing_packages.append(package)
                print(f"   ❌ 패키지 누락: {package}")

        # 4. 종합 결과
        if missing_configs or missing_packages:
            print(f"\n⚠️  사전 요구사항 미충족:")
            if missing_configs:
                print(f"   - 누락된 설정 파일: {missing_configs}")
            if missing_packages:
                print(f"   - 누락된 패키지: {missing_packages}")
            return False
        else:
            print(f"\n✅ 모든 사전 요구사항 충족")
            return True

    except Exception as e:
        logger.error(f"사전 요구사항 체크 실패: {e}")
        return False

def create_sample_config_files():
    """샘플 설정 파일 생성"""
    try:
        print("\n📝 샘플 설정 파일 생성...")

        # config.json 샘플
        config_sample = {
            "trading": {
                "initial_capital": 10000000,
                "max_positions": 5,
                "rebalance_frequency": "daily"
            },
            "risk_management": {
                "daily_loss_limit_pct": 0.02,
                "single_stock_limit_pct": 0.005,
                "stop_loss_pct": 0.05,
                "take_profit_pct": 0.10
            },
            "symbols": ["005930", "000660", "035420", "035720", "051910"],
            "logging": {
                "level": "INFO",
                "save_trades": true,
                "save_positions": true
            }
        }

        config_file = project_root / "config.json"
        if not config_file.exists():
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_sample, f, ensure_ascii=False, indent=2)
            print(f"   ✅ config.json 샘플 생성")

        # secrets.json 샘플 (실제 값은 사용자가 입력해야 함)
        secrets_sample = {
            "KIS_APP_KEY": "YOUR_APP_KEY_HERE",
            "KIS_APP_SECRET": "YOUR_APP_SECRET_HERE",
            "ACCOUNT_NUMBER": "YOUR_ACCOUNT_NUMBER_HERE",
            "DISCORD_WEBHOOK_URL": "YOUR_DISCORD_WEBHOOK_URL_HERE"
        }

        secrets_file = project_root / "secrets.json"
        if not secrets_file.exists():
            with open(secrets_file, 'w', encoding='utf-8') as f:
                json.dump(secrets_sample, f, ensure_ascii=False, indent=2)
            print(f"   ✅ secrets.json 샘플 생성")
            print(f"   ⚠️  secrets.json에 실제 API 키와 계좌 정보를 입력하세요!")

    except Exception as e:
        logger.error(f"샘플 설정 파일 생성 실패: {e}")

def create_sample_data():
    """샘플 데이터 생성 (테스트용)"""
    try:
        print("\n📊 샘플 데이터 생성...")

        symbols = ['005930', '000660', '035420', '035720', '051910']

        # 샘플 가격 데이터 생성
        import pandas as pd
        import numpy as np

        for symbol in symbols:
            data_file = project_root / "data" / "prices" / f"{symbol}.csv"

            if not data_file.exists():
                data_file.parent.mkdir(parents=True, exist_ok=True)

                # 1년간 샘플 데이터 생성
                dates = pd.date_range(start='2023-01-01', end='2024-10-31', freq='D')

                # 랜덤 가격 데이터 (실제로는 실제 데이터를 사용해야 함)
                np.random.seed(42)  # 재현 가능한 결과

                initial_price = np.random.uniform(10000, 100000)  # 초기 가격
                returns = np.random.normal(0.0005, 0.02, len(dates))  # 일간 수익률

                prices = [initial_price]
                for ret in returns[1:]:
                    prices.append(prices[-1] * (1 + ret))

                # 고가, 저가, 거래량 생성
                highs = [p * np.random.uniform(1.0, 1.05) for p in prices]
                lows = [p * np.random.uniform(0.95, 1.0) for p in prices]
                volumes = [np.random.randint(100000, 1000000) for _ in prices]

                df = pd.DataFrame({
                    'date': dates,
                    'open': prices,
                    'high': highs,
                    'low': lows,
                    'close': prices,
                    'volume': volumes
                })

                df.to_csv(data_file, index=False)
                print(f"   ✅ 샘플 데이터 생성: {symbol}")

        # 샘플 ML 예측 데이터 생성
        pred_file = project_root / "results" / "predictions.json"
        if not pred_file.exists():
            pred_file.parent.mkdir(parents=True, exist_ok=True)

            predictions = []
            for symbol in symbols:
                for i in range(100):  # 100일간 예측
                    date = (datetime.now() - timedelta(days=100-i)).strftime('%Y-%m-%d')

                    predictions.append({
                        'date': date,
                        'code': symbol,
                        'prediction': np.random.uniform(0.2, 0.8),
                        'confidence': np.random.uniform(0.6, 0.9)
                    })

            with open(pred_file, 'w', encoding='utf-8') as f:
                json.dump(predictions, f, ensure_ascii=False, indent=2)

            print(f"   ✅ 샘플 ML 예측 데이터 생성")

    except Exception as e:
        logger.error(f"샘플 데이터 생성 실패: {e}")

def run_system_tests() -> bool:
    """시스템 테스트 실행"""
    try:
        print("\n🧪 시스템 테스트 실행...")

        # 1. 고급 백테스팅 테스트
        print("   📊 고급 백테스팅 테스트...")
        try:
            from src.analysis.advanced_backtesting import AdvancedBacktester

            backtester = AdvancedBacktester()
            symbols = ['005930', '000660']  # 테스트용 2개 종목

            # 짧은 기간 테스트
            results = backtester.run_multi_symbol_backtest(
                symbols, '2024-01-01', '2024-10-31'
            )

            if results:
                print(f"      ✅ 백테스팅 성공: {len(results)}개 종목")
            else:
                print(f"      ❌ 백테스팅 실패")
                return False

        except Exception as e:
            print(f"      ❌ 백테스팅 테스트 실패: {e}")
            return False

        # 2. 포트폴리오 최적화 테스트
        print("   💼 포트폴리오 최적화 테스트...")
        try:
            from src.analysis.portfolio_optimization import PortfolioOptimizer

            optimizer = PortfolioOptimizer()
            returns_df = optimizer.load_returns_data(symbols, '2024-01-01', '2024-10-31')

            if not returns_df.empty:
                expected_returns = optimizer.calculate_expected_returns(returns_df)
                cov_matrix = optimizer.calculate_covariance_matrix(returns_df)

                opt_result = optimizer.optimize_portfolio(
                    expected_returns, cov_matrix, method='max_sharpe'
                )

                if opt_result.get('success', False):
                    print(f"      ✅ 포트폴리오 최적화 성공")
                else:
                    print(f"      ❌ 포트폴리오 최적화 실패")
                    return False
            else:
                print(f"      ❌ 수익률 데이터 로드 실패")
                return False

        except Exception as e:
            print(f"      ❌ 포트폴리오 최적화 테스트 실패: {e}")
            return False

        # 3. 거래 엔진 기본 테스트
        print("   🚀 거래 엔진 기본 테스트...")
        try:
            from src.trading.live_trading_engine import LiveTradingEngine

            engine = LiveTradingEngine()

            # 기본 설정 확인
            if hasattr(engine, 'config') and hasattr(engine, 'secrets'):
                print(f"      ✅ 거래 엔진 초기화 성공")
            else:
                print(f"      ❌ 거래 엔진 초기화 실패")
                return False

        except Exception as e:
            print(f"      ❌ 거래 엔진 테스트 실패: {e}")
            return False

        print(f"\n✅ 모든 시스템 테스트 통과")
        return True

    except Exception as e:
        logger.error(f"시스템 테스트 실패: {e}")
        return False

def display_system_overview():
    """시스템 개요 표시"""
    print("\n" + "="*60)
    print("🚀 실제 모의거래 고도화 시스템 v2.0")
    print("="*60)
    print()
    print("📋 주요 기능:")
    print("   • 실시간 모의거래 엔진 (한국투자증권 API)")
    print("   • 고급 백테스팅 시스템")
    print("   • 포트폴리오 최적화")
    print("   • 실시간 시장 데이터 수신")
    print("   • 자동 리밸런싱")
    print("   • 리스크 관리 시스템")
    print("   • 성과 모니터링 및 리포팅")
    print()
    print("⚠️  중요 주의사항:")
    print("   • 이 시스템은 실제 모의거래를 수행합니다")
    print("   • 실제 거래 전 충분한 테스트가 필요합니다")
    print("   • API 키와 계좌 정보를 정확히 설정하세요")
    print("   • 리스크 한도를 적절히 설정하세요")
    print()

def main():
    """메인 실행 함수"""
    display_system_overview()

    # 1. 사전 요구사항 체크
    if not check_prerequisites():
        print("\n❌ 사전 요구사항 미충족")

        # 샘플 파일 생성 제안
        create_sample = input("\n샘플 설정 파일과 데이터를 생성하시겠습니까? (y/N): ").strip().lower()
        if create_sample == 'y':
            create_sample_config_files()
            create_sample_data()

            print("\n📝 설정 완료 후 다시 실행하세요:")
            print("   1. secrets.json에 실제 API 키와 계좌 정보 입력")
            print("   2. config.json에서 거래 설정 조정")
            print("   3. 실제 가격 데이터로 data/prices/ 파일들 교체")

        return

    # 2. 시스템 테스트
    print("\n🧪 시스템 테스트를 실행하시겠습니까? (권장)")
    run_tests = input("테스트 실행 (y/N): ").strip().lower()

    if run_tests == 'y':
        if not run_system_tests():
            print("\n❌ 시스템 테스트 실패")
            print("문제를 해결한 후 다시 실행하세요.")
            return

    # 3. 실행 모드 선택
    print("\n🔧 실행 모드 선택:")
    print("1. 백테스팅만 실행")
    print("2. 포트폴리오 최적화만 실행")
    print("3. 실시간 모의거래 실행 (전체 시스템)")
    print("4. 시스템 종료")

    choice = input("\n선택 (1-4): ").strip()

    if choice == '1':
        print("\n📊 고급 백테스팅 실행...")
        try:
            from src.analysis.advanced_backtesting import AdvancedBacktester
            backtester = AdvancedBacktester()

            symbols = ['005930', '000660', '035420', '035720', '051910']
            results = backtester.run_multi_symbol_backtest(symbols, '2023-01-01', '2024-10-31')

            if results:
                report = backtester.create_performance_report(results)
                print("\n" + report)
                backtester.save_results(results, report)
                print("\n✅ 백테스팅 완료! 결과가 results/advanced_backtest/에 저장되었습니다.")
            else:
                print("❌ 백테스팅 실패")

        except Exception as e:
            print(f"❌ 백테스팅 오류: {e}")

    elif choice == '2':
        print("\n💼 포트폴리오 최적화 실행...")
        try:
            from src.analysis.portfolio_optimization import PortfolioOptimizer
            optimizer = PortfolioOptimizer()

            symbols = ['005930', '000660', '035420', '035720', '051910']
            returns_df = optimizer.load_returns_data(symbols, '2023-01-01', '2024-10-31')

            if not returns_df.empty:
                result = optimizer.backtest_strategy(returns_df, 'max_sharpe')
                if result:
                    report = optimizer.create_portfolio_report(result, symbols)
                    print("\n" + report)
                    optimizer.save_results(result, report, symbols)
                    print("\n✅ 포트폴리오 최적화 완료! 결과가 results/portfolio_optimization/에 저장되었습니다.")
                else:
                    print("❌ 포트폴리오 최적화 실패")
            else:
                print("❌ 데이터 로드 실패")

        except Exception as e:
            print(f"❌ 포트폴리오 최적화 오류: {e}")

    elif choice == '3':
        print("\n⚠️  실시간 모의거래를 시작합니다!")
        print("이 작업은 실제 모의거래 API를 사용하여 자동 거래를 수행합니다.")

        final_confirm = input("\n정말로 실시간 모의거래를 시작하시겠습니까? (yes/no): ").strip().lower()

        if final_confirm == 'yes':
            try:
                from scripts.live_trading_orchestrator import LiveTradingOrchestrator

                orchestrator = LiveTradingOrchestrator()
                orchestrator.start()

            except Exception as e:
                print(f"❌ 실시간 거래 시스템 오류: {e}")
        else:
            print("실시간 거래 시작 취소")

    elif choice == '4':
        print("시스템 종료")

    else:
        print("잘못된 선택입니다.")

if __name__ == "__main__":
    main()
