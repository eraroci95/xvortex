"""Paper accounts and simulated market orders (needs the full dependency set)."""
from datetime import date, timedelta
from decimal import Decimal as D

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("argon2")

from sqlalchemy import select  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.models import AuditLog  # noqa: E402
from app.services.market import service  # noqa: E402
from app.services.market.provider import Bar, ProviderError  # noqa: E402
from tests.helpers import login_csrf  # noqa: E402


def _bars(last="100", age_days=1):
    end = date.today() - timedelta(days=age_days)
    mk = lambda d, c: Bar(d, D(c), D(c), D(c), D(c), 1)  # noqa: E731
    return [mk(end - timedelta(days=1), "90"), mk(end, last)]


@pytest.fixture()
def provider(monkeypatch):
    monkeypatch.setattr(get_settings(), "alphavantage_api_key", "test-key", raising=False)

    def fake(symbol, key):
        if isinstance(fake.result, Exception):
            raise fake.result
        return fake.result
    fake.result = _bars()
    monkeypatch.setattr(service, "fetch_daily", fake)
    return fake


def _account(client, h, cash="1000.00", currency="SEK"):
    r = client.post("/api/paper/accounts", json={"name": "Practice", "starting_cash": cash, "currency": currency}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _watch(client, h, symbol="IBM"):
    wid = client.post("/api/market/watchlists", json={"name": f"L-{symbol}"}, headers=h).json()["id"]
    assert client.post(f"/api/market/watchlists/{wid}/instruments", json={"symbol": symbol}, headers=h).status_code == 201


def _order(client, h, aid, side="buy", qty="5", symbol="IBM"):
    return client.post(f"/api/paper/accounts/{aid}/orders", json={"symbol": symbol, "side": side, "quantity": qty}, headers=h)


def test_needs_sign_in_and_csrf(client):
    assert client.get("/api/paper/accounts").status_code == 401
    h = login_csrf(client)
    assert client.post("/api/paper/accounts", json={"name": "x", "starting_cash": "10"}).status_code == 403
    assert client.post("/api/paper/accounts", json={"name": "x", "starting_cash": "10"}, headers=h).status_code == 201


def test_account_validation_and_limit(client):
    h = login_csrf(client)
    for bad in ({"name": "a", "starting_cash": "0"}, {"name": "a", "starting_cash": "-5"}, {"name": " ", "starting_cash": "5"},
                {"name": "a", "starting_cash": "5", "currency": "sek"}, {"name": "a", "starting_cash": "5.001"}):
        assert client.post("/api/paper/accounts", json=bad, headers=h).status_code == 422
    for _ in range(5):
        _account(client, h)
    assert client.post("/api/paper/accounts", json={"name": "six", "starting_cash": "5"}, headers=h).status_code == 409


def test_buy_fills_at_saved_close_and_values_the_position(client, provider):
    h = login_csrf(client)
    aid = _account(client, h)
    _watch(client, h)
    r = _order(client, h, aid)
    assert r.status_code == 201, r.text
    out = r.json()
    assert D(out["trade"]["price"]) == D("100") and out["trade"]["simulated"] is True and out["trade"]["side"] == "buy"
    acct = out["account"]
    assert D(acct["cash_balance"]) == D("500.00")
    pos = acct["positions"][0]
    assert pos["symbol"] == "IBM" and D(pos["quantity"]) == D(5) and D(pos["market_value"]) == D("500.00")
    assert D(acct["equity"]) == D("1000.00") and D(acct["unrealized_pnl"]) == D("0.00") and acct["valuation_status"] == "end_of_day"
    with client.Session() as s:
        assert "paper_order_filled" in s.scalars(select(AuditLog.action)).all()


def test_sell_realises_profit_and_closing_removes_the_position(client, provider):
    h = login_csrf(client)
    aid = _account(client, h)
    _watch(client, h)
    _order(client, h, aid, qty="5")
    provider.result = _bars("120")
    # saved prices are still fresh, so force a newer close by expiring the cache
    with client.Session() as s:
        from app.models import MarketDataCache
        row = s.scalar(select(MarketDataCache).where(MarketDataCache.cache_key == "av:daily:IBM"))
        row.expires_at = row.fetched_at - timedelta(hours=1)
        s.commit()
    r = _order(client, h, aid, side="sell", qty="5")
    assert r.status_code == 201, r.text
    assert D(r.json()["trade"]["realized_pnl"]) == D("100.00")
    acct = r.json()["account"]
    assert acct["positions"] == [] and D(acct["cash_balance"]) == D("1100.00") and D(acct["realized_pnl"]) == D("100.00")


def test_rejections_are_clear_and_change_nothing(client, provider):
    h = login_csrf(client)
    aid = _account(client, h, cash="100.00")
    assert _order(client, h, aid).status_code == 409  # not on a watchlist
    _watch(client, h)
    assert _order(client, h, aid, qty="5").status_code == 409  # costs 500, has 100
    assert _order(client, h, aid, side="sell", qty="1").status_code == 409  # holds nothing
    assert _order(client, h, aid, qty="0").status_code == 422
    assert _order(client, h, aid, qty="1.00001").status_code == 422
    assert client.post(f"/api/paper/accounts/{aid}/orders", json={"symbol": "IBM", "side": "short", "quantity": "1"}, headers=h).status_code == 422
    acct = client.get("/api/paper/accounts").json()[0]
    assert D(acct["cash_balance"]) == D("100.00") and acct["trades"] == []


def test_no_price_or_old_price_means_no_trade(client, provider):
    h = login_csrf(client)
    aid = _account(client, h)
    _watch(client, h)
    provider.result = ProviderError("rate_limit", "The price provider's request limit has been reached.")
    r = _order(client, h, aid)
    assert r.status_code == 429 and "No price for IBM" in r.json()["detail"]
    provider.result = _bars(age_days=30)
    r = _order(client, h, aid)
    assert r.status_code == 409 and "too old" in r.json()["detail"]
    assert client.get("/api/paper/accounts").json()[0]["trades"] == []


def test_users_cannot_touch_each_others_accounts(client, provider):
    admin = login_csrf(client)
    aid = _account(client, admin)
    _watch(client, admin)
    other = login_csrf(client, "user@example.com")
    assert client.get("/api/paper/accounts").json() == []
    _watch(client, other)
    assert _order(client, other, aid).status_code == 404
    assert client.delete(f"/api/paper/accounts/{aid}", headers=other).status_code == 404
    login_csrf(client)
    assert D(client.get("/api/paper/accounts").json()[0]["cash_balance"]) == D("1000.00")


def test_delete_account(client):
    h = login_csrf(client)
    aid = _account(client, h)
    assert client.delete(f"/api/paper/accounts/{aid}", headers=h).status_code == 204
    assert client.get("/api/paper/accounts").json() == []


def test_dashboard_values_positions_and_leaves_out_other_currencies(client, provider):
    h = login_csrf(client)
    aid = _account(client, h)
    _account(client, h, currency="USD")
    _watch(client, h)
    _order(client, h, aid, qty="5")
    p = client.get("/api/dashboard/summary").json()["paper"]
    assert p["accounts"] == 1 and p["excluded_accounts"] == 1 and p["currency"] == "SEK"
    assert D(p["market_value"]) == D("500.00") and p["valuation_status"] == "end_of_day"
