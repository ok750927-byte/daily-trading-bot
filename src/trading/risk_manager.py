"""Risk management helpers for position sizing and constraint checks.

This module is intentionally small and focused for the MVP: it exposes a
RiskManager class that RealtimeTrader or OrderManager can call before placing
orders. It supports dry-run friendly behavior and emits human-friendly error
messages for why an order was rejected.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass
class RiskResult:
    allowed: bool
    reason: Optional[str] = None


class RiskManager:
    """Simple rule-based risk manager.

    Rules included (configurable / simple defaults):
    - max_account_loss: absolute KRW loss per day
    - max_position_exposure: fraction of account equity per symbol
    - min_cash_reserve: minimum cash to keep
    """

    def __init__(self, account_equity: float, config: Optional[Dict] = None) -> None:
        self.account_equity = account_equity
        self.config = config or {}
        self.max_account_loss = float(self.config.get("max_account_loss", account_equity * 0.05))
        self.max_position_exposure = float(self.config.get("max_position_exposure", 0.2))
        self.min_cash_reserve = float(self.config.get("min_cash_reserve", 100000))

    def check_order(self, symbol: str, qty: int, price: float, side: str, current_positions: Dict[str, float], cash: float, projected_daily_loss: float = 0.0) -> RiskResult:
        """Return whether the order should be allowed and a reason if not.

        current_positions: mapping symbol->position_value (positive for long)
        cash: current available cash balance
        """
        # simple exposure check: new position value / equity
        try:
            order_value = abs(qty) * float(price)
        except Exception:
            return RiskResult(False, "Invalid price/qty")

        # check cash reserve
        if side.lower() == "buy":
            if cash - order_value < self.min_cash_reserve:
                return RiskResult(False, "보유 현금 부족(최소 보유고 유지 필요)")

        exposure = (current_positions.get(symbol, 0.0) + (order_value if side.lower() == "buy" else -order_value)) / max(1.0, self.account_equity)
        if abs(exposure) > self.max_position_exposure:
            return RiskResult(False, f"종목 노출 한도 초과: {exposure:.2%} > {self.max_position_exposure:.2%}")

        # daily loss check: if a projected_daily_loss is provided, compare against max
        try:
            proj_loss = float(projected_daily_loss or 0.0)
        except Exception:
            proj_loss = 0.0
        if proj_loss > self.max_account_loss:
            return RiskResult(False, f"일일 손실 한도 초과 예정: {proj_loss} > {self.max_account_loss}")

        return RiskResult(True, None)


def example_usage() -> None:
    rm = RiskManager(account_equity=10_000_000)
    res = rm.check_order(symbol="005930", qty=1, price=70000, side="buy", current_positions={}, cash=1000000)
    print(res)


if __name__ == "__main__":
    example_usage()
