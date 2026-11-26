"""Watchlist and daily-price endpoints (needs the full dependency set)."""
from datetime import date, timedelta
from decimal import Decimal as D

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("argon2")

from app.core.config import get_settings  # noqa: E402
from app.services.market import service  # noqa: E402
from app.services.market.provider import Bar, ProviderError  # noqa: E402
from tests.helpers import login_csrf  # noqa: E402


def _bars(n=60):
    start = date(2026, 1, 1)
    return [Bar(start + timedelta(days=i), D(100 + i), D(100 + i), D(100 + i), D(100 + i), 10) for i in range(n)]


@pytest.fixture()
def provider(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "alphavantage_api_key", "test-key", raising=False)
    calls = []

    def fake(symbol, key):
        calls.append(symbol)
        if isinstance(fake.result, Exception):
            raise fake.result
        return fake.result
    fake.result, fake.calls = _bars(), calls
    monkeypatch.setattr(service, "fetch_daily", fake)
    return fake


def _list(client, h, name="Core"):
    r = client.post("/api/market/watchlists", json={"name": name}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_needs_sign_in(client):
    assert client.get("/api/market/watchlists").status_code == 401
    assert client.get("/api/market/symbols/IBM/daily").status_code == 401


def test_watchlist_crud_and_validation(client):
    h = login_csrf(client)
    wid = _list(client, h)
    assert client.post("/api/market/watchlists", json={"name": "Core"}, headers=h).status_code == 409
    assert client.post("/api/market/watchlists", json={"name": "  "}, headers=h).status_code == 422
    r = client.post(f"/api/market/watchlists/{wid}/instruments", json={"symbol": " ibm "}, headers=h)
    assert r.status_code == 201 and r.json()["instruments"][0]["symbol"] == "IBM"
    assert r.json()["instruments"][0]["last_close"] is None  # nothing fetched yet
    assert client.post(f"/api/market/watchlists/{wid}/instruments", json={"symbol": "IBM"}, headers=h).status_code == 409
    assert client.post(f"/api/market/watchlists/{wid}/instruments", json={"symbol": "bad symbol!"}, headers=h).status_code == 422
    assert client.patch(f"/api/market/watchlists/{wid}", json={"name": "Renamed"}, headers=h).json()["name"] == "Renamed"
    assert client.delete(f"/api/market/watchlists/{wid}/instruments/IBM", headers=h).json()["instruments"] == []
    assert client.delete(f"/api/market/watchlists/{wid}/instruments/IBM", headers=h).status_code == 404
    assert client.delete(f"/api/market/watchlists/{wid}", headers=h).status_code == 204
    assert client.get("/api/market/watchlists").json() == []


def test_daily_returns_prices_indicators_and_freshness(client, provider):
    h = login_csrf(client)
    wid = _list(client, h)
    client.post(f"/api/market/watchlists/{wid}/instruments", json={"symbol": "IBM"}, headers=h)
    d = client.get("/api/market/symbols/IBM/daily").json()
    assert len(d["bars"]) == 60 and d["stale"] is False and d["source"] == "Alpha Vantage"
    assert d["sma20"][18] is None and d["sma20"][19] is not None and d["sma50"][48] is None and d["rsi14"][13] is None
    assert D(d["rsi14"][-1]) == D(100)  # prices only rise
    client.get("/api/market/symbols/IBM/daily")
    assert provider.calls == ["IBM"]  # second view came from the saved prices
    row = client.get("/api/market/watchlists").json()[0]["instruments"][0]
    assert row["last_close"] == "159.000000" or D(row["last_close"]) == D(159)
    assert row["as_of"] == (date(2026, 1, 1) + timedelta(days=59)).isoformat() and row["change_pct"] is not None


def test_daily_only_for_symbols_on_your_watchlists(client, provider):
    h = login_csrf(client)
    assert client.get("/api/market/symbols/IBM/daily").status_code == 404
    wid = _list(client, h)
    client.post(f"/api/market/watchlists/{wid}/instruments", json={"symbol": "IBM"}, headers=h)
    other = login_csrf(client, "user@example.com")  # noqa: F841
    assert client.get("/api/market/symbols/IBM/daily").status_code == 404
    assert client.get("/api/market/watchlists").json() == []
    assert provider.calls == []


def test_provider_problems_map_to_clear_statuses(client, provider):
    h = login_csrf(client)
    wid = _list(client, h)
    client.post(f"/api/market/watchlists/{wid}/instruments", json={"symbol": "ZZZ"}, headers=h)
    provider.result = ProviderError("invalid_symbol", "The price provider does not know this symbol.")
    assert client.get("/api/market/symbols/ZZZ/daily").status_code == 404
    provider.result = ProviderError("rate_limit", "The price provider's request limit has been reached.")
    r = client.get("/api/market/symbols/ZZZ/daily")
    assert r.status_code == 429 and "limit" in r.json()["detail"]


def test_status_reports_budget(client, provider):
    login_csrf(client)
    s = client.get("/api/market/status").json()
    assert s["configured"] is True and s["budget_used"] == 0 and s["budget_limit"] >= 1
