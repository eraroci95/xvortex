"""Technical indicators over closing prices. Exact Decimal arithmetic; None where there is not enough history."""
from decimal import ROUND_HALF_UP, Decimal

Q = Decimal("0.0001")


def _q(x: Decimal) -> Decimal:
    return x.quantize(Q, rounding=ROUND_HALF_UP)


def sma(closes: list[Decimal], period: int) -> list[Decimal | None]:
    """Simple moving average; the first period-1 entries are None."""
    if period < 1:
        raise ValueError("period must be at least 1")
    out: list[Decimal | None] = []
    window = Decimal(0)
    for i, c in enumerate(closes):
        window += c
        if i >= period:
            window -= closes[i - period]
        out.append(_q(window / period) if i >= period - 1 else None)
    return out


def rsi(closes: list[Decimal], period: int = 14) -> list[Decimal | None]:
    """Wilder's RSI on a 0-100 scale. The first value needs period+1 closes. A flat series is 50."""
    if period < 1:
        raise ValueError("period must be at least 1")
    out: list[Decimal | None] = [None] * len(closes)
    if len(closes) <= period:
        return out
    gains = [max(closes[i] - closes[i - 1], Decimal(0)) for i in range(1, len(closes))]
    losses = [max(closes[i - 1] - closes[i], Decimal(0)) for i in range(1, len(closes))]
    avg_gain = sum(gains[:period], Decimal(0)) / period
    avg_loss = sum(losses[:period], Decimal(0)) / period

    def value() -> Decimal:
        if avg_gain == 0 and avg_loss == 0:
            return Decimal(50)
        if avg_loss == 0:
            return Decimal(100)
        return _q(100 - 100 / (1 + avg_gain / avg_loss))

    out[period] = value()
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        out[i + 1] = value()
    return out
