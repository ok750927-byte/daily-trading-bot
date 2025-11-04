import pytest
from src.trading.korea_investment_order import KoreaInvestmentAPI

class DummyAPI(KoreaInvestmentAPI):
    def __init__(self):
        self.appkey = 'dummy'
        self.appsecret = 'dummy'
        self.access_token = 'dummy_token'
    def get_balance(self):
        return {'balance': 'ok'}
    def send_order(self, symbol, qty, price, side='buy'):
        return {'result': 'ok'}
    def monitor_orders(self):
        return {'monitor': 'ok'}

def test_monitor_orders():
    api = DummyAPI()
    result = api.monitor_orders()
    assert result == {'monitor': 'ok'}

def test_send_order():
    api = DummyAPI()
    resp = api.send_order('005930', 1, 70000, side='buy')
    assert resp['result'] == 'ok'

def test_get_balance():
    api = DummyAPI()
    resp = api.get_balance()
    assert resp['balance'] == 'ok'
