import json
import os
from datetime import datetime
try:
    import FinanceDataReader as fdr
except Exception:
    fdr = None

def get_stock_name(code):
    """
    종목 코드로 종목명을 조회합니다.
    """
    try:
        # FinanceDataReader를 사용하여 KRX 전체 종목 정보 조회
        df_krx = fdr.StockListing('KRX')
        stock_info = df_krx[df_krx['Code'] == code]
        if not stock_info.empty:
            return stock_info.iloc[0]['Name']
    except Exception as e:
        print(f"[WARNING] 종목명 조회 실패 ({code}): {e}")
    return code  # 조회 실패 시 코드 그대로 반환

def create_report(prediction_path, report_path):
    """
    예측 결과 JSON 파일을 읽어 세련된 HTML 보고서를 생성합니다.
    """
    print("HTML 보고서 생성을 시작합니다...")
    
    # 종목 코드를 종목명으로 변환하는 딕셔너리 (확장된 버전)
    stock_names = {
        '005930': '삼성전자',
        '000660': 'SK하이닉스',
        '035720': '카카오',
        '005380': '현대차',
        '000270': '기아',
        '005490': 'POSCO홀딩스',
        '035420': 'NAVER',
        '051910': 'LG화학',
        '006400': '삼성SDI',
        '012330': '현대모비스',
        '028260': '삼성물산',
        '096770': 'SK이노베이션',
        '207940': '삼성바이오로직스',
        '066570': 'LG전자',
        '003670': '포스코퓨처엠',
        '323410': '카카오뱅크',
        '000810': '삼성화재',
        '017670': 'SK텔레콤',
        '034730': 'SK',
        '086790': '하나금융지주',
        '003550': 'LG',
        '105560': 'KB금융',
        '055550': '신한지주',
        '018260': '삼성에스디에스',
        '015760': '한국전력',
        '032830': '삼성생명',
        '010130': '고려아연',
        '009150': '삼성전기',
        '011200': 'HMM',
        '003490': '대한항공',
        '196170': '알테오젠',
        '069500': 'KODEX 200',
        '373220': 'LG에너지솔루션',
        '005935': '삼성전자우',
        '034020': '두산에너빌리티',
        '329180': '현대중공업',
        '012450': '한화에어로스페이스',
        '068270': '셀트리온',
        '042660': '한화오션',
        '402340': 'SK스퀘어',
        '009540': 'HD한국조선해양',
        '267260': '현대일렉트릭',
        '010140': '삼성중공업',
        '064350': '현대로템',
        '000080': '하이트진로',
        '033780': 'KT&G',
        '009830': '한화솔루션',
        '047810': '한국항공우주',
        '010950': 'S-Oil',
        '001570': '금양',
        '024110': '기업은행',
        '138930': 'BNK금융지주',
        '139480': '이마트'
    }

    # 1. 예측 파일 읽기
    try:
        with open(prediction_path, 'r', encoding='utf-8') as f:
            predictions = json.load(f)
    except FileNotFoundError:
        print(f"[ERROR] 예측 파일({prediction_path})을 찾을 수 없습니다. 먼저 예측을 생성해주세요.")
        # 빈 보고서라도 생성하기 위해 기본 구조 사용
        predictions = {}

    # 2. 보고서 내용 생성
    prediction_date = predictions.get('prediction_date', (datetime.now()).strftime('%Y-%m-%d'))
    recommendations = predictions.get('recommendations', [])

    # 추천 종목 테이블 생성
    if recommendations:
        # KRX 종목 리스트를 한 번만 조회 (성능 최적화)
        try:
            df_krx = fdr.StockListing('KRX')
            print(f"KRX 종목 리스트 조회 완료 ({len(df_krx)}개 종목)")
        except Exception as e:
            print(f"[WARNING] KRX 종목 리스트 조회 실패: {e}")
            df_krx = None
        
        # 신뢰도(up_probability) 높은 순으로 정렬
        sorted_recommendations = sorted(recommendations, key=lambda x: x.get('up_probability', 0), reverse=True)
        
        rows = ""
        for i, item in enumerate(sorted_recommendations, 1):
            code = item.get('code', 'N/A')
            
            # 종목명 조회 (실시간 or 딕셔너리)
            if df_krx is not None:
                try:
                    stock_info = df_krx[df_krx['Code'] == code]
                    stock_name = stock_info.iloc[0]['Name'] if not stock_info.empty else stock_names.get(code, code)
                except:
                    stock_name = stock_names.get(code, code)
            else:
                stock_name = stock_names.get(code, code)
            
            price = item.get('last_close_price', 0)
            up_prob = item.get('up_probability', 0)
            estimated_gain = item.get('estimated_gain_rate', 0)
            reasons = item.get('reasons', [])
            
            # 상승 이유를 HTML 리스트로 변환
            reasons_html = "<br>".join([f"• {reason}" for reason in reasons])
            
            rows += f"""
            <tr>
                <td style="text-align: center;">{i}</td>
                <td style="text-align: center;">{code}</td>
                <td style="font-weight: 600;">{stock_name}</td>
                <td style="text-align: right;">{price:,.0f}원</td>
                <td style="text-align: center; color: #e74c3c; font-weight: 600;">+{estimated_gain:.1f}%</td>
                <td style="text-align: center; color: #27ae60;">{up_prob:.1f}%</td>
                <td style="font-size: 0.9em; line-height: 1.4;">{reasons_html}</td>
            </tr>"""
        recommendation_html = f"""
        <h2>🎯 AI 추천 종목</h2>
        <table>
            <thead>
                <tr>
                    <th style="width: 5%; text-align: center;">No.</th>
                    <th style="width: 10%; text-align: center;">종목코드</th>
                    <th style="width: 10%;">종목명</th>
                    <th style="width: 12%; text-align: right;">현재가</th>
                    <th style="width: 10%; text-align: center;">예상 상승률</th>
                    <th style="width: 10%; text-align: center;">신뢰도</th>
                    <th style="width: 43%;">상승 예상 이유</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        <p class="info">
            <strong>📊 참고사항</strong><br>
            • <strong>예상 상승률</strong>: AI 모델의 신뢰도를 기반으로 추정한 단기 상승 가능성<br>
            • <strong>신뢰도</strong>: 모델이 해당 종목의 상승을 예측한 확률<br>
            • 위 정보는 투자 참고용이며, 실제 투자 결정은 신중히 하시기 바랍니다.
        </p>
        """
    else:
        recommendation_html = """
        <h2>🎯 AI 추천 종목</h2>
        <div class="no-recommendation">
            <p>금일 AI 모델의 추천 종목이 없습니다.</p>
            <p class="info">* 시장 상황을 관망하거나 보수적인 접근이 필요할 수 있습니다.</p>
        </div>
        """

    # 전체 HTML 구조
    html_content = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>주식 자동매매 일일 보고서</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 20px auto;
            padding: 0 20px;
            background-color: #f4f7f6;
        }}
        .container {{
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            padding: 30px 40px;
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.08);
        }}
        h1 {{
            text-align: center;
            font-size: 2.2em;
            margin-bottom: 10px;
            color: #2c3e50;
        }}
        .date {{
            text-align: center;
            color: #7f8c8d;
            font-size: 1.1em;
            margin-bottom: 40px;
        }}
        h2 {{
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
            font-size: 1.5em;
            color: #2c3e50;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th, td {{
            padding: 12px 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #34495e;
            color: white;
            font-weight: 600;
            font-size: 0.95em;
        }}
        tbody tr:hover {{
            background-color: #f0f8ff;
        }}
        tbody tr {{
            transition: background-color 0.2s;
        }}
        .info {{
            margin-top: 20px;
            font-size: 0.9em;
            color: #555;
            background-color: #ecf8ff;
            border: 1px solid #bde0fe;
            padding: 15px;
            border-radius: 5px;
        }}
        .no-recommendation {{
            margin-top: 20px;
            padding: 20px;
            text-align: center;
            background-color: #f9f9f9;
            border: 1px dashed #ccc;
            border-radius: 5px;
        }}
        .no-recommendation p {{
            margin: 0;
            font-size: 1.1em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>주식 자동매매 일일 보고서</h1>
        <p class="date">예측 기준일: {prediction_date}</p>
        {recommendation_html}
    </div>
</body>
</html>
"""

    # 3. 보고서 파일 저장
    try:
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"HTML 보고서를 '{report_path}'에 성공적으로 저장했습니다.")

    except Exception as e:
        print(f"[ERROR] 보고서 저장 중 오류가 발생했습니다: {e}")


if __name__ == '__main__':
    # 테스트용 실행 코드 (워크스페이스 루트 자동 탐색)
    def find_workspace_root():
        env = os.environ.get('DAILY_TRADING_WORKSPACE')
        if env and os.path.isdir(env):
            return os.path.abspath(env)
        try:
            cur = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        except Exception:
            cur = os.getcwd()
        markers = ('pyproject.toml', 'README.md', 'requirements.txt', '.git')
        root = cur
        while True:
            for m in markers:
                if os.path.exists(os.path.join(root, m)):
                    return os.path.abspath(root)
            parent = os.path.dirname(root)
            if parent == root:
                break
            root = parent
        return os.path.abspath(cur)

    PROJ_DIR = find_workspace_root()

    # 1. 추천 종목이 있는 경우 테스트
    PREDICTION_PATH_1 = os.path.join(PROJ_DIR, 'results', 'predictions_sample.json')
    REPORT_PATH_1 = os.path.join(PROJ_DIR, 'results', 'daily_report_sample.html')

    sample_predictions = {
        "prediction_date": "2025-10-29",
        "recommendations": [
            {"code": "005930", "last_close_price": 85000},
            {"code": "000660", "last_close_price": 130000}
        ]
    }
    os.makedirs(os.path.dirname(PREDICTION_PATH_1), exist_ok=True)
    with open(PREDICTION_PATH_1, 'w', encoding='utf-8') as f:
        json.dump(sample_predictions, f, indent=4)

    create_report(
        prediction_path=PREDICTION_PATH_1,
        report_path=REPORT_PATH_1
    )

    # 2. 추천 종목이 없는 경우 테스트
    PREDICTION_PATH_2 = os.path.join(PROJ_DIR, 'results', 'predictions_empty.json')
    REPORT_PATH_2 = os.path.join(PROJ_DIR, 'results', 'daily_report_empty.html')

    empty_predictions = {
        "prediction_date": "2025-10-29",
        "recommendations": []
    }
    with open(PREDICTION_PATH_2, 'w', encoding='utf-8') as f:
        json.dump(empty_predictions, f, indent=4)

    create_report(
        prediction_path=PREDICTION_PATH_2,
        report_path=REPORT_PATH_2
    )
