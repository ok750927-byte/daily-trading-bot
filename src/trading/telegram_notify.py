"""
텔레그램 실시간 알림/모니터링 샘플
- 주문 체결, 잔고변동, 오류 발생 시 텔레그램 메시지 전송
- python-telegram-bot 필요
"""
import os
import requests

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')


def send_telegram_message(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print('[텔레그램] 환경변수 미설정')
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    try:
        resp = requests.post(url, data=data)
        if resp.status_code == 200:
            print('[텔레그램] 메시지 전송 성공')
        else:
            print(f'[텔레그램] 전송 실패: {resp.text}')
    except Exception as e:
        print(f'[텔레그램] 예외: {e}')

if __name__ == "__main__":
    send_telegram_message('자동매매 시스템 테스트 메시지')
