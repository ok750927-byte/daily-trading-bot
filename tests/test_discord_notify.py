import os
import pytest
import requests
from src.trading.discord_notify import send_discord_message

def test_send_discord_message_success(monkeypatch, requests_mock):
    monkeypatch.setenv('DISCORD_WEBHOOK_URL', 'https://discord.com/api/webhooks/dummy')
    requests_mock.post('https://discord.com/api/webhooks/dummy', status_code=204)
    send_discord_message('테스트 메시지')
    # 성공 메시지 출력만 확인

def test_send_discord_message_fail(monkeypatch, requests_mock):
    monkeypatch.setenv('DISCORD_WEBHOOK_URL', 'https://discord.com/api/webhooks/dummy')
    requests_mock.post('https://discord.com/api/webhooks/dummy', status_code=400, text='fail')
    send_discord_message('테스트 실패')
    # 실패 메시지 출력만 확인

def test_send_discord_message_no_env(monkeypatch):
    monkeypatch.delenv('DISCORD_WEBHOOK_URL', raising=False)
    send_discord_message('환경변수 없음')
    # 환경변수 미설정 메시지 출력만 확인
