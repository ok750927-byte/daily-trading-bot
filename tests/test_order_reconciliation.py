from src.trading.korea_investment_order import KoreaInvestmentAPI


def test_wait_for_fill_dryrun():
    api = KoreaInvestmentAPI()
    api.dry_run = True
    # simulate sending order
    res = api.send_order('005930', 1, 1000, side='buy')
    assert isinstance(res, dict)
    order_id = res.get('order_id')
    assert order_id is not None
    status = api.wait_for_fill(order_id, timeout=2, poll_interval=0.1)
    assert isinstance(status, dict)
    assert status.get('status') == 'filled'
