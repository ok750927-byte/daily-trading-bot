"""
디스코드 실시간 알림/리포트 전송 모듈 (샘플)
- Discord Webhook URL 필요
- 주문 체결, 잔고변동, 리포트, 장애 발생 시 디스코드 메시지 전송
"""
import os
import requests

def send_discord_message(text):
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    if not webhook_url:
        print('[디스코드] Webhook URL 미설정')
        return
    data = {"content": text}
    try:
        resp = requests.post(webhook_url, json=data)
        if resp.status_code == 204:
            print('[디스코드] 메시지 전송 성공')
        else:
            print(f'[디스코드] 전송 실패: {resp.text}')
    except Exception as e:
        print(f'[디스코드] 예외: {e}')

if __name__ == "__main__":
    send_discord_message('자동매매 시스템 디스코드 테스트 메시지')
