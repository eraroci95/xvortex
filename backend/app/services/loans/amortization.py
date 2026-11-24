"""Loan amortization and payment allocation. Pure functions, exact Decimal arithmetic.

Documented conventions (configurable per loan via `method` and `frequency`):
- Periodic rate = annual_rate_percent / 100 / periods_per_year (nominal rate, no day-count).
- All amounts are rounded to 0.01 with ROUND_HALF_UP; the final installment absorbs any
  rounding remainder so the schedule always sums to exactly the principal.
- Methods:
    annuity          equal total installments (principal share grows over time)
    equal_principal  equal principal installments (total shrinks over time)
    interest_only    interest each period, full principal at maturity
- Due dates are start_date + k periods; the last installment is always on maturity_date.
- Payments are allocated to the oldest unpaid installment first, interest before principal.
- Prepayments do not recompute the schedule in this version; they reduce the remaining
  principal due on the oldest installments.
"""
import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
PERIODS_PER_YEAR = {
    "weekly": 52, "biweekly": 26, "monthly": 12, "quarterly": 4, "semiannual": 2, "annual": 1,
}
METHODS = ("annuity", "equal_principal", "interest_only")


def money(x: Decimal) -> Decimal:
    return x.quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Installment:
    number: int
    due_date: date
    principal: Decimal
    interest: Decimal

    @property
    def total(self) -> Decimal:
        return self.principal + self.interest


@dataclass(frozen=True)
class Allocation:
    installment: Installment
    paid_principal: Decimal
    paid_interest: Decimal

    @property
    def principal_outstanding(self) -> Decimal:
        return self.installment.principal - self.paid_principal

    @property
    def interest_outstanding(self) -> Decimal:
        return self.installment.interest - self.paid_interest

    @property
    def is_settled(self) -> bool:
        return self.principal_outstanding == 0 and self.interest_outstanding == 0


def add_months(d: date, months: int) -> date:
    index = d.year * 12 + (d.month - 1) + months
    year, month = divmod(index, 12)
    month += 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def due_date(start: date, frequency: str, k: int) -> date:
    if frequency == "weekly":
        return start + timedelta(weeks=k)
    if frequency == "biweekly":
        return start + timedelta(weeks=2 * k)
    months = {"monthly": 1, "quarterly": 3, "semiannual": 6, "annual": 12}[frequency]
    return add_months(start, months * k)


def due_dates(start: date, maturity: date, frequency: str) -> list[date]:
    if frequency not in PERIODS_PER_YEAR:
        raise ValueError(f"unknown frequency: {frequency}")
    if maturity <= start:
        raise ValueError("maturity must be after start")
    dates, k = [], 1
    while (d := due_date(start, frequency, k)) < maturity:
        dates.append(d)
        k += 1
    dates.append(maturity)
    return dates


def build_schedule(
    principal: Decimal,
    annual_rate_percent: Decimal,
    start: date,
    maturity: date,
    frequency: str = "monthly",
    method: str = "annuity",
) -> list[Installment]:
    if principal <= 0:
        raise ValueError("principal must be positive")
    if annual_rate_percent < 0:
        raise ValueError("rate must not be negative")
    if method not in METHODS:
        raise ValueError(f"unknown method: {method}")

    dates = due_dates(start, maturity, frequency)
    n = len(dates)
    r = annual_rate_percent / Decimal(100) / PERIODS_PER_YEAR[frequency]

    if method == "annuity":
        level = principal / n if r == 0 else principal * r / (1 - (1 + r) ** -n)
        level = money(level)
    elif method == "equal_principal":
        level = money(principal / n)

    balance, out = principal, []
    for i, d in enumerate(dates, start=1):
        interest = money(balance * r)
        last = i == n
        if method == "interest_only":
            princ = balance if last else Decimal("0.00")
        elif last:
            princ = balance
        elif method == "annuity":
            princ = min(level - interest, balance)
        else:
            princ = min(level, balance)
        out.append(Installment(i, d, princ, interest))
        balance -= princ
    return out


def allocate_payments(schedule: list[Installment], payments: list[Decimal]) -> tuple[list[Allocation], Decimal]:
    """Apply payments oldest-first, interest before principal. Returns (allocations, unapplied excess)."""
    remaining = sum(payments, Decimal("0.00"))
    result = []
    for inst in schedule:
        pay_interest = min(remaining, inst.interest)
        remaining -= pay_interest
        pay_principal = min(remaining, inst.principal)
        remaining -= pay_principal
        result.append(Allocation(inst, pay_principal, pay_interest))
    return result, remaining


def outstanding_principal(allocations: list[Allocation]) -> Decimal:
    return sum((a.principal_outstanding for a in allocations), Decimal("0.00"))


def remaining_interest(allocations: list[Allocation]) -> Decimal:
    return sum((a.interest_outstanding for a in allocations), Decimal("0.00"))
