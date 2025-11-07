import json
import os
from datetime import datetime
import time
import argparse
# import pandas as pd  # 함수 내부에서 import

def analyze_performance(trade_log_path, report_dir):
    """
    실매매 거래내역 분석 (pandas 함수 내부 import 버전)
    """
    import pandas as pd  # 함수 내부에서 import하여 pyinstaller 호환성 향상

    if not os.path.exists(report_dir):
        os.makedirs(report_dir)

    print(f"분석 시작: {trade_log_path}")

    # pandas를 사용한 간단한 데이터 처리
    try:
        if trade_log_path.endswith('.csv'):
            df = pd.read_csv(trade_log_path)
        else:
            with open(trade_log_path, 'r', encoding='utf-8') as f:
                df = pd.DataFrame(json.load(f))

        total_trades = len(df)
        total_profit = df['profit'].sum() if 'profit' in df.columns else 0
        win_rate = (df['profit'] > 0).mean() * 100 if not df.empty else 0

        summary = {
            'total_trades': int(total_trades),
            'win_rate': float(win_rate),
            'total_profit': float(total_profit),
            'message': 'pandas 함수 내부 import 버전'
        }
    except Exception as e:
        print(f"데이터 로드 오류: {e}")
        summary = {
            'total_trades': 0,
            'win_rate': 0.0,
            'total_profit': 0.0,
            'message': f'오류: {str(e)}'
        }

    with open(os.path.join(report_dir, 'performance_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print('[실적분석] pandas 함수 내부 import 버전 완료')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='실적 분석 및 실시간 모의투자')
    parser.add_argument('--realtime', action='store_true', help='실시간 모의투자 모드')
    parser.add_argument('--interval', type=int, default=5, help='실시간 모의투자 간격(초)')
    parser.add_argument('--trade_log', type=str, default='results/trade_log.json', help='거래 로그 파일 경로')
    parser.add_argument('--report_dir', type=str, default='results/performance_report', help='리포트 저장 디렉토리')

    args = parser.parse_args()

    if args.realtime:
        print("실시간 모의투자 모드 시작...")
        while True:
            analyze_performance(args.trade_log, args.report_dir)
            time.sleep(args.interval)
    else:
        analyze_performance(args.trade_log, args.report_dir)
