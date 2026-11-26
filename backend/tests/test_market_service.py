"""Cache and budget rules, run against in-memory SQLite (needs sqlalchemy)."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D

import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("pydantic_settings")

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.models import Base  # noqa: E402
from app.services.market import service  # noqa: E402
from app.services.market.provider import Bar, ProviderError  # noqa: E402

NOW = datetime(2026, 3, 2, 12, 0, tzinfo=timezone.utc)


class Cfg:
    def __init__(self, key="k", limit=2, hours=12):
        self.alphavantage_api_key, self.alphavantage_daily_limit, self.market_cache_hours = key, limit, hours


def _bars(close="10"):
    from datetime import date
    return [Bar(date(2026, 2, 27), D(close), D(close), D(close), D(close), 1)]


@pytest.fixture()
def db():
    engine = create_engine("sqlite+pysqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine, expire_on_commit=False)() as s:
        yield s


@pytest.fixture()
def fetches(monkeypatch):
    calls = []

    def fake(symbol, key):
        calls.append(symbol)
        if isinstance(fake.result, Exception):
            raise fake.result
        return fake.result
    fake.result = _bars()
    monkeypatch.setattr(service, "fetch_daily", fake)
    fake.calls = calls
    return fake


def test_fresh_cache_is_served_without_a_request(db, fetches):
    first = service.get_daily(db, Cfg(), "IBM", NOW)
    again = service.get_daily(db, Cfg(), "IBM", NOW + timedelta(hours=1))
    assert len(fetches.calls) == 1 and not again.stale and again.bars == first.bars
    assert service.budget_used(db, NOW) == 1


def test_expired_cache_is_refetched(db, fetches):
    service.get_daily(db, Cfg(), "IBM", NOW)
    fetches.result = _bars("11")
    later = service.get_daily(db, Cfg(), "IBM", NOW + timedelta(hours=13))
    assert len(fetches.calls) == 2 and later.bars[-1].close == D("11")


def test_manual_refresh_is_rate_limited_per_symbol(db, fetches):
    service.get_daily(db, Cfg(), "IBM", NOW)
    service.get_daily(db, Cfg(), "IBM", NOW + timedelta(minutes=5), force=True)
    assert len(fetches.calls) == 1
    service.get_daily(db, Cfg(), "IBM", NOW + timedelta(minutes=20), force=True)
    assert len(fetches.calls) == 2


def test_budget_stops_requests_and_serves_stale_data(db, fetches):
    cfg = Cfg(limit=2)
    service.get_daily(db, cfg, "AAA", NOW)
    service.get_daily(db, cfg, "BBB", NOW)
    with pytest.raises(service.MarketUnavailable) as e:
        service.get_daily(db, cfg, "CCC", NOW)  # nothing cached, budget gone
    assert e.value.kind == "budget" and len(fetches.calls) == 2
    stale = service.get_daily(db, cfg, "AAA", NOW + timedelta(hours=13))  # expired but budget gone
    assert stale.stale and "budget" in stale.warning and len(fetches.calls) == 2
    # a new UTC day has a new budget
    service.get_daily(db, cfg, "CCC", NOW + timedelta(days=1))
    assert len(fetches.calls) == 3


def test_provider_failure_falls_back_to_cache_or_raises(db, fetches):
    service.get_daily(db, Cfg(limit=5), "IBM", NOW)
    fetches.result = ProviderError("rate_limit", "The price provider's request limit has been reached.")
    stale = service.get_daily(db, Cfg(limit=5), "IBM", NOW + timedelta(hours=13))
    assert stale.stale and "limit" in stale.warning
    with pytest.raises(service.MarketUnavailable) as e:
        service.get_daily(db, Cfg(limit=5), "NEW", NOW)
    assert e.value.kind == "rate_limit"


def test_without_a_key_nothing_is_fetched(db, fetches):
    with pytest.raises(service.MarketUnavailable) as e:
        service.get_daily(db, Cfg(key=None), "IBM", NOW)
    assert e.value.kind == "not_configured" and fetches.calls == []
