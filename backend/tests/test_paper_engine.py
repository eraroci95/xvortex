from decimal import Decimal as D

import pytest

from app.services.paper.engine import Position, TradeError, buy, sell, value_position

EMPTY = Position(D(0), D(0), D("0.00"))


def test_first_buy_sets_average_and_reduces_cash():
    f = buy(D("1000.00"), EMPTY, D(10), D("12.50"))
    assert f.cash == D("875.00") and f.position.quantity == D(10) and f.position.avg_entry_price == D("12.500000")
    assert f.realized_pnl is None and f.gross == D("125.00")


def test_second_buy_uses_weighted_average():
    p = buy(D("1000"), EMPTY, D(10), D("10")).position
    f = buy(D("900"), p, D(30), D("20"))
    assert f.position.quantity == D(40) and f.position.avg_entry_price == D("17.500000")


def test_cannot_spend_more_than_cash():
    with pytest.raises(TradeError, match="Not enough cash"):
        buy(D("99.99"), EMPTY, D(10), D("10"))
    assert buy(D("100.00"), EMPTY, D(10), D("10")).cash == D("0.00")  # exactly enough is fine


def test_sell_realises_profit_against_average_and_keeps_average():
    p = Position(D(40), D("17.5"), D("5.00"))
    f = sell(D("0"), p, D(10), D("20"))
    assert f.realized_pnl == D("25.00") and f.cash == D("200.00")
    assert f.position.quantity == D(30) and f.position.avg_entry_price == D("17.5") and f.position.realized_pnl == D("30.00")


def test_sell_at_a_loss_and_with_fees():
    p = Position(D(10), D("10"), D("0.00"))
    f = sell(D("0"), p, D(10), D("9"), fees=D("1.00"))
    assert f.realized_pnl == D("-11.00") and f.cash == D("89.00") and f.position.quantity == D(0)


def test_cannot_sell_more_than_held_or_short():
    with pytest.raises(TradeError, match="You hold"):
        sell(D("0"), Position(D(5), D("1"), D("0")), D(6), D("1"))
    with pytest.raises(TradeError):
        sell(D("0"), EMPTY, D(1), D("1"))


def test_rejects_bad_numbers():
    for q, pr in ((D(0), D(1)), (D(-1), D(1)), (D(1), D(0))):
        with pytest.raises(TradeError):
            buy(D("10"), EMPTY, q, pr)


def test_fractional_quantities_and_rounding():
    f = buy(D("100"), EMPTY, D("0.3333"), D("3.333333"))
    assert f.gross == D("1.11") and f.cash == D("98.89")


def test_rebuy_after_closing_starts_a_fresh_average_but_keeps_realized():
    closed = sell(D("0"), Position(D(10), D("10"), D("0")), D(10), D("12")).position
    again = buy(D("1000"), closed, D(5), D("30")).position
    assert again.avg_entry_price == D("30.000000") and again.realized_pnl == D("20.00")


def test_valuation():
    v = value_position(Position(D(40), D("17.5"), D(0)), D("20"))
    assert (v.market_value, v.cost_basis, v.unrealized_pnl) == (D("800.00"), D("700.00"), D("100.00"))
