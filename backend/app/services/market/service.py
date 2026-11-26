"""Cached daily prices with a hard daily request budget.

Prices are shared public data, so the cache is shared across users. Every provider request is counted
before it is made (failed requests count too: the provider counts them). When the provider fails or the
budget is used up, the last cached prices are returned marked stale rather than hidden or invented.
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import MarketDataCache

from .provider import Bar, ProviderError, fetch_daily

PROVIDER = "alphavantage"
MIN_REFRESH = timedelta(minutes=15)  # a manual refresh cannot spend requests faster than this per symbol


class MarketUnavailable(Exception):
    """kind: not_configured | budget | rate_limit | invalid_symbol | auth | unavailable"""

    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind


@dataclass
class Daily:
    bars: list[Bar]
    fetched_at: datetime
    expires_at: datetime
    stale: bool
    warning: str | None


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def cache_key(symbol: str) -> str:
    return f"av:daily:{symbol}"


def encode_bars(bars: list[Bar]) -> dict:
    return {"bars": [[b.day.isoformat(), str(b.open), str(b.high), str(b.low), str(b.close), b.volume] for b in bars]}


def decode_bars(payload: dict) -> list[Bar]:
    return [Bar(date.fromisoformat(d), Decimal(o), Decimal(h), Decimal(l), Decimal(c), int(v)) for d, o, h, l, c, v in payload["bars"]]


def _budget_key(day: date) -> str:
    return f"av:budget:{day.isoformat()}"


def budget_used(db: Session, now: datetime) -> int:
    row = db.scalar(select(MarketDataCache).where(MarketDataCache.cache_key == _budget_key(now.date())))
    return int(row.payload.get("used", 0)) if row else 0


def _reserve_request(db: Session, now: datetime, limit: int) -> bool:
    """Counts one provider request against today's budget (UTC day). False when the budget is used up."""
    key = _budget_key(now.date())
    for attempt in (1, 2):
        row = db.scalar(select(MarketDataCache).where(MarketDataCache.cache_key == key).with_for_update())
        if row is not None:
            used = int(row.payload.get("used", 0))
            if used >= limit:
                db.rollback()
                return False
            row.payload = {"used": used + 1}
            db.commit()
            return True
        try:
            db.add(MarketDataCache(
                cache_key=key, provider=PROVIDER, symbol="*", data_type="budget", payload={"used": 1},
                fetched_at=now, expires_at=now + timedelta(days=2),
            ))
            db.commit()
            return True
        except IntegrityError:  # another request created today's row first; count on top of it
            db.rollback()
    return False


def cached_daily(db: Session, symbol: str) -> MarketDataCache | None:
    return db.scalar(select(MarketDataCache).where(MarketDataCache.cache_key == cache_key(symbol)))


def saved_close(db: Session, symbol: str) -> tuple[Decimal, date] | None:
    """Latest saved closing price and its trading day, from the cache only (never calls the provider)."""
    row = cached_daily(db, symbol)
    if row is None:
        return None
    bars = decode_bars(row.payload)
    return (bars[-1].close, bars[-1].day) if bars else None


def on_watchlist(db: Session, user_id, symbol: str) -> bool:
    from app.models import Watchlist, WatchlistInstrument
    return db.scalar(
        select(WatchlistInstrument.id).join(Watchlist, Watchlist.id == WatchlistInstrument.watchlist_id)
        .where(Watchlist.user_id == user_id, WatchlistInstrument.symbol == symbol).limit(1)
    ) is not None


def get_daily(db: Session, settings: Settings, symbol: str, now: datetime | None = None, force: bool = False) -> Daily:
    now = now or datetime.now(timezone.utc)
    row = cached_daily(db, symbol)
    if row is not None:
        fresh = _utc(row.expires_at) > now
        recent = now - _utc(row.fetched_at) < MIN_REFRESH
        if (fresh and not force) or (force and recent):
            return Daily(decode_bars(row.payload), _utc(row.fetched_at), _utc(row.expires_at), False, None)

    def fall_back(kind: str, message: str) -> Daily:
        if row is None:
            raise MarketUnavailable(kind, message)
        return Daily(decode_bars(row.payload), _utc(row.fetched_at), _utc(row.expires_at), True,
                     f"{message} Showing the last prices saved.")

    if not settings.alphavantage_api_key:
        return fall_back("not_configured", "No price provider key is configured.")
    if not _reserve_request(db, now, settings.alphavantage_daily_limit):
        return fall_back("budget", "Today's price request budget is used up.")
    try:
        bars = fetch_daily(symbol, settings.alphavantage_api_key)
    except ProviderError as exc:
        return fall_back(exc.kind, str(exc))
    expires = now + timedelta(hours=settings.market_cache_hours)
    payload = encode_bars(bars)
    row = cached_daily(db, symbol)  # re-read: the budget commit above may have expired it
    if row is None:
        db.add(MarketDataCache(
            cache_key=cache_key(symbol), provider=PROVIDER, symbol=symbol, data_type="daily",
            payload=payload, fetched_at=now, expires_at=expires,
        ))
    else:
        row.payload, row.fetched_at, row.expires_at = payload, now, expires
    try:
        db.commit()
    except IntegrityError:  # two requests for a new symbol raced; the other one's data is just as good
        db.rollback()
    return Daily(bars, now, expires, False, None)
