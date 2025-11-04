import os
import pytest
from src.trading.korea_investment_order import KoreaInvestmentAPI

def test_env_variables_exist(monkeypatch):
    monkeypatch.setenv('KOREA_APP_KEY', 'dummy')
    monkeypatch.setenv('KOREA_APP_SECRET', 'dummy')
    monkeypatch.setenv('KOREA_ACCOUNT_NO', '12345678')
    monkeypatch.setenv('KOREA_ACCOUNT_PRDT', '01')
    api = KoreaInvestmentAPI()
    assert api.appkey == 'dummy'
    assert api.appsecret == 'dummy'

def test_get_access_token(monkeypatch, requests_mock):
    monkeypatch.setenv('KOREA_APP_KEY', 'dummy')
    monkeypatch.setenv('KOREA_APP_SECRET', 'dummy')
    monkeypatch.setenv('KOREA_ACCOUNT_NO', '12345678')
    monkeypatch.setenv('KOREA_ACCOUNT_PRDT', '01')
    # Mock token endpoint
    requests_mock.post('https://openapi.koreainvestment.com:9443/oauth2/tokenP', json={'access_token': 'testtoken'})
    api = KoreaInvestmentAPI()
    # call get_access_token explicitly (KoreaInvestmentAPI uses lazy token fetch)
    token = api.get_access_token()
    assert token == 'testtoken'
    assert api.access_token == 'testtoken'

def test_send_order(monkeypatch, requests_mock):
    monkeypatch.setenv('KOREA_APP_KEY', 'dummy')
    monkeypatch.setenv('KOREA_APP_SECRET', 'dummy')
    monkeypatch.setenv('KOREA_ACCOUNT_NO', '12345678')
    monkeypatch.setenv('KOREA_ACCOUNT_PRDT', '01')
    requests_mock.post('https://openapi.koreainvestment.com:9443/oauth2/tokenP', json={'access_token': 'testtoken'})
    requests_mock.post('https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/trading/order-cash', status_code=200, json={'result':'ok'})
    api = KoreaInvestmentAPI()
    resp = api.send_order('005930', 1, 70000, side='buy')
    assert resp['result'] == 'ok'

def test_get_balance(monkeypatch, requests_mock):
    monkeypatch.setenv('KOREA_APP_KEY', 'dummy')
    monkeypatch.setenv('KOREA_APP_SECRET', 'dummy')
    monkeypatch.setenv('KOREA_ACCOUNT_NO', '12345678')
    monkeypatch.setenv('KOREA_ACCOUNT_PRDT', '01')
    requests_mock.post('https://openapi.koreainvestment.com:9443/oauth2/tokenP', json={'access_token': 'testtoken'})
    requests_mock.get('https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/trading/inquire-balance', status_code=200, json={'balance':'ok'})
    api = KoreaInvestmentAPI()
    resp = api.get_balance()
    assert resp['balance'] == 'ok'
