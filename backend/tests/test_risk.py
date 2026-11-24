from datetime import date
from decimal import Decimal as D

from app.services.loans.amortization import allocate_payments, build_schedule
from app.services.loans.risk import assess_loan


def _allocs(paid):
    s = build_schedule(D("1200"), D("12"), date(2026, 1, 1), date(2026, 7, 1), "monthly", "equal_principal")
    a, _ = allocate_payments(s, [D(paid)])
    return a


def test_on_time_is_low():
    r = assess_loan(_allocs("0"), date(2026, 1, 1), D("1200"), D("5000"))
    assert r.level == "low" and r.triggers == []


def test_overdue_thresholds():
    assert assess_loan(_allocs("0"), date(2026, 2, 10), D("1200"), D("5000")).level == "medium"
    assert assess_loan(_allocs("0"), date(2026, 4, 15), D("1200"), D("5000")).level == "high"


def test_concentration_flag_and_disclaimer():
    r = assess_loan(_allocs("0"), date(2026, 1, 1), D("1200"), D("1500"))
    assert r.level == "medium" and "total outstanding" in r.triggers[0]
    assert "not a prediction" in r.disclaimer
