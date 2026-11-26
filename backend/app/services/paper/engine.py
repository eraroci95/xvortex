"""Simulated trade arithmetic. Pure functions, exact Decimal. Long-only: no shorting, no margin.

Cash is rounded to 0.01, prices to 6 decimals, quantities to 8. Buying updates a volume-weighted
average entry price; selling realises profit against that average. Nothing here touches a database.
"""
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
PRICE_Q = Decimal("0.000001")
ZERO = Decimal("0.00")


class TradeError(ValueError):
    """The order cannot be filled (not enough cash or shares)."""


def money(x: Decimal) -> Decimal:
    return x.quantize(CENT, rounding=ROUND_HALF_UP)


def price_q(x: Decimal) -> Decimal:
    return x.quantize(PRICE_Q, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Position:
    quantity: Decimal
    avg_entry_price: Decimal
    realized_pnl: Decimal


@dataclass(frozen=True)
class Fill:
    cash: Decimal  # cash after the trade
    position: Position
    realized_pnl: Decimal | None  # this trade's profit; None for a buy
    gross: Decimal  # quantity x price, rounded to cents


def buy(cash: Decimal, pos: Position, quantity: Decimal, price: Decimal, fees: Decimal = ZERO) -> Fill:
    _check(quantity, price)
    gross = money(quantity * price)
    total = gross + fees
    if total > cash:
        raise TradeError(f"Not enough cash: this costs {total} and the account has {cash}.")
    new_qty = pos.quantity + quantity
    # Fees are not folded into the average: they reduce cash and are reported on the trade.
    avg = price_q((pos.quantity * pos.avg_entry_price + quantity * price) / new_qty)
    return Fill(money(cash - total), Position(new_qty, avg, pos.realized_pnl), None, gross)


def sell(cash: Decimal, pos: Position, quantity: Decimal, price: Decimal, fees: Decimal = ZERO) -> Fill:
    _check(quantity, price)
    if quantity > pos.quantity:
        raise TradeError(f"You hold {pos.quantity.normalize():f} and tried to sell {quantity.normalize():f}.")
    gross = money(quantity * price)
    pnl = money(quantity * (price - pos.avg_entry_price) - fees)
    new_qty = pos.quantity - quantity
    return Fill(
        money(cash + gross - fees),
        Position(new_qty, pos.avg_entry_price, money(pos.realized_pnl + pnl)),
        pnl, gross,
    )


def _check(quantity: Decimal, price: Decimal) -> None:
    if quantity <= 0:
        raise TradeError("Quantity must be positive.")
    if price <= 0:
        raise TradeError("Price must be positive.")


@dataclass(frozen=True)
class Valuation:
    market_value: Decimal
    cost_basis: Decimal
    unrealized_pnl: Decimal


def value_position(pos: Position, last_close: Decimal) -> Valuation:
    value = money(pos.quantity * last_close)
    cost = money(pos.quantity * pos.avg_entry_price)
    return Valuation(value, cost, money(value - cost))
