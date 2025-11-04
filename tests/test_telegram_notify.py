import os
import pytest
import requests
from src.trading.telegram_notify import send_telegram_message

def test_send_telegram_message_success(monkeypatch, requests_mock):
    monkeypatch.setenv('TELEGRAM_BOT_TOKEN', 'dummy_token')
    monkeypatch.setenv('TELEGRAM_CHAT_ID', '123456')
    requests_mock.post('https://api.telegram.org/botdummy_token/sendMessage', status_code=200)
    send_telegram_message('테스트 메시지')
    # 성공 메시지 출력만 확인

def test_send_telegram_message_fail(monkeypatch, requests_mock):
    monkeypatch.setenv('TELEGRAM_BOT_TOKEN', 'dummy_token')
    monkeypatch.setenv('TELEGRAM_CHAT_ID', '123456')
    requests_mock.post('https://api.telegram.org/botdummy_token/sendMessage', status_code=400, text='fail')
    send_telegram_message('테스트 실패')
    # 실패 메시지 출력만 확인

def test_send_telegram_message_no_env(monkeypatch):
    monkeypatch.delenv('TELEGRAM_BOT_TOKEN', raising=False)
    monkeypatch.delenv('TELEGRAM_CHAT_ID', raising=False)
    send_telegram_message('환경변수 없음')
    # 환경변수 미설정 메시지 출력만 확인
