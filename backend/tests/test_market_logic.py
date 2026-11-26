from datetime import date
from decimal import Decimal as D

import pytest

from app.services.market.indicators import rsi, sma
from app.services.market.provider import ProviderError, parse_daily


def _row(c):
    return {"1. open": c, "2. high": c, "3. low": c, "4. close": c, "5. volume": "100"}


def test_parse_orders_oldest_first_and_keeps_decimals():
    bars = parse_daily({"Meta Data": {}, "Time Series (Daily)": {"2026-01-03": _row("3.10"), "2026-01-02": _row("2.05")}})
    assert [b.day for b in bars] == [date(2026, 1, 2), date(2026, 1, 3)]
    assert bars[0].close == D("2.05") and bars[1].volume == 100


@pytest.mark.parametrize("payload,kind", [
    ({"Error Message": "Invalid API call. Please retry or visit the documentation"}, "invalid_symbol"),
    ({"Error Message": "the parameter apikey is invalid or missing."}, "auth"),
    ({"Information": "our standard API rate limit is 25 requests per day."}, "rate_limit"),
    ({"Note": "Thank you! Our standard API call frequency is 5 calls per minute"}, "rate_limit"),
    ({"Information": "The demo API key is for demo purposes only."}, "auth"),
    ({"Information": "Something else entirely"}, "unavailable"),
    ({}, "unavailable"), ({"Time Series (Daily)": {"2026-01-02": {"1. open": "x"}}}, "unavailable"),
    ({"Time Series (Daily)": {"bad-date": _row("1")}}, "unavailable"), ([], "unavailable"),
])
def test_provider_errors_are_classified(payload, kind):
    with pytest.raises(ProviderError) as e:
        parse_daily(payload)
    assert e.value.kind == kind


def test_sma():
    out = sma([D(x) for x in (1, 2, 3, 4, 5)], 3)
    assert out == [None, None, D("2.0000"), D("3.0000"), D("4.0000")]
    assert sma([D(1)], 1) == [D("1.0000")]
    with pytest.raises(ValueError):
        sma([D(1)], 0)


def test_rsi_edges():
    assert rsi([D(1)] * 5, 14) == [None] * 5  # too short
    assert rsi([D(5)] * 20, 14)[-1] == D(50)  # flat
    assert rsi([D(i) for i in range(1, 21)], 14)[-1] == D(100)  # only gains
    assert rsi([D(20 - i) for i in range(20)], 14)[-1] == D("0.0000")  # only losses
    assert rsi([D(i) for i in range(1, 21)], 14)[:14] == [None] * 14


def test_rsi_matches_wilder_reference():
    # Classic worked example (Wilder / StockCharts): first RSI(14) value is about 70.46.
    closes = [D(x) for x in (
        "44.3389", "44.0902", "44.1497", "43.6124", "44.3278", "44.8264", "45.0955", "45.4245", "45.8433",
        "46.0826", "45.8931", "46.0328", "45.6140", "46.2820", "46.2820",
    )]
    first = rsi(closes, 14)[14]
    assert D("70.0") < first < D("71.0")
