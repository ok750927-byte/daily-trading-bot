import pytest
from src.trading.risk_manager import RiskManager


def test_min_cash_reserve_blocks_buy():
    rm = RiskManager(account_equity=1_000_000, config={"min_cash_reserve": 500_000})
    res = rm.check_order(symbol="0001", qty=10, price=10000, side="buy", current_positions={}, cash=400_000)
    assert not res.allowed
    assert "보유 현금 부족" in (res.reason or "")


def test_max_position_exposure_blocks():
    rm = RiskManager(account_equity=1_000_000, config={"max_position_exposure": 0.1})
    # trying to buy that exceeds 10% exposure
    res = rm.check_order(symbol="0001", qty=200, price=1000, side="buy", current_positions={}, cash=1_000_000)
    assert not res.allowed
    assert "종목 노출 한도 초과" in (res.reason or "")


def test_projected_daily_loss_blocks():
    rm = RiskManager(account_equity=1_000_000, config={"max_account_loss": 10000})
    res = rm.check_order(symbol="0001", qty=1, price=100, side="sell", current_positions={}, cash=100000, projected_daily_loss=15000)
    assert not res.allowed
    assert "일일 손실 한도 초과" in (res.reason or "")
