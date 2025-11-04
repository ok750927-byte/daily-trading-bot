
import json
import os
import time
import argparse

try:
    import pandas as pd
except Exception:
    pd = None


def send_telegram_message(msg):
    # 스텁: 실제 연동은 필요 시 구현
    return


def send_discord_message(msg):
    # 스텁
    return


def _load_trade_log(trade_log_path):
    """CSV 또는 JSON 포맷의 거래 로그를 안전하게 로드하여 DataFrame(또는 리스트) 반환."""
    if pd is None:
        # pandas가 없으면 JSON 배열 파일만 지원
        if trade_log_path.endswith('.json') and os.path.exists(trade_log_path):
            with open(trade_log_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    # pandas 사용 가능
    if trade_log_path.endswith('.csv'):
        return pd.read_csv(trade_log_path)
    elif trade_log_path.endswith('.json'):
        with open(trade_log_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return pd.DataFrame(data)
    else:
        # 시도해보기
        try:
            return pd.read_csv(trade_log_path)
        except Exception:
            try:
                with open(trade_log_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return pd.DataFrame(data)
            except Exception:
                return pd.DataFrame()


def analyze_performance(trade_log_path, report_dir):
    """간소화된 실적 분석 - pyinstaller 포함 배포에서 안정적으로 동작하도록 작성.

    입력: trade_log_path (csv 또는 json), report_dir
    출력: report_dir/performance_summary.json
    """
    if not os.path.exists(report_dir):
        os.makedirs(report_dir)

    print(f"분석 시작: {trade_log_path}")

    df = _load_trade_log(trade_log_path)

    if pd is None:
        # pandas가 없을 때는 최소한의 리포트 생성
        total_trades = len(df) if isinstance(df, list) else 0
        win_trades = sum(1 for r in df if r.get('profit', 0) > 0) if isinstance(df, list) else 0
        total_profit = sum(r.get('profit', 0) for r in df) if isinstance(df, list) else 0.0
        win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0.0
        summary = {
            'total_trades': int(total_trades),
            'win_rate': float(win_rate),
            'total_profit': float(total_profit),
            'message': 'pandas 미설치 - 간소화 리포트'
        }
    else:
        # pandas가 있는 경우 안전하게 통계 계산
        if df is None or df.empty:
            summary = {
                'total_trades': 0,
                'win_rate': 0.0,
                'total_profit': 0.0,
                'message': '거래 데이터 없음'
            }
        else:
            total_trades = int(len(df))
            win_trades = int((df['profit'] > 0).sum()) if 'profit' in df.columns else 0
            loss_trades = int((df['profit'] <= 0).sum()) if 'profit' in df.columns else 0
            win_rate = float(win_trades / total_trades * 100) if total_trades > 0 else 0.0
            total_profit = float(df['profit'].sum()) if 'profit' in df.columns else 0.0
            avg_profit = float(df['profit'].mean()) if 'profit' in df.columns else 0.0
            max_drawdown = float((df['balance'].cummax() - df['balance']).max()) if 'balance' in df.columns else 0.0
            volatility = float(df['profit'].std()) if 'profit' in df.columns else 0.0
            max_loss = float(df['profit'].min()) if 'profit' in df.columns else 0.0

            summary = {
                'total_trades': total_trades,
                'win_trades': win_trades,
                'loss_trades': loss_trades,
                'win_rate': win_rate,
                'total_profit': total_profit,
                'avg_profit': avg_profit,
                'max_drawdown': max_drawdown,
                'volatility': volatility,
                'max_loss': max_loss,
                'last_balance': float(df['balance'].iloc[-1]) if 'balance' in df.columns and not df.empty else 0.0
            }
            if 'strategy' in df.columns:
                strat_summary = df.groupby('strategy').agg(
                    trades=('profit', 'count'),
                    win_rate=('profit', lambda x: float((x > 0).mean() * 100)),
                    total_profit=('profit', 'sum'),
                    avg_profit=('profit', 'mean')
                ).reset_index()
                summary['strategy_stats'] = strat_summary.to_dict(orient='records')

    out_path = os.path.join(report_dir, 'performance_summary.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print('[실적분석] 간소화 버전 완료 - 리포트 생성:', out_path)


def analyze_performance_realtime(df, report_dir):
    """실시간(누적) 분석 - 간단히 현재까지의 통계만 생성한다."""
    if not os.path.exists(report_dir):
        os.makedirs(report_dir)

    # df는 pandas DataFrame일 가능성이 크다고 가정. 안전하게 처리.
    if pd is None or df is None or len(df) == 0:
        summary = {'total_trades': 0, 'total_profit': 0.0}
    else:
        total_trades = int(len(df))
        win_trades = int((df['profit'] > 0).sum()) if 'profit' in df.columns else 0
        total_profit = float(df['profit'].sum()) if 'profit' in df.columns else 0.0
        win_rate = float(win_trades / total_trades * 100) if total_trades > 0 else 0.0
        summary = {
            'total_trades': total_trades,
            'win_trades': win_trades,
            'win_rate': win_rate,
            'total_profit': total_profit
        }

    with open(os.path.join(report_dir, 'performance_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f'[실시간 모의투자] 거래 {summary.get("total_trades",0)}건 분석 완료 - 수익: {summary.get("total_profit",0.0):.2f}')


def simulate_realtime_performance(trade_log_path, report_dir, interval=5):
    """과거 거래 데이터를 순차적으로 재생하면서 analyze_performance_realtime를 호출한다."""
    print(f"[실시간 모의투자] 시작 - 간격: {interval}초")
    df = _load_trade_log(trade_log_path)

    if pd is None:
        # pandas가 없으면 단순 리스트 반복
        seq = df if isinstance(df, list) else []
        current = []
        for i, row in enumerate(seq):
            current.append(row)
            temp_dir = os.path.join(report_dir, f'realtime_trade_{i+1}')
            # write minimal summary
            analyze_performance_realtime(None, temp_dir)
            if i < len(seq) - 1:
                time.sleep(interval)
    else:
        full_df = df
        if full_df is None or full_df.empty:
            print('[실시간 모의투자] 재생할 거래 데이터 없음')
            return
        for i in range(len(full_df)):
            current_df = full_df.iloc[: i + 1]
            temp_report_dir = os.path.join(report_dir, f'realtime_trade_{i+1}')
            analyze_performance_realtime(current_df, temp_report_dir)
            if i < len(full_df) - 1:
                time.sleep(interval)

    print('[실시간 모의투자] 완료')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='실적 분석 및 실시간 모의투자')
    parser.add_argument('--realtime', action='store_true', help='실시간 모의투자 모드')
    parser.add_argument('--interval', type=int, default=5, help='실시간 모의투자 간격(초)')
    parser.add_argument('--trade_log', type=str, default='results/trade_log.json', help='거래 로그 파일 경로')
    parser.add_argument('--report_dir', type=str, default='results/performance_report', help='리포트 저장 디렉토리')

    args = parser.parse_args()

    if args.realtime:
        simulate_realtime_performance(args.trade_log, args.report_dir, args.interval)
    else:
        analyze_performance(args.trade_log, args.report_dir)
