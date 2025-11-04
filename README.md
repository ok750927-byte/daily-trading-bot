# trading-bot

주식 자동매매 프로젝트 초기 레포. Phase1(환경설정) 템플릿과 예제 파일을 포함합니다.

구성:
- `src/` : 소스 코드
- `tests/` : 단위/통합 테스트

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
