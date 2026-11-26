"""Alpha Vantage daily prices. Parsing is pure (tested without network); the fetch uses only the stdlib.

Free keys allow 25 requests a day and 5 a minute and return the latest 100 daily bars, so callers
cache aggressively and count every request (see service.py). Prices are end-of-day, never live.
"""
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

URL = "https://www.alphavantage.co/query"
SYMBOL_PATTERN = r"^[A-Z0-9][A-Z0-9.\-]{0,15}$"


class ProviderError(Exception):
    """kind: rate_limit | invalid_symbol | auth | unavailable"""

    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind


@dataclass(frozen=True)
class Bar:
    day: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


def parse_daily(payload: dict) -> list[Bar]:
    """Oldest first. Raises ProviderError for the provider's error and limit messages."""
    if not isinstance(payload, dict):
        raise ProviderError("unavailable", "Unexpected response from the price provider.")
    message = payload.get("Error Message")
    if message:
        text = str(message).lower()
        if "apikey" in text or "api key" in text:
            raise ProviderError("auth", "The price provider rejected the API key.")
        raise ProviderError("invalid_symbol", "The price provider does not know this symbol.")
    note = payload.get("Note") or payload.get("Information")
    if note:
        text = str(note).lower()
        if any(w in text for w in ("per day", "per minute", "call frequency", "rate limit", "requests")):
            raise ProviderError("rate_limit", "The price provider's request limit has been reached.")
        if "api key" in text or "apikey" in text:
            raise ProviderError("auth", "The price provider rejected the API key.")
        raise ProviderError("unavailable", "The price provider could not serve this request.")
    series = payload.get("Time Series (Daily)")
    if not isinstance(series, dict) or not series:
        raise ProviderError("unavailable", "The price provider returned no daily prices.")
    bars = []
    try:
        for day, row in series.items():
            bars.append(Bar(
                date.fromisoformat(day), Decimal(row["1. open"]), Decimal(row["2. high"]),
                Decimal(row["3. low"]), Decimal(row["4. close"]), int(row["5. volume"]),
            ))
    except (KeyError, ValueError, InvalidOperation, TypeError):
        raise ProviderError("unavailable", "The price provider returned malformed prices.")
    bars.sort(key=lambda b: b.day)
    return bars


def fetch_daily(symbol: str, api_key: str, timeout: float = 10.0) -> list[Bar]:
    query = urllib.parse.urlencode({"function": "TIME_SERIES_DAILY", "symbol": symbol, "outputsize": "compact", "apikey": api_key})
    try:
        with urllib.request.urlopen(f"{URL}?{query}", timeout=timeout) as resp:  # noqa: S310 (fixed https URL)
            payload = json.loads(resp.read(2_000_000))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        raise ProviderError("unavailable", "Could not reach the price provider.")
    return parse_daily(payload)
